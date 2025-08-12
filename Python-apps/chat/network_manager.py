# network_manager.py

import socket
import struct
import json
import threading
import ssl
import datetime
from secure_socket import SecureSocket
from crypto_utils import CryptoUtils
from config import TIMEOUT

class NetworkManager:
    HEADER_LENGTH = 5

    def __init__(self, sock=None):
        self._sock = sock
        if self._sock:
            self._sock.settimeout(TIMEOUT)

    def connect(self, host, port):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(TIMEOUT)
        self._sock.connect((host, port))

    def close(self):
        if self._sock:
            self._sock.close()
            self._sock = None

    def send_message(self, message_type, message_payload):
        self._send_message_static(self._sock, message_type, message_payload)

    @staticmethod
    def _send_message_static(sock, message_type, message_payload):
        print(f"NetworkManager (static) sending message of type '{message_type}' with payload length {len(message_payload)} bytes.")
        header = struct.pack("!BI", message_type, len(message_payload))
        sock.sendall(header + message_payload)

    def receive_message(self):
        return self._receive_message_from_static(self._sock)

    @staticmethod
    def _receive_message_from_static(sock):
        try:
            header = NetworkManager._recv_all(sock, NetworkManager.HEADER_LENGTH)
            if not header:
                return None, None
            
            message_type, message_length = struct.unpack("!BI", header)
            
            print(f"NetworkManager received header: type '{message_type}', length {message_length} bytes. Fetching payload.")
            
            payload = NetworkManager._recv_all(sock, message_length)
            if not payload:
                return None, None
            
            return message_type, payload
        except (socket.timeout, socket.error) as e:
            # 🆕 The change is here: print a keep-alive message instead of an error
            now = datetime.datetime.now()
            print(f"Keep Alive Date({now.strftime('%Y-%m-%d')}) Time({now.strftime('%H:%M:%S')})")
            return None, None
    
    @staticmethod
    def _recv_all(sock, n):
        data = bytearray()
        while len(data) < n:
            try:
                packet = sock.recv(n - len(data))
            except (socket.timeout, ssl.SSLError) as e:
                # 🆕 The change is here: simply re-raise the timeout exception
                raise socket.timeout(str(e))
            if not packet:
                return None
            data.extend(packet)
        return bytes(data)

    def secure_key_exchange(self, username):
        raise NotImplementedError("This method needs to be implemented for client-side key exchange logic.")

    @staticmethod
    def secure_key_exchange_server(client_socket):
        raise NotImplementedError("This method needs to be implemented for server-side key exchange logic.")