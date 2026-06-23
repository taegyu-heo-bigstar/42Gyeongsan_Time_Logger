import importlib

import pytest


def reload_config():
    import config

    return importlib.reload(config)


def set_required_env(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "test-key")
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", "pbkdf2_sha256$100000$salt$digest")
    monkeypatch.setenv("SESSION_SECRET", "test-session-secret-with-at-least-32-characters")


def test_load_settings_rejects_invalid_session_ttl(monkeypatch):
    set_required_env(monkeypatch)
    monkeypatch.setenv("SESSION_TTL_SECONDS", "not-a-number")
    config = reload_config()

    with pytest.raises(RuntimeError, match="SESSION_TTL_SECONDS must be an integer"):
        config.load_settings()


def test_load_settings_parses_optional_values(monkeypatch):
    set_required_env(monkeypatch)
    monkeypatch.setenv("SESSION_TTL_SECONDS", "600")
    monkeypatch.setenv("COOKIE_SECURE", "false")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://app.example.com, https://admin.example.com")
    config = reload_config()

    settings = config.load_settings()

    assert settings.session_ttl_seconds == 600
    assert settings.cookie_secure is False
    assert settings.allowed_origins == [
        "https://app.example.com",
        "https://admin.example.com",
    ]
