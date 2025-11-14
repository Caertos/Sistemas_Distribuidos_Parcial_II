from passlib.hash import pbkdf2_sha256
from passlib.exc import UnknownHashError
import hashlib

# Legacy static hash used by the k8s populate script (not a bcrypt hash).
# The populate script inserts the same hex string for all seeded users.
LEGACY_STATIC_HASH = "bc44a1755bfe54b6efa2abb783f19144511eb277efc6f8f9088df7b67b46614b"


def hash_password(password: str) -> str:
    # Use PBKDF2-SHA256 which does not rely on the bcrypt C backend and
    # avoids the 72-byte limitation. It's reasonably secure for this
    # application and available in passlib without bcrypt.
    return pbkdf2_sha256.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password with backward-compatibility for the legacy seeded users.

    - First try passlib (bcrypt).
    - If the stored hash is the legacy static hex from the population script,
      accept the plaintext 'secret' (used by the population script) as valid.
    - As a final fallback, attempt a straight sha256 comparison (in case of
      simple hex-encoded SHA256 hashes).
    """
    try:
        # If the stored hash is a pbkdf2_sha256 hash, verify with that.
        if pbkdf2_sha256.identify(hashed_password):
            return pbkdf2_sha256.verify(plain_password, hashed_password)
    except UnknownHashError:
        # Continue to fallback checks
        pass

    # Legacy special-case: the population script used a fixed hex value.
    if hashed_password == LEGACY_STATIC_HASH and plain_password == "secret":
        return True

    # Fallback: compare sha256 hex digest (many simple scripts store hex hashes)
    try:
        if len(hashed_password) == 64:
            sha = hashlib.sha256(plain_password.encode()).hexdigest()
            if sha == hashed_password:
                return True
    except Exception:
        pass

    return False
