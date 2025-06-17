import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization
import argon2
from typing import Optional
import secrets
import string

class SecurityManager:
    def __init__(self):
        self.salt = os.urandom(16)
        self._fernet = None
        self._master_key = None
        self._ph = argon2.PasswordHasher(
            time_cost=3,      # Reduced from default for better performance
            memory_cost=65536, # 64MB
            parallelism=4,    # Number of parallel threads
            hash_len=32,      # Length of the hash in bytes
            salt_len=16       # Length of the salt in bytes
        )
        
    def generate_master_key(self, password: str) -> bytes:
        """Generate a master key from the user's password using Argon2id."""
        self._master_key = self._ph.hash(password.encode()).encode()
        return self._master_key
    
    def verify_master_password(self, password: str, stored_hash: str) -> bool:
        """Verify the master password against the stored hash."""
        try:
            self._ph.verify(stored_hash, password.encode())
            return True
        except argon2.exceptions.VerifyMismatchError:
            return False
    
    def initialize_encryption(self, master_key: bytes):
        """Initialize the Fernet encryption with the master key."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,  # Reduced from default for better performance
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_key))
        self._fernet = Fernet(key)
    
    def encrypt_data(self, data: str) -> bytes:
        """Encrypt data using Fernet symmetric encryption."""
        if not self._fernet:
            raise RuntimeError("Encryption not initialized")
        return self._fernet.encrypt(data.encode())
    
    def decrypt_data(self, encrypted_data: bytes) -> str:
        """Decrypt data using Fernet symmetric encryption."""
        if not self._fernet:
            raise RuntimeError("Encryption not initialized")
        return self._fernet.decrypt(encrypted_data).decode()
    
    def generate_password(self, length: int = 16, use_uppercase: bool = True,
                         use_lowercase: bool = True, use_numbers: bool = True,
                         use_special: bool = True) -> str:
        """Generate a secure random password."""
        # Define character sets
        chars = ''
        if use_uppercase:
            chars += string.ascii_uppercase
        if use_lowercase:
            chars += string.ascii_lowercase
        if use_numbers:
            chars += string.digits
        if use_special:
            chars += string.punctuation
            
        if not chars:
            raise ValueError("At least one character set must be selected")
        
        # Pre-calculate character sets for validation
        has_upper = use_uppercase and any(c.isupper() for c in chars)
        has_lower = use_lowercase and any(c.islower() for c in chars)
        has_digit = use_numbers and any(c.isdigit() for c in chars)
        has_special = use_special and any(not c.isalnum() for c in chars)
        
        # Generate password with validation
        while True:
            password = ''.join(secrets.choice(chars) for _ in range(length))
            if (not use_uppercase or any(c.isupper() for c in password)) and \
               (not use_lowercase or any(c.islower() for c in password)) and \
               (not use_numbers or any(c.isdigit() for c in password)) and \
               (not use_special or any(not c.isalnum() for c in password)):
                return password
    
    def secure_wipe(self, data: bytes):
        """Securely wipe sensitive data from memory."""
        if isinstance(data, str):
            data = data.encode()
        for i in range(len(data)):
            data[i:i+1] = os.urandom(1)
    
    def __del__(self):
        """Clean up sensitive data."""
        if self._master_key:
            self.secure_wipe(self._master_key)
        if self._fernet:
            self._fernet = None 