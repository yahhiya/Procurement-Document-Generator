"""
Password hashing and session-token helpers.

- Passwords are never stored in plain text. We store a random "salt" plus a
  hash produced by PBKDF2 (a standard, slow-by-design hashing algorithm built
  into Python — no extra library needed for this part).
- After login, the user gets a signed token (JWT) instead of re-sending their
  password on every request. The token carries their id, email, and role, and
  expires after 24 hours.
"""

import hashlib
import hmac
import os
import time

import jwt

# In production, set a real SECRET_KEY as an environment variable — never
# commit a real secret to git. This fallback is fine for local development.
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me-before-deploying")
TOKEN_TTL_SECONDS = 60 * 60 * 24  # 24 hours
PBKDF2_ITERATIONS = 200_000


def hash_password(password: str) -> tuple[str, str]:
    """Returns (salt_hex, hash_hex) for a new password."""
    salt = os.urandom(16)
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    return salt.hex(), pwd_hash.hex()


def verify_password(password: str, salt_hex: str, expected_hash_hex: str) -> bool:
    salt = bytes.fromhex(salt_hex)
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    return hmac.compare_digest(pwd_hash.hex(), expected_hash_hex)


def create_token(user_id: int, email: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": int(time.time()) + TOKEN_TTL_SECONDS,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> dict:
    """Raises jwt.PyJWTError if the token is invalid or expired."""
    return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
