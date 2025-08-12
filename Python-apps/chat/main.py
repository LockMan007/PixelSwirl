# main.py

import sys
import threading
from server import SecureChatServer
from client import SecureChatClient
from config import SERVER_HOST, SERVER_PORT
from secure_socket import SecureSocket

def run_server():
    """Starts the secure chat server."""
    cert_file = "cert.pem"
    key_file = "key.pem"
    server = SecureChatServer(SERVER_HOST, SERVER_PORT, cert_file, key_file)
    server.start()

def run_client():
    """Starts the secure chat client."""
    cert_file = "cert.pem"
    client = SecureChatClient(SERVER_HOST, SERVER_PORT, cert_file)
    client.run()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py [client|server]")
        sys.exit(1)

    role = sys.argv[1].lower()

    if role == "server":
        print("Starting Secure Chat Server...")
        SecureSocket.generate_certificates()
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        print("Server is running. Press Ctrl+C to stop.")
        try:
            # Keep the main thread alive so the server thread can run
            while True:
                pass
        except KeyboardInterrupt:
            print("Server shutting down.")
            sys.exit(0)

    elif role == "client":
        print("Starting Secure Chat Client...")
        SecureSocket.generate_certificates()
        run_client()

    else:
        print("Invalid argument. Please use 'client' or 'server'.")
        sys.exit(1)