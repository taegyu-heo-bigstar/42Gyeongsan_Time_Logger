from datetime import date, time

from pydantic import BaseModel


class LoginRequest(BaseModel):
    password: str


class StartRequest(BaseModel):
    work_date: date | None = None


class ManualLogRequest(BaseModel):
    work_date: date
    start_time: time
    end_time: time
