# server.py

import socket
import threading
import ssl
import json
import time

from config import SERVER_HOST, SERVER_PORT, MESSAGE_TYPE_TEXT, TIMEOUT
from secure_socket import SecureSocket
from network_manager import NetworkManager
from crypto_utils import CryptoUtils
from message_handler import Message

class SecureChatServer:
    """
    The main server class for the secure chat application.
    """
    def __init__(self, host, port, certfile, keyfile):
        """Initializes the server with host, port, certificate, and key."""
        self.host = host
        self.port = port
        self.certfile = certfile
        self.keyfile = keyfile
        self.secure_socket = SecureSocket(self.certfile, self.keyfile)
        self.clients = {}
        self.lock = threading.Lock()
        self.is_running = False
        self.server_socket = None

    def start(self):
        """Starts the server, listening for incoming connections."""
        SecureSocket.generate_certificates(self.certfile, self.keyfile)
        context = self.secure_socket.create_server_context()

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        self.server_socket.settimeout(1.0)
        self.is_running = True
        print(f"Server listening on {self.host}:{self.port}")

        self.accept_thread = threading.Thread(target=self.accept_connections, args=(context,))
        self.accept_thread.daemon = True
        self.accept_thread.start()

    def accept_connections(self, context):
        while self.is_running:
            try:
                conn, addr = self.server_socket.accept()
                print(f"Connection from {addr}")
                self.handle_client_connection(conn, addr, context)
            except socket.timeout:
                continue
            except Exception as e:
                if self.is_running:
                    print(f"Error accepting connection: {e}")
                break

    def handle_client_connection(self, conn, addr, context):
        """Handles a new client connection in a separate thread."""
        thread = threading.Thread(target=self.client_thread, args=(conn, addr, context))
        thread.daemon = True
        thread.start()

    def client_thread(self, conn, addr, context):
        """The main loop for a single client connection."""
        ssl_sock = None
        try:
            ssl_sock = self.secure_socket.wrap_socket(context, conn, server_side=True)
            network_manager = NetworkManager(ssl_sock)

            server_private_key, server_public_key = CryptoUtils.generate_ecc_key_pair()
            serialized_server_pk = CryptoUtils.serialize_ecc_public_key(server_public_key)
            
            print(f"Server sending public key to {addr}")
            network_manager.send_message(MESSAGE_TYPE_TEXT, serialized_server_pk)
            
            result = network_manager.receive_message()
            if not result or not result[1]:
                raise ConnectionError("Failed to receive client public key.")
            
            msg_type, client_pk_bytes = result
            client_public_key = CryptoUtils.deserialize_ecc_public_key(client_pk_bytes)
            
            shared_secret = CryptoUtils.derive_shared_secret(server_private_key, client_public_key)
            aes_key, _ = CryptoUtils.generate_aes_key_from_password(shared_secret.x.to_bytes(32, 'big'))

            print(f"Key exchange successful with {addr}")

            with self.lock:
                self.clients[addr] = {
                    'socket': ssl_sock,
                    'network_manager': network_manager,
                    'aes_key': aes_key
                }

            # 🆕 The main loop now correctly handles timeouts without exiting the thread
            while self.is_running:
                try:
                    msg_type, encrypted_payload = network_manager.receive_message()
                    if not encrypted_payload:
                        continue
                    
                    print(f"Server received encrypted message from {addr}: {encrypted_payload}")
                    
                    payload = json.loads(encrypted_payload)
                    nonce = bytes.fromhex(payload['nonce'])
                    ciphertext = bytes.fromhex(payload['ciphertext'])
                    tag = bytes.fromhex(payload['tag'])
                    
                    decrypted_content = CryptoUtils.decrypt_aes_gcm(aes_key, nonce, ciphertext, tag).decode('utf-8')
                    
                    print(f"Server decrypted message from {addr} to: '{decrypted_content}'")
                    
                    message = Message.from_dict(json.loads(decrypted_content))
                    print(f"Received message from {addr}: {message.content}")

                    print(f"Server is about to broadcast message from {addr}.")
                    self.broadcast(message.to_dict(), sender_addr=addr)
                except socket.timeout:
                    # 🆕 Timeout is a normal event when there's no data. We continue the loop.
                    continue
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"Error decrypting or decoding message from {addr}: {e}")
                    continue

        except (socket.error, ssl.SSLError) as e:
            print(f"Client {addr} disconnected due to an error: {e}")
        finally:
            if ssl_sock:
                self.remove_client(addr)

    def broadcast(self, message_data, sender_addr):
        """Broadcasts a message to all connected clients, including the sender."""
        with self.lock:
            print(f"Server broadcasting a message from {sender_addr}")
            for addr, client_info in list(self.clients.items()):
                try:
                    aes_key = client_info['aes_key']
                    network_manager = client_info['network_manager']
                    
                    plaintext_message = json.dumps(message_data).encode('utf-8')
                    nonce, ciphertext, tag = CryptoUtils.encrypt_aes_gcm(aes_key, plaintext_message)
                    
                    encrypted_payload = {
                        'nonce': nonce.hex(),
                        'ciphertext': ciphertext.hex(),
                        'tag': tag.hex()
                    }
                    serialized_payload = json.dumps(encrypted_payload).encode('utf-8')

                    # Debug: Server sending encrypted message to client
                    print(f"Server sending encrypted message '{ciphertext.hex()}' to client {addr}")
                    
                    network_manager.send_message(MESSAGE_TYPE_TEXT, serialized_payload)
                except Exception as e:
                    print(f"Error broadcasting to client {addr}: {e}")
                    self.remove_client(addr)

    def remove_client(self, addr):
        """Removes a client from the server's list."""
        with self.lock:
            if addr in self.clients:
                print(f"Removing client {addr}")
                self.clients[addr]['socket'].close()
                del self.clients[addr]

if __name__ == '__main__':
    cert_file = "cert.pem"
    key_file = "key.pem"
    server = SecureChatServer(SERVER_HOST, SERVER_PORT, cert_file, key_file)
    server.start()