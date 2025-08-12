# client.py

import socket
import threading
import ssl
import json
import os
import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog
import queue
import time

from config import (SERVER_HOST, SERVER_PORT, WINDOW_TITLE, MESSAGE_TYPE_TEXT,
                    MESSAGE_TYPE_IMAGE, MESSAGE_TYPE_DOCUMENT, MESSAGE_TYPE_VIDEO,
                    MAX_IMAGE_SIZE, MAX_DOCUMENT_SIZE, MAX_VIDEO_SIZE)
from secure_socket import SecureSocket
from network_manager import NetworkManager
from crypto_utils import CryptoUtils
from event_handler import EventHandler
from message_handler import Message

class SecureChatClient:
    """
    The main client class for the secure chat application.
    """
    def __init__(self, host, port, certfile):
        """Initializes the client with host, port, and certificate."""
        self.host = host
        self.port = port
        self.certfile = certfile
        self.secure_socket = SecureSocket(self.certfile, self.certfile)
        self.sock = None
        self.network_manager = None
        self.aes_key = None
        self._is_connected = False
        self.username = "User"
        self.incoming_messages_queue = queue.Queue()

        self.event_handler = EventHandler(self)
        self.setup_gui()

    def setup_gui(self):
        """Sets up the graphical user interface using Tkinter."""
        self.window = tk.Tk()
        self.window.title(f"{WINDOW_TITLE} - {self.username}")
        self.window.geometry("800x600")

        self.chat_area = scrolledtext.ScrolledText(self.window, state=tk.DISABLED, wrap=tk.WORD)
        self.chat_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        input_frame = tk.Frame(self.window)
        input_frame.pack(padx=10, pady=(0, 10), fill=tk.X)

        self.message_entry = tk.Entry(input_frame)
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.message_entry.bind("<Return>", self.event_handler.on_send_button_click)
        
        send_button = tk.Button(input_frame, text="Send", command=lambda: self.event_handler.on_send_button_click(self.message_entry.get()))
        send_button.pack(side=tk.LEFT, padx=(5, 0))

        connect_frame = tk.Frame(self.window)
        connect_frame.pack(padx=10, pady=(0, 10), fill=tk.X)
        self.status_label = tk.Label(connect_frame, text="Status: Disconnected", fg="red")
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        connect_button = tk.Button(connect_frame, text="Connect", command=lambda: self.event_handler.on_connect_button_click(self.host, self.port))
        connect_button.pack(side=tk.LEFT, padx=(5,0))
        disconnect_button = tk.Button(connect_frame, text="Disconnect", command=self.event_handler.on_disconnect_button_click)
        disconnect_button.pack(side=tk.LEFT)

        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

    def run(self):
        self.window.mainloop()

    def on_close(self):
        self.cleanup_connection()
        self.window.destroy()

    def connect_to_server(self, host, port):
        if self._is_connected:
            messagebox.showinfo("Info", "Already connected.")
            return

        try:
            print("Client is attempting to connect to the server.")
            context = self.secure_socket.create_client_context()
            self.sock = socket.create_connection((host, port))
            
            self.sock = self.secure_socket.wrap_socket(context, self.sock, server_hostname=host)
            
            self.network_manager = NetworkManager(self.sock)
            
            # Key exchange
            # 🆕 Added robust check to handle failed receive
            result = self.network_manager.receive_message()
            if not result or not result[1]:
                raise ConnectionError("Failed to receive server public key.")
            server_pk_bytes = result[1]
            server_public_key = CryptoUtils.deserialize_ecc_public_key(server_pk_bytes)
            
            client_private_key, client_public_key = CryptoUtils.generate_ecc_key_pair()
            serialized_client_pk = CryptoUtils.serialize_ecc_public_key(client_public_key)
            self.network_manager.send_message(MESSAGE_TYPE_TEXT, serialized_client_pk)

            shared_secret = CryptoUtils.derive_shared_secret(client_private_key, server_public_key)
            self.aes_key, _ = CryptoUtils.generate_aes_key_from_password(shared_secret.x.to_bytes(32, 'big'))

            self._is_connected = True
            print("Secure key exchange successful. Connection established.")
            self.status_label.config(text="Status: Connected", fg="green")
            
            self.receive_thread = threading.Thread(target=self.receive_messages_thread, daemon=True)
            self.receive_thread.start()
            self.send_text_message("Hello from the client!")
            self.process_queue()
        
        except (socket.error, ssl.SSLError) as e:
            messagebox.showerror("Connection Error", f"Failed to connect to the server: {e}")
            self.cleanup_connection()
        except Exception as e:
            print(f"An unexpected error occurred during connection: {e}")
            self.cleanup_connection()

    def send_text_message(self, message_text):
        if not self._is_connected or not message_text:
            return

        try:
            # Debug: Client is about to send a message
            print(f"Client is about to send a message: '{message_text}'")
            
            message = Message(self.username, message_text, MESSAGE_TYPE_TEXT)
            serialized_message = json.dumps(message.to_dict()).encode('utf-8')
            
            nonce, ciphertext, tag = CryptoUtils.encrypt_aes_gcm(self.aes_key, serialized_message)
            
            # Debug: Client encrypted message
            print(f"Client encrypted message to: '{ciphertext.hex()}'")

            encrypted_payload = {
                'nonce': nonce.hex(),
                'ciphertext': ciphertext.hex(),
                'tag': tag.hex()
            }
            self.network_manager.send_message(MESSAGE_TYPE_TEXT, json.dumps(encrypted_payload).encode('utf-8'))
            self.message_entry.delete(0, tk.END)

        except Exception as e:
            messagebox.showerror("Error", f"Error sending message: {e}")
            self.cleanup_connection()

    def display_message(self, message_data):
        self.chat_area.config(state=tk.NORMAL)
        sender = message_data['sender']
        content = message_data['content']
        self.chat_area.insert(tk.END, f"[{sender}]: {content}\n")
        self.chat_area.config(state=tk.DISABLED)
        self.chat_area.see(tk.END)

    def receive_messages_thread(self):
        while self._is_connected:
            try:
                msg_type, encrypted_payload = self.network_manager.receive_message()
                if not encrypted_payload:
                    continue
                
                # Debug: Client received encrypted message
                print(f"Client received encrypted message: {encrypted_payload}")
                
                if msg_type == MESSAGE_TYPE_TEXT:
                    payload = json.loads(encrypted_payload)
                    nonce = bytes.fromhex(payload['nonce'])
                    ciphertext = bytes.fromhex(payload['ciphertext'])
                    tag = bytes.fromhex(payload['tag'])
                    
                    decrypted_message_bytes = CryptoUtils.decrypt_aes_gcm(self.aes_key, nonce, ciphertext, tag)
                    
                    # Debug: Client decrypted message
                    print(f"Client decrypted message to: '{decrypted_message_bytes.decode('utf-8')}'")
                    
                    message_data = json.loads(decrypted_message_bytes.decode('utf-8'))
                    self.incoming_messages_queue.put(message_data)

            except (socket.error, ConnectionResetError, ssl.SSLError) as e:
                print(f"Connection error: {e}")
                self._is_connected = False
                break
            except Exception as e:
                print(f"Error in receive_messages_thread: {e}")
        
        self.window.after(0, self.cleanup_connection)

    def process_queue(self):
        while not self.incoming_messages_queue.empty():
            message_data = self.incoming_messages_queue.get_nowait()
            self.display_message(message_data)

        if self._is_connected:
            self.window.after(100, self.process_queue)

    def cleanup_connection(self):
        # 🆕 Only proceed if the client is currently connected.
        if not self._is_connected:
            return

        if self.sock:
            self.sock.close()
        self.sock = None
        self.network_manager = None
        self._is_connected = False
        self.status_label.config(text="Status: Disconnected", fg="red")
        messagebox.showinfo("Disconnected", "Disconnected from server.")

def main():
    cert_file = "cert.pem"
    client = SecureChatClient(SERVER_HOST, SERVER_PORT, cert_file)
    client.run()

if __name__ == '__main__':
    main()