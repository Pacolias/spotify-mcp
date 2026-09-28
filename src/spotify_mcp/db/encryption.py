"""Encryption at rest for third-party secrets (users' Spotify tokens).

Fernet (from `cryptography`) is authenticated encryption: a ciphertext that
was tampered with, or encrypted under another key, fails to decrypt instead
of producing garbage.
"""

from cryptography.fernet import Fernet

from spotify_mcp.config import settings


def _fernet() -> Fernet:
    return Fernet(settings.token_encryption_key.get_secret_value())


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    return _fernet().decrypt(ciphertext.encode()).decode()
