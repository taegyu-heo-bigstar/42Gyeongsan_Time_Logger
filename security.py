import base64
import binascii
import hashlib
import hmac
import secrets
import time


PASSWORD_ALGORITHM = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 600_000
SESSION_VERSION = "v1"


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def hash_password(password: str, iterations: int = PASSWORD_ITERATIONS) -> str:
    if not password:
        raise ValueError("Password must not be empty.")

    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return "$".join(
        [PASSWORD_ALGORITHM, str(iterations), _b64encode(salt), _b64encode(digest)]
    )


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt_text, expected_text = encoded_hash.split("$")
        if algorithm != PASSWORD_ALGORITHM:
            return False

        iterations = int(iterations_text)
        if iterations < 100_000 or iterations > 2_000_000:
            return False

        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            _b64decode(salt_text),
            iterations,
        )
        expected = _b64decode(expected_text)
        return hmac.compare_digest(actual, expected)
    except (binascii.Error, TypeError, ValueError):
        return False


def create_session_token(secret: str, ttl_seconds: int, now: int | None = None) -> str:
    issued_at = int(time.time()) if now is None else now
    expires_at = issued_at + ttl_seconds
    payload = f"{SESSION_VERSION}.{expires_at}.{secrets.token_urlsafe(16)}"
    encoded_payload = _b64encode(payload.encode("utf-8"))
    signature = hmac.new(
        secret.encode("utf-8"),
        encoded_payload.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{encoded_payload}.{_b64encode(signature)}"


def verify_session_token(token: str, secret: str, now: int | None = None) -> bool:
    try:
        encoded_payload, signature_text = token.split(".", 1)
        expected_signature = hmac.new(
            secret.encode("utf-8"),
            encoded_payload.encode("ascii"),
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(_b64decode(signature_text), expected_signature):
            return False

        version, expires_text, _nonce = _b64decode(encoded_payload).decode("utf-8").split(".", 2)
        current_time = int(time.time()) if now is None else now
        return version == SESSION_VERSION and current_time < int(expires_text)
    except (binascii.Error, TypeError, ValueError, UnicodeDecodeError):
        return False
