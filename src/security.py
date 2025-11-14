"""
Cryptographic utilities for SilentLock password manager.
Provides secure encryption/decryption for stored credentials.
"""

import os
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import secrets


class SecurityManager:
    """Handles all cryptographic operations for the password manager."""
    
    def __init__(self):
        self.backend = default_backend()
    
    def derive_key(self, password: str, salt: bytes) -> bytes:
        """Derive a key from password using PBKDF2."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 256-bit key
            salt=salt,
            iterations=100000,
            backend=self.backend
        )
        return kdf.derive(password.encode())
    
    def generate_salt(self) -> bytes:
        """Generate a random salt."""
        return os.urandom(16)
    
    def encrypt_data(self, data: str, password: str) -> dict:
        """Encrypt data using AES-256-GCM."""
        salt = self.generate_salt()
        key = self.derive_key(password, salt)
        
        # Generate a random IV
        iv = os.urandom(12)  # 96-bit IV for GCM
        
        # Create cipher
        cipher = Cipher(algorithms.AES(key), modes.GCM(iv), backend=self.backend)
        encryptor = cipher.encryptor()
        
        # Encrypt data
        ciphertext = encryptor.update(data.encode()) + encryptor.finalize()
        
        return {
            'ciphertext': base64.b64encode(ciphertext).decode(),
            'salt': base64.b64encode(salt).decode(),
            'iv': base64.b64encode(iv).decode(),
            'tag': base64.b64encode(encryptor.tag).decode()
        }
    
    def decrypt_data(self, encrypted_data: dict, password: str) -> str:
        """Decrypt data using AES-256-GCM."""
        try:
            # Decode components
            ciphertext = base64.b64decode(encrypted_data['ciphertext'])
            salt = base64.b64decode(encrypted_data['salt'])
            iv = base64.b64decode(encrypted_data['iv'])
            tag = base64.b64decode(encrypted_data['tag'])
            
            # Derive key
            key = self.derive_key(password, salt)
            
            # Create cipher
            cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag), backend=self.backend)
            decryptor = cipher.decryptor()
            
            # Decrypt data
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            return plaintext.decode()
            
        except Exception as e:
            raise ValueError("Invalid password or corrupted data") from e
    
    def secure_delete(self, data: str) -> None:
        """Securely overwrite sensitive data in memory."""
        # In Python, we can't directly overwrite memory, but we can help GC
        # by creating a new string filled with random data
        if data:
            for _ in range(len(data)):
                data = secrets.token_hex(len(data))
            del data