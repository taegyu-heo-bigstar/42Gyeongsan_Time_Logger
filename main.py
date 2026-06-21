from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone
import os
from dotenv import load_dotenv
from supabase import create_client, Client

# .env 파일 불러오기
load_dotenv()

# Supabase 클라이언트 초기화
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

app = FastAPI(title="TimeLog API")

# [1] CORS 설정 (프론트엔드와 백엔드 분리를 위한 필수 설정)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 개발 중에는 모두 허용, 배포 시 프론트엔드 Vercel URL로 변경
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# [2] 자동 종료 '지연 평가' 로직 (데이터 조회 전 항상 실행)
def check_and_auto_stop_logs():
    """
    TODO: Supabase에서 status='RUNNING'인 로그를 조회.
    현재 시간과 start_time을 비교하여 12시간이 지났거나 날짜가 바뀌었으면
    status를 'AUTO_STOPPED'로 업데이트하고 end_time과 duration을 계산하여 저장.
    """
    pass

# 의존성 주입(Dependency)을 활용한 미들웨어
async def auto_stop_middleware():
    check_and_auto_stop_logs()

# [3] 핵심 API 엔드포인트 라우팅 (뼈대)
@app.post("/login")
async def login():
    # TODO: 관리자 계정 검증 및 세션/토큰 발급
    return {"message": "Login logic here"}

@app.post("/logs/start", dependencies=[Depends(auto_stop_middleware)])
async def start_log():
    # TODO: RUNNING 상태 검증 후 새 로그 생성
    return {"status": "RUNNING", "start_time": datetime.now(timezone.utc)}

@app.post("/logs/stop", dependencies=[Depends(auto_stop_middleware)])
async def stop_log():
    # TODO: 현재 RUNNING인 로그를 찾아 end_time, duration 기록 후 COMPLETED로 변경
    return {"status": "COMPLETED", "message": "Log stopped successfully"}

@app.get("/logs/current", dependencies=[Depends(auto_stop_middleware)])
async def get_current_log():
    # TODO: 현재 RUNNING 상태인 로그 반환 (버튼 상태 UI 렌더링용)
    return {"current_log": None}

@app.get("/logs/month", dependencies=[Depends(auto_stop_middleware)])
async def get_monthly_logs(year: int, month: int):
    # TODO: 해당 연/월의 로그 데이터 목록 및 합산 데이터 반환
    return {"logs": [], "total_duration_seconds": 0}