import os
import json
from base64 import b64encode, b64decode
from Cryptodome.PublicKey import ECC
from Cryptodome.Cipher import AES
from Cryptodome.Hash import SHA256
from Cryptodome.Protocol.KDF import PBKDF2
from Cryptodome.PublicKey.ECC import EccPoint as ECCPoint
from Cryptodome.Util.number import long_to_bytes, bytes_to_long


class CryptoUtils:
    """
    A utility class for cryptographic operations.
    """
    
    @staticmethod
    def generate_ecc_key_pair():
        """Generates an Elliptic Curve key pair."""
        key = ECC.generate(curve='P-256')
        return key, key.public_key()
    
    @staticmethod
    def serialize_ecc_public_key(public_key):
        """Serializes a public key to a byte string."""
        return public_key.export_key(format='DER')
    
    @staticmethod
    def deserialize_ecc_public_key(serialized_key):
        """Deserializes a public key from a byte string."""
        try:
            return ECC.import_key(serialized_key)
        except Exception as e:
            print(f"Error deserializing key: {e}")
            return None
    
    @staticmethod
    def derive_shared_secret(private_key, public_key_other):
        """Derives a shared secret using ECDH."""
        # The private key is an integer, the public key is an EccPoint.
        # This performs a scalar multiplication to get the shared secret point.
        shared_secret_point = private_key.d * public_key_other.pointQ
        return shared_secret_point

    @staticmethod
    def generate_aes_key_from_password(password, salt=b'SecureChatFixedSalt'):
        """
        Generates a deterministic AES key from a password and a fixed salt.
        This ensures both client and server generate the same key from the same shared secret.
        """
        if not isinstance(salt, bytes):
            salt = salt.encode('utf-8')
        
        # Use PBKDF2 for key derivation
        key = PBKDF2(password, salt, dkLen=32, count=100000, hmac_hash_module=SHA256)
        return key, salt

    @staticmethod
    def encrypt_aes_gcm(key, plaintext):
        """Encrypts plaintext using AES-256 GCM."""
        cipher = AES.new(key, AES.MODE_GCM)
        ciphertext, tag = cipher.encrypt_and_digest(plaintext)
        return cipher.nonce, ciphertext, tag

    @staticmethod
    def decrypt_aes_gcm(key, nonce, ciphertext, tag):
        """Decrypts AES-256 GCM ciphertext and verifies the tag."""
        cipher = AES.new(key, AES.MODE_GCM, nonce)
        plaintext = cipher.decrypt_and_verify(ciphertext, tag)
        return plaintext