from __future__ import annotations

import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

SALT_BYTES = 16
NONCE_BYTES = 12
KEY_BYTES = 32
KDF_ITERATIONS = 390_000


def _build_key(secret: str, salt: bytes) -> bytes:
    normalized_secret = secret.strip()

    if not normalized_secret:
        raise RuntimeError("Не задан TOKEN_ENCRYPTION_SECRET")

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_BYTES,
        salt=salt,
        iterations=KDF_ITERATIONS,
    )

    return kdf.derive(normalized_secret.encode("utf-8"))


def encrypt_token(token: str, secret: str) -> tuple[bytes, bytes, bytes]:
    normalized_token = token.strip()

    if not normalized_token:
        raise ValueError("Пустой iTick токен")

    salt = os.urandom(SALT_BYTES)
    nonce = os.urandom(NONCE_BYTES)
    key = _build_key(secret, salt)
    cipher = AESGCM(key)
    ciphertext = cipher.encrypt(nonce, normalized_token.encode("utf-8"), None)

    return ciphertext, nonce, salt


def decrypt_token(ciphertext: bytes, nonce: bytes, salt: bytes, secret: str) -> str:
    key = _build_key(secret, salt)
    cipher = AESGCM(key)
    plain = cipher.decrypt(nonce, ciphertext, None)

    return plain.decode("utf-8")
