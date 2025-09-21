from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from routers import eyetracking, staff, consultations, face_router
import json
import asyncio
from typing import Dict, List
import logging
import cv2
import numpy as np
import base64
import os
from models.database import startup_database, shutdown_database

# 텍스트 분석 모듈 임포트
try:
    from routers import text_analysis
    TEXT_ANALYSIS_AVAILABLE = True
except ImportError as e:
    TEXT_ANALYSIS_AVAILABLE = False

# 얼굴 분석 모듈 임포트
try:
    from routers import face_analysis
    FACE_ANALYSIS_AVAILABLE = True
except ImportError as e:
    FACE_ANALYSIS_AVAILABLE = False

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = FastAPI(
    title="NH 스마트 상담 분석 시스템",
    description="금융 상담 이해도 분석",
    version="1.0.0"
)

# 애플리케이션 시작 시 데이터베이스 연결
@app.on_event("startup")
async def startup():
    try:
        await startup_database()
    except Exception as e:
        logger.error(f"Database connection failed: {e}")

@app.on_event("shutdown")
async def shutdown():
    await shutdown_database()

# CORS 설정으로 프론트엔드와의 통신 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
app.include_router(eyetracking.router, prefix="/api/eyetracking", tags=["아이트래킹"])
app.include_router(staff.router, prefix="/api/staff", tags=["직원용"])
app.include_router(consultations.router, prefix="/api/consultations", tags=["상담관리"])
app.include_router(face_router.router)

# 텍스트 분석 라우터 조건부 등록
if TEXT_ANALYSIS_AVAILABLE:
    app.include_router(text_analysis.router, prefix="/api/text", tags=["텍스트분석"])

# 얼굴 분석 라우터 조건부 등록
if FACE_ANALYSIS_AVAILABLE:
    app.include_router(face_analysis.router, prefix="/api/face", tags=["얼굴분석"])

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

# WebSocket 연결 관리
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        
    async def connect(self, websocket: WebSocket, consultation_id: str):
        await websocket.accept()
        if consultation_id not in self.active_connections:
            self.active_connections[consultation_id] = []
        self.active_connections[consultation_id].append(websocket)
        logger.info(f"WebSocket 연결: consultation_id={consultation_id}")
        
    def disconnect(self, websocket: WebSocket, consultation_id: str):
        if consultation_id in self.active_connections:
            self.active_connections[consultation_id].remove(websocket)
            if not self.active_connections[consultation_id]:
                del self.active_connections[consultation_id]
        logger.info(f"WebSocket 연결 해제: consultation_id={consultation_id}")
        
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
        
    async def broadcast(self, message: str, consultation_id: str):
        if consultation_id in self.active_connections:
            for connection in self.active_connections[consultation_id]:
                await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws/{consultation_id}")
