import os
from datetime import date, datetime, timedelta, timezone

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

if not SUPABASE_URL or not SUPABASE_KEY or not ADMIN_PASSWORD:
    raise RuntimeError("SUPABASE_URL, SUPABASE_KEY, ADMIN_PASSWORD가 필요합니다.")

db = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # toy project용
    allow_methods=["*"],
    allow_headers=["*"],
)

KST = timezone(timedelta(hours=9))


class LoginRequest(BaseModel):
    password: str


class StartRequest(BaseModel):
    work_date: date | None = None


def check_admin(x_admin_password: str = Header(alias="X-Admin-Password")):
    if x_admin_password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="관리자 비밀번호가 틀렸습니다.")


def now_utc():
    return datetime.now(timezone.utc)


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def local_date(dt):
    return dt.astimezone(KST).date()


def get_running_log():
    res = (
        db.table("time_logs")
        .select("*")
        .eq("status", "RUNNING")
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None


def auto_stop_if_needed():
    log = get_running_log()

    if not log:
        return

    start = parse_time(log["start_time"])
    now = now_utc()

    over_12_hours = now - start >= timedelta(hours=12)
    date_changed = local_date(start) != local_date(now)

    if not over_12_hours and not date_changed:
        return

    duration = int((now - start).total_seconds())

    (
        db.table("time_logs")
        .update({
            "end_time": now.isoformat(),
            "duration_seconds": duration,
            "status": "AUTO_STOPPED",
        })
        .eq("id", log["id"])
        .execute()
    )


@app.get("/")
def root():
    return {"message": "Time Logger API"}


@app.post("/login")
def login(data: LoginRequest):
    if data.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="비밀번호가 틀렸습니다.")

    return {"ok": True}


@app.get("/logs/current")
def current_log(_: None = Depends(check_admin)):
    auto_stop_if_needed()
    return {"current_log": get_running_log()}


@app.post("/logs/start")
def start_log(
    data: StartRequest | None = None,
    _: None = Depends(check_admin),
):
    auto_stop_if_needed()

    if get_running_log():
        raise HTTPException(status_code=400, detail="이미 진행 중인 로그가 있습니다.")

    work_date = data.work_date if data and data.work_date else local_date(now_utc())
    now = now_utc()

    res = (
        db.table("time_logs")
        .insert({
            "work_date": work_date.isoformat(),
            "start_time": now.isoformat(),
            "status": "RUNNING",
        })
        .execute()
    )

    return res.data[0]


@app.post("/logs/stop")
def stop_log(_: None = Depends(check_admin)):
    auto_stop_if_needed()

    log = get_running_log()

    if not log:
        raise HTTPException(status_code=400, detail="진행 중인 로그가 없습니다.")

    start = parse_time(log["start_time"])
    end = now_utc()
    duration = int((end - start).total_seconds())

    res = (
        db.table("time_logs")
        .update({
            "end_time": end.isoformat(),
            "duration_seconds": duration,
            "status": "COMPLETED",
        })
        .eq("id", log["id"])
        .execute()
    )

    return res.data[0]


@app.get("/logs/month")
def month_logs(
    year: int = Query(...),
    month: int = Query(...),
    _: None = Depends(check_admin),
):
    auto_stop_if_needed()

    start = date(year, month, 1)

    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)

    res = (
        db.table("time_logs")
        .select("*")
        .gte("work_date", start.isoformat())
        .lt("work_date", end.isoformat())
        .order("work_date")
        .order("start_time")
        .execute()
    )

    logs = res.data or []
    total = sum(log["duration_seconds"] or 0 for log in logs)

    return {
        "year": year,
        "month": month,
        "logs": logs,
        "total_duration_seconds": total,
    }


@app.get("/logs/day")
def day_logs(
    work_date: date = Query(...),
    _: None = Depends(check_admin),
):
    auto_stop_if_needed()

    res = (
        db.table("time_logs")
        .select("*")
        .eq("work_date", work_date.isoformat())
        .order("start_time")
        .execute()
    )

    return {
        "work_date": work_date.isoformat(),
        "logs": res.data or [],
    }t.data or [],
    }