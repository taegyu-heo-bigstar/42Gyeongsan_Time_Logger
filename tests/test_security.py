from security import (
    create_session_token,
    hash_password,
    verify_password,
    verify_session_token,
)


SECRET = "a-test-session-secret-that-is-longer-than-32-characters"


def test_password_hash_verifies_without_storing_plaintext():
    encoded = hash_password("correct horse battery staple", iterations=100_000)
    assert "correct horse battery staple" not in encoded
    assert verify_password("correct horse battery staple", encoded)
    assert not verify_password("wrong password", encoded)


def test_malformed_password_hash_is_rejected():
    assert not verify_password("password", "not-a-valid-hash")


def test_session_token_expires():
    token = create_session_token(SECRET, ttl_seconds=60, now=1_000)
    assert verify_session_token(token, SECRET, now=1_059)
    assert not verify_session_token(token, SECRET, now=1_060)


def test_tampered_session_token_is_rejected():
    token = create_session_token(SECRET, ttl_seconds=60, now=1_000)
    assert not verify_session_token(f"{token}x", SECRET, now=1_001)