async def websocket_endpoint(websocket: WebSocket, consultation_id: str):
    """실시간 아이트래킹 + 얼굴 분석 WebSocket 엔드포인트"""
    
    await manager.connect(websocket, consultation_id)
    
    # AI 서비스 초기화
    from services.ai_model_service import ai_model_manager
    from services.eyetrack_service import eyetrack_service
    
    try:
        while True:
            # 클라이언트로부터 데이터 수신
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # 메시지 타입별 처리
            if message.get("type") == "eyetracking":
                # 아이트래킹 데이터 처리
                section_text = message.get("section_text", "")
                reading_time = message.get("reading_time", 0)
                gaze_data = message.get("gaze_data", {})
                
                # 텍스트 난이도 분석 (KLUE-BERT)
                if ai_model_manager and ai_model_manager.current_model:
                    difficulty = await ai_model_manager.current_model.analyze_difficulty(section_text)
                    confused_sections = await ai_model_manager.current_model.identify_confused_sections(section_text)
                else:
                    difficulty = 0.5
                    confused_sections = []
                
                response = {
                    "type": "difficulty_analysis",
                    "difficulty_score": difficulty,
                    "confused_sections": confused_sections,
                    "timestamp": message.get("timestamp")
                }
                
                await manager.send_personal_message(json.dumps(response), websocket)
                
            elif message.get("type") == "face_frame":
                # 얼굴 프레임 데이터 처리 (base64 인코딩된 이미지)
                frame_data = message.get("frame", "")
                
                if frame_data and ai_model_manager and hasattr(ai_model_manager, 'hf_models'):
                    try:
                        # base64 디코딩
                        img_bytes = base64.b64decode(frame_data)
                        nparr = np.frombuffer(img_bytes, np.uint8)
                        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                        
                        # 얼굴 혼란도 분석 (Face-Comprehension)
                        if ai_model_manager.hf_models:
                            face_result = await ai_model_manager.hf_models.analyze_confusion_from_face(frame)
                            
                            response = {
                                "type": "face_analysis",
                                "confused": face_result.get("confused", False),
                                "confusion_probability": face_result.get("probability", 0.0),
                                "timestamp": face_result.get("timestamp")
                            }
                            
                            await manager.send_personal_message(json.dumps(response), websocket)
                            
                            # 혼란도가 높으면 모든 연결된 클라이언트에 브로드캐스트
                            if face_result.get("confused", False):
                                alert = {
                                    "type": "confusion_alert",
                                    "consultation_id": consultation_id,
                                    "confusion_probability": face_result.get("probability", 0.0),
                                    "message": "고객이 어려워하고 있습니다"
                                }
                                await manager.broadcast(json.dumps(alert), consultation_id)
                                
                    except Exception as e:
                        logger.error(f"얼굴 분석 오류: {e}")
                        
            elif message.get("type") == "combined_analysis":
                # 아이트래킹 + 얼굴 통합 분석
                section_text = message.get("section_text", "")
                reading_time = message.get("reading_time", 0)
                gaze_data = message.get("gaze_data", {})
                frame_data = message.get("face_frame", "")
                
                # 얼굴 프레임 디코딩
                frame = None
                if frame_data:
                    try:
                        img_bytes = base64.b64decode(frame_data)
                        nparr = np.frombuffer(img_bytes, np.uint8)
                        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    except:
                        frame = None
                
                # 얼굴 분석 데이터 처리
                face_data = None
                if frame is not None:
                    # face_service를 통해 얼굴 분석
                    try:
                        from services.face_service import face_service
                        face_result = await face_service.analyze_face(frame)
                        face_data = {
                            'confusion_probability': face_result.get('confusion_detected', 0.0),
                            'emotions': face_result.get('emotions', {})
                        }
                    except Exception as e:
                        logger.error(f"얼굴 분석 실패: {e}")
                
                # 통합 분석 수행
                analysis_result = await eyetrack_service.analyze_reading_session(
                    consultation_id=consultation_id,
                    section_name=message.get("section_name", "unknown"),
                    section_text=section_text,
                    reading_time=reading_time,
                    gaze_data=gaze_data,
                    face_data=face_data  # 얼굴 분석 데이터 전달
                )
                
                # 분석 결과 전송
                await manager.send_personal_message(json.dumps(analysis_result), websocket)
                
                # AI 도우미가 필요한 경우 알림
                if analysis_result.get("needs_ai_assistance", False):
                    ai_helper = {
                        "type": "ai_helper_trigger",
                        "explanation": analysis_result.get("ai_explanation", ""),
                        "difficulty_score": analysis_result.get("difficulty_score", 0),
                        "confused_sections": analysis_result.get("confused_sections", [])
                    }
                    await manager.broadcast(json.dumps(ai_helper), consultation_id)
                    
            elif message.get("type") == "ping":
                # 연결 유지용 ping
                await manager.send_personal_message(json.dumps({"type": "pong"}), websocket)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, consultation_id)
        logger.info(f"WebSocket 연결 종료: {consultation_id}")
        
    except Exception as e:
        logger.error(f"WebSocket 오류: {e}")
        manager.disconnect(websocket, consultation_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)