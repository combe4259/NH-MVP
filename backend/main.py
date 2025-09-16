from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import eyetracking, staff, consultations
from models.database import startup_database, shutdown_database

# 텍스트 분석 모듈 임포트 (오류 처리 포함)
try:
    from routers import text_analysis
    TEXT_ANALYSIS_AVAILABLE = True
    print("text_analysis router import success")
except ImportError as e:
    print(f"text_analysis router import failed: {e}")
    TEXT_ANALYSIS_AVAILABLE = False

# 얼굴 분석 모듈 임포트 (오류 처리 포함)
try:
    from routers import face_analysis
    FACE_ANALYSIS_AVAILABLE = True
    print("face_analysis router import success")
except ImportError as e:
    print(f"face_analysis router import failed: {e}")
    FACE_ANALYSIS_AVAILABLE = False

app = FastAPI(
    title="NH 스마트 상담 분석 시스템",
    description="금융 상담 이해도 분석",
    version="1.0.0"
)

# 데이터베이스 초기화 이벤트
@app.on_event("startup")
async def startup():
    try:
        await startup_database()
        print("데이터베이스 연결 성공")
    except Exception as e:
        print(f"데이터베이스 연결 실패: {e}")

@app.on_event("shutdown")
async def shutdown():
    await shutdown_database()

# CORS 설정 (프론트엔드 연결용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(eyetracking.router, prefix="/api/eyetracking", tags=["아이트래킹"])
app.include_router(staff.router, prefix="/api/staff", tags=["직원용"])
app.include_router(consultations.router, prefix="/api/consultations", tags=["상담관리"])

# 텍스트 분석 라우터는 조건부 등록
if TEXT_ANALYSIS_AVAILABLE:
    app.include_router(text_analysis.router, prefix="/api/text", tags=["텍스트분석"])
    print("text_analysis router registered successfully")
else:
    print("text_analysis router registration failed - missing dependencies")

# 얼굴 분석 라우터는 조건부 등록
if FACE_ANALYSIS_AVAILABLE:
    app.include_router(face_analysis.router, prefix="/api/face", tags=["얼굴분석"])
    print("face_analysis router registered successfully")
else:
    print("face_analysis router registration failed - missing dependencies")

@app.get("/")
async def root():
    return {
        "message": "NH 스마트 상담 분석 시스템",
        "version": "1.0.0",
        "status": "활성",
        "endpoints": {
            "아이트래킹 분석": "/api/eyetracking/analyze",
            "직원 모니터링": "/api/staff/realtime/{consultation_id}",
            "상담 리포트": "/api/consultations/{consultation_id}/report",
            "얼굴 분석": "/api/face/analyze-frame",
            "텍스트 분석": "/api/text/analyze-text"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "nh-smart-consultation"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)