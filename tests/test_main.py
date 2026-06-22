import importlib
import os
import sys
import types
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from security import hash_password


class DuplicateRunningDB:
    def __init__(self):
        self.mode = "select"

    def table(self, _name):
        return self

    def select(self, _columns):
        self.mode = "select"
        return self

    def eq(self, _column, _value):
        return self

    def gte(self, _column, _value):
        return self

    def lt(self, _column, _value):
        return self

    def order(self, _column):
        return self

    def limit(self, _count):
        return self

    def insert(self, _payload):
        self.mode = "insert"
        return self

    def execute(self):
        if self.mode == "insert":
            raise Exception("23505 time_logs_single_running_idx")
        return type("Result", (), {"data": []})()


class RecordingUpdateDB:
    def __init__(self):
        self.filters = []
        self.payload = None

    def table(self, _name):
        return self

    def update(self, payload):
        self.payload = payload
        return self

    def eq(self, column, value):
        self.filters.append((column, value))
        return self

    def execute(self):
        return type("Result", (), {"data": [self.payload]})()


os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")
os.environ.setdefault(
    "ADMIN_PASSWORD_HASH", hash_password("test-password", iterations=100_000)
)
os.environ.setdefault("SESSION_SECRET", "test-session-secret-with-at-least-32-characters")
os.environ.setdefault("COOKIE_SECURE", "true")
sys.modules["supabase"] = types.SimpleNamespace(
    create_client=lambda *_args, **_kwargs: DuplicateRunningDB()
)
sys.modules["dotenv"] = types.SimpleNamespace(load_dotenv=lambda: None)
sys.modules.pop("main", None)
main = importlib.import_module("main")


def make_client():
    return TestClient(main.app, base_url="https://testserver")


def make_authenticated_client():
    client = make_client()
    response = client.post("/login", json={"password": "test-password"})
    assert response.status_code == 200
    return client


def test_admin_endpoint_requires_password():
    client = make_client()
    response = client.get("/logs/current")
    assert response.status_code == 401


def test_login_sets_secure_http_only_session_cookie():
    client = make_client()
    response = client.post("/login", json={"password": "test-password"})
    cookie = response.headers["set-cookie"].lower()

    assert response.status_code == 200
    assert "time_logger_session=" in cookie
    assert "httponly" in cookie
    assert "secure" in cookie
    assert "samesite=lax" in cookie


def test_wrong_password_does_not_create_session():
    client = make_client()
    response = client.post("/login", json={"password": "wrong-password"})
    assert response.status_code == 401
    assert "time_logger_session=" not in response.headers.get("set-cookie", "")


def test_logout_invalidates_session():
    client = make_authenticated_client()
    assert client.get("/session").status_code == 200
    assert client.post("/logout").status_code == 200
    assert client.get("/session").status_code == 401


def test_month_rejects_out_of_range_value():
    client = make_authenticated_client()
    response = client.get("/logs/month?year=2026&month=13")
    assert response.status_code == 422


def test_month_returns_summaries_instead_of_raw_logs():
    client = make_authenticated_client()
    response = client.get("/logs/month?year=2026&month=6")
    data = response.json()

    assert response.status_code == 200
    assert data["days"] == []
    assert "logs" not in data


def test_manual_log_rejects_invalid_time_format():
    client = make_authenticated_client()
    response = client.post(
        "/logs/manual",
        json={
            "work_date": "2026-06-22",
            "start_time": "not-a-time",
            "end_time": "18:00",
        },
    )
    assert response.status_code == 422


def test_manual_log_rejects_end_before_start():
    client = make_authenticated_client()
    response = client.post(
        "/logs/manual",
        json={
            "work_date": "2026-06-22",
            "start_time": "18:00",
            "end_time": "09:00",
        },
    )
    assert response.status_code == 400


def test_start_translates_unique_constraint_to_conflict():
    client = make_authenticated_client()
    response = client.post("/logs/start", json={})
    assert response.status_code == 409
    assert response.json()["detail"] == "이미 진행 중인 로그가 있습니다."


def test_auto_stop_cutoff_uses_next_kst_midnight_when_earlier():
    start = datetime(2026, 6, 22, 10, 0, tzinfo=timezone.utc)
    assert main.auto_stop_cutoff(start) == datetime(
        2026, 6, 22, 15, 0, tzinfo=timezone.utc
    )


def test_auto_stop_cutoff_uses_twelve_hours_when_earlier():
    start = datetime(2026, 6, 22, 0, 0, tzinfo=timezone.utc)
    assert main.auto_stop_cutoff(start) == datetime(
        2026, 6, 22, 12, 0, tzinfo=timezone.utc
    )


def test_auto_stop_update_is_conditional_on_running_status(monkeypatch):
    start = datetime(2026, 6, 22, 0, 0, tzinfo=timezone.utc)
    recording_db = RecordingUpdateDB()
    monkeypatch.setattr(main, "db", recording_db)
    monkeypatch.setattr(
        main,
        "get_running_log",
        lambda: {"id": 42, "start_time": start.isoformat(), "status": "RUNNING"},
    )
    monkeypatch.setattr(
        main,
        "now_utc",
        lambda: datetime(2026, 6, 22, 13, 0, tzinfo=timezone.utc),
    )

    main.auto_stop_if_needed()

    assert ("id", 42) in recording_db.filters
    assert ("status", "RUNNING") in recording_db.filters
    assert recording_db.payload["end_time"] == datetime(
        2026, 6, 22, 12, 0, tzinfo=timezone.utc
    ).isoformat()


def test_debug_endpoint_is_not_exposed():
    client = make_authenticated_client()
    assert client.get("/debug/db").status_code == 404
