# secure_socket.py

import ssl
import socket
import os
import datetime
import ipaddress

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.x509.oid import NameOID
from config import SERVER_HOST, SERVER_PORT

class SecureSocket:
    """
    A class to manage secure socket connections using TLS/SSL.
    """
    def __init__(self, certfile, keyfile):
        """
        Initializes the SecureSocket with paths to the certificate and key files.
        """
        self.certfile = certfile
        self.keyfile = keyfile

    def create_server_context(self):
        """
        Creates and returns a server-side SSLContext object.
        """
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(certfile=self.certfile, keyfile=self.keyfile)
        context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1  # Disable old, insecure protocols
        return context

    def create_client_context(self):
        """
        Creates and returns a client-side SSLContext object.
        """
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=self.certfile)
        context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
        return context

    def wrap_socket(self, context, sock, server_side=False, server_hostname=None):
        """
        Wraps a socket with an SSL context.
        """
        return context.wrap_socket(sock, server_side=server_side, server_hostname=server_hostname)

    @staticmethod
    def generate_certificates(cert_path="cert.pem", key_path="key.pem"):
        """
        Generates a new self-signed certificate and private key.
        """
        if os.path.exists(cert_path) and os.path.exists(key_path):
            print("Certificates already exist. Skipping generation.")
            return

        print("Generating new SSL certificate...")
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, u"US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"Florida"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, u"Titusville"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Secure Chat"),
            x509.NameAttribute(NameOID.COMMON_NAME, u"localhost"),
        ])
        
        san_list = [
            x509.DNSName(u"localhost"),
            x509.IPAddress(ipaddress.IPv4Address(u"127.0.0.1"))
        ]

        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.utcnow()
        ).not_valid_after(
            datetime.datetime.utcnow() + datetime.timedelta(days=365)
        ).add_extension(
            x509.SubjectAlternativeName(san_list),
            critical=False,
        ).sign(key, hashes.SHA256())

        with open(key_path, "wb") as f:
            f.write(key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            ))
        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        print("Certificates generated successfully.")