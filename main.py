import os
from datetime import date, datetime, time, timedelta, timezone

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client

from security import create_session_token, verify_password, verify_session_token

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH")
SESSION_SECRET = os.getenv("SESSION_SECRET")
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "28800"))
SESSION_COOKIE_NAME = "time_logger_session"
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "true").lower() != "false"
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]

if not SUPABASE_URL or not SUPABASE_KEY or not ADMIN_PASSWORD_HASH or not SESSION_SECRET:
    raise RuntimeError(
        "SUPABASE_URL, SUPABASE_KEY, ADMIN_PASSWORD_HASH, SESSION_SECRET가 필요합니다."
    )

if len(SESSION_SECRET) < 32:
    raise RuntimeError("SESSION_SECRET는 32자 이상이어야 합니다.")

if SESSION_TTL_SECONDS < 300 or SESSION_TTL_SECONDS > 86400:
    raise RuntimeError("SESSION_TTL_SECONDS는 300~86400 범위여야 합니다.")

db = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()

if ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

KST = timezone(timedelta(hours=9))


class LoginRequest(BaseModel):
    password: str


class StartRequest(BaseModel):
    work_date: date | None = None


def check_admin(request: Request):
    token = request.cookies.get(SESSION_COOKIE_NAME, "")
    if not verify_session_token(token, SESSION_SECRET):
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


def now_utc():
    return datetime.now(timezone.utc)


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def local_date(dt):
    return dt.astimezone(KST).date()


def auto_stop_cutoff(start):
    start_local = start.astimezone(KST)
    next_midnight_local = datetime.combine(
        start_local.date() + timedelta(days=1),
        time.min,
        tzinfo=KST,
    )
    return min(
        start + timedelta(hours=12),
        next_midnight_local.astimezone(timezone.utc),
    )


def get_running_log():
    try:
        res = (
            db.table("time_logs")
            .select("*")
            .eq("status", "RUNNING")
            .order("start_time")
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Supabase running log 조회 실패: {type(e).__name__}"
        )


def auto_stop_if_needed():
    log = get_running_log()

    if not log:
        return

    start = parse_time(log["start_time"])
    cutoff = auto_stop_cutoff(start)
    if now_utc() < cutoff:
        return

    duration = int((cutoff - start).total_seconds())

    (
        db.table("time_logs")
        .update({
            "end_time": cutoff.isoformat(),
            "duration_seconds": duration,
            "status": "AUTO_STOPPED",
        })
        .eq("id", log["id"])
        .eq("status", "RUNNING")
        .execute()
    )


@app.get("/")
def root():
    return {"message": "Time Logger API"}


@app.post("/login")
def login(data: LoginRequest, response: Response):
    if not verify_password(data.password, ADMIN_PASSWORD_HASH):
        raise HTTPException(status_code=401, detail="비밀번호가 틀렸습니다.")

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=create_session_token(SESSION_SECRET, SESSION_TTL_SECONDS),
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    return {"ok": True}


@app.post("/logout")
def logout(response: Response):
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        secure=COOKIE_SECURE,
        httponly=True,
        samesite="lax",
    )
    return {"ok": True}


@app.get("/session")
def session(_: None = Depends(check_admin)):
    return {"authenticated": True}


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

    try:
        res = (
            db.table("time_logs")
            .insert({
                "work_date": work_date.isoformat(),
                "start_time": now.isoformat(),
                "status": "RUNNING",
            })
            .execute()
        )

        if not res.data:
            raise HTTPException(status_code=500, detail="로그 시작 결과를 확인할 수 없습니다.")

        return res.data[0]

    except Exception as e:
        if isinstance(e, HTTPException):
            raise

        error_text = str(e).lower()
        if "23505" in error_text or "time_logs_single_running_idx" in error_text:
            raise HTTPException(status_code=409, detail="이미 진행 중인 로그가 있습니다.")

        raise HTTPException(
            status_code=500,
            detail=f"Supabase 로그 시작 실패: {type(e).__name__}"
        )


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
        .eq("status", "RUNNING")
        .execute()
    )

    if not res.data:
        raise HTTPException(status_code=409, detail="로그 상태가 이미 변경되었습니다.")

    return res.data[0]


@app.get("/logs/month")
def month_logs(
    year: int = Query(..., ge=1, le=9998),
    month: int = Query(..., ge=1, le=12),
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

    days = {}
    for log in logs:
        work_date = log["work_date"]
        summary = days.setdefault(
            work_date,
            {"work_date": work_date, "log_count": 0, "total_duration_seconds": 0},
        )
        summary["log_count"] += 1
        summary["total_duration_seconds"] += log["duration_seconds"] or 0

    return {
        "year": year,
        "month": month,
        "days": list(days.values()),
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
    }

class ManualLogRequest(BaseModel):
    work_date: date
    start_time: time
    end_time: time


@app.post("/logs/manual")
def add_manual_log(
    data: ManualLogRequest,
    _: None = Depends(check_admin),
):
    try:
        start_local = datetime(
            data.work_date.year,
            data.work_date.month,
            data.work_date.day,
            data.start_time.hour,
            data.start_time.minute,
            data.start_time.second,
            tzinfo=KST,
        )

        end_local = datetime(
            data.work_date.year,
            data.work_date.month,
            data.work_date.day,
            data.end_time.hour,
            data.end_time.minute,
            data.end_time.second,
            tzinfo=KST,
        )

        if end_local <= start_local:
            raise HTTPException(
                status_code=400,
                detail="종료 시각은 시작 시각보다 뒤여야 합니다.",
            )

        duration = int((end_local - start_local).total_seconds())

        res = (
            db.table("time_logs")
            .insert({
                "work_date": data.work_date.isoformat(),
                "start_time": start_local.astimezone(timezone.utc).isoformat(),
                "end_time": end_local.astimezone(timezone.utc).isoformat(),
                "duration_seconds": duration,
                "status": "COMPLETED",
            })
            .execute()
        )

        if not res.data:
            raise HTTPException(status_code=500, detail="수동 로그 저장 결과를 확인할 수 없습니다.")

        return res.data[0]

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"수동 로그 추가 실패: {type(e).__name__}",
        )

@app.delete("/logs/{log_id}")
def delete_log(
    log_id: int,
    _: None = Depends(check_admin),
):
    try:
        res = (
            db.table("time_logs")
            .delete()
            .eq("id", log_id)
            .execute()
        )

        if not res.data:
            raise HTTPException(status_code=404, detail="삭제할 로그를 찾을 수 없습니다.")

        return {
            "ok": True,
            "deleted": res.data,
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"로그 삭제 실패: {type(e).__name__}",
        )
