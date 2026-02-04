"""
Encryption Service for API Keys
Provides secure encryption/decryption for storing user API keys in database
"""

import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Optional
from loguru import logger


class EncryptionService:
    """Service for encrypting/decrypting sensitive data like API keys"""
    
    def __init__(self):
        # Get encryption key from environment or generate a default (for development)
        # In production, this should be a strong secret stored securely
        encryption_key = os.getenv("ENCRYPTION_KEY")
        
        if not encryption_key:
            # Generate a default key for development (NOT for production!)
            logger.warning("⚠️ ENCRYPTION_KEY not set - using default key (NOT SECURE for production!)")
            # Default key - MUST be changed in production
            default_key = b"default_encryption_key_32_bytes_long!!"
            encryption_key = base64.urlsafe_b64encode(default_key).decode('utf-8')
        
        try:
            # Ensure key is proper Fernet format (32 bytes base64-encoded)
            if len(base64.urlsafe_b64decode(encryption_key.encode())) != 32:
                # Derive a proper key from the provided string
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=b'fixed_salt_for_key_derivation',  # In production, use random salt stored separately
                    iterations=100000,
                )
                key = kdf.derive(encryption_key.encode())
                encryption_key = base64.urlsafe_b64encode(key).decode('utf-8')
            
            self.cipher = Fernet(encryption_key.encode())
        except Exception as e:
            logger.error(f"❌ Failed to initialize encryption: {e}")
            raise
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt a plaintext string"""
        if not plaintext:
            return ""
        try:
            encrypted_bytes = self.cipher.encrypt(plaintext.encode('utf-8'))
            return base64.urlsafe_b64encode(encrypted_bytes).decode('utf-8')
        except Exception as e:
            logger.error(f"❌ Encryption failed: {e}")
            raise
    
    def decrypt(self, ciphertext: str) -> Optional[str]:
        """Decrypt a ciphertext string"""
        if not ciphertext:
            return None
        try:
            decoded_bytes = base64.urlsafe_b64decode(ciphertext.encode('utf-8'))
            decrypted_bytes = self.cipher.decrypt(decoded_bytes)
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            logger.error(f"❌ Decryption failed: {e}")
            return None


# Singleton instance
encryption_service = EncryptionService()
