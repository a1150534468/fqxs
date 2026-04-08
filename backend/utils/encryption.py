"""
Encryption utilities for sensitive data storage.
"""
from cryptography.fernet import Fernet
from django.conf import settings
import base64
import hashlib


def get_encryption_key() -> bytes:
    """
    Generate encryption key from Django SECRET_KEY.
    This ensures the key is consistent across app restarts.
    """
    # Use SECRET_KEY to derive a Fernet-compatible key
    key_material = settings.SECRET_KEY.encode()
    # Hash to get consistent 32 bytes
    hashed = hashlib.sha256(key_material).digest()
    # Fernet requires base64-encoded 32-byte key
    return base64.urlsafe_b64encode(hashed)


def encrypt_text(plaintext: str) -> str:
    """
    Encrypt plaintext string.

    Args:
        plaintext: Text to encrypt

    Returns:
        Base64-encoded encrypted text
    """
    if not plaintext:
        return ''

    key = get_encryption_key()
    f = Fernet(key)
    encrypted = f.encrypt(plaintext.encode())
    return encrypted.decode()


def decrypt_text(encrypted_text: str) -> str:
    """
    Decrypt encrypted string.

    Args:
        encrypted_text: Base64-encoded encrypted text

    Returns:
        Decrypted plaintext
    """
    if not encrypted_text:
        return ''

    key = get_encryption_key()
    f = Fernet(key)
    decrypted = f.decrypt(encrypted_text.encode())
    return decrypted.decode()
