import os
from dataclasses import dataclass

from dotenv import load_dotenv


SESSION_TTL_MIN_SECONDS = 300
SESSION_TTL_MAX_SECONDS = 86400


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    supabase_key: str
    admin_password_hash: str
    session_secret: str
    session_ttl_seconds: int
    cookie_secure: bool
    allowed_origins: list[str]


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is required.")
    return value


def _parse_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default

    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer.") from exc


def _parse_bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value.lower() not in {"0", "false", "no", "off"}


def _parse_origins_env(name: str) -> list[str]:
    return [origin.strip() for origin in os.getenv(name, "").split(",") if origin.strip()]


def load_settings() -> Settings:
    load_dotenv()

    session_secret = _required_env("SESSION_SECRET")
    if len(session_secret) < 32:
        raise RuntimeError("SESSION_SECRET must be at least 32 characters.")

    session_ttl_seconds = _parse_int_env("SESSION_TTL_SECONDS", 28800)
    if not SESSION_TTL_MIN_SECONDS <= session_ttl_seconds <= SESSION_TTL_MAX_SECONDS:
        raise RuntimeError(
            "SESSION_TTL_SECONDS must be between "
            f"{SESSION_TTL_MIN_SECONDS} and {SESSION_TTL_MAX_SECONDS}."
        )

    return Settings(
        supabase_url=_required_env("SUPABASE_URL"),
        supabase_key=_required_env("SUPABASE_KEY"),
        admin_password_hash=_required_env("ADMIN_PASSWORD_HASH"),
        session_secret=session_secret,
        session_ttl_seconds=session_ttl_seconds,
        cookie_secure=_parse_bool_env("COOKIE_SECURE", True),
        allowed_origins=_parse_origins_env("ALLOWED_ORIGINS"),
    )
