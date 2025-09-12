from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import eyetracking, staff, consultations

app = FastAPI(
    title="NH 스마트 상담 분석 시스템", 
    description="아이트래킹과 AI를 활용한 금융 상담 이해도 분석",
    version="1.0.0"
)

# CORS 설정 (프론트엔드 연결용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발용 - 실제 배포시 특정 도메인만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(eyetracking.router, prefix="/api/eyetracking", tags=["아이트래킹"])
app.include_router(staff.router, prefix="/api/staff", tags=["직원용"])
app.include_router(consultations.router, prefix="/api/consultations", tags=["상담관리"])

@app.get("/")
async def root():
    return {
        "message": "NH 스마트 상담 분석 시스템",
        "version": "1.0.0",
        "status": "활성",
        "endpoints": {
            "아이트래킹 분석": "/api/eyetracking/analyze",
            "직원 모니터링": "/api/staff/realtime/{consultation_id}",
            "상담 리포트": "/api/consultations/{consultation_id}/report"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "nh-smart-consultation"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)