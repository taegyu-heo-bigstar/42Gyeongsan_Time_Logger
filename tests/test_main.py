import importlib
import os
import sys
import types

from fastapi.testclient import TestClient


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


os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "test-password")
sys.modules["supabase"] = types.SimpleNamespace(
    create_client=lambda *_args, **_kwargs: DuplicateRunningDB()
)
sys.modules["dotenv"] = types.SimpleNamespace(load_dotenv=lambda: None)
sys.modules.pop("main", None)
main = importlib.import_module("main")
client = TestClient(main.app)
AUTH = {"X-Admin-Password": "test-password"}


def test_admin_endpoint_requires_password():
    response = client.get("/logs/current")
    assert response.status_code == 401


def test_month_rejects_out_of_range_value():
    response = client.get("/logs/month?year=2026&month=13", headers=AUTH)
    assert response.status_code == 422


def test_manual_log_rejects_invalid_time_format():
    response = client.post(
        "/logs/manual",
        headers=AUTH,
        json={
            "work_date": "2026-06-22",
            "start_time": "not-a-time",
            "end_time": "18:00",
        },
    )
    assert response.status_code == 422


def test_manual_log_rejects_end_before_start():
    response = client.post(
        "/logs/manual",
        headers=AUTH,
        json={
            "work_date": "2026-06-22",
            "start_time": "18:00",
            "end_time": "09:00",
        },
    )
    assert response.status_code == 400


def test_start_translates_unique_constraint_to_conflict():
    response = client.post("/logs/start", headers=AUTH, json={})
    assert response.status_code == 409
    assert response.json()["detail"] == "이미 진행 중인 로그가 있습니다."
