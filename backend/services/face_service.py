"""
얼굴 표정 인식 서비스 - CNN-LSTM 래퍼
기존 인터페이스를 유지하면서 CNN-LSTM 모델 사용
"""
import logging
from typing import Dict, List, Optional, Any
from collections import deque
import asyncio
from datetime import datetime

# CNN-LSTM 서비스 import
from services.face_analysis_service import face_analyzer

logger = logging.getLogger(__name__)

class FaceAnalysisService:
    """얼굴 표정 분석 서비스 - CNN-LSTM 버전"""

    def __init__(self):
        self.face_analyzer = face_analyzer
        self.frame_buffer = deque(maxlen=30)  # 30프레임 버퍼
        self.last_analysis_result = None
        self.is_initialized = True
        logger.info("✅ CNN-LSTM 얼굴 분석 서비스 초기화 완료")

    async def analyze_face_emotion(self, image_data: str, consultation_id: str) -> Dict[str, Any]:
        """
        프레임을 버퍼에 추가하고 30프레임이 모이면 CNN-LSTM 분석
        
        Args:
            image_data: base64 인코딩된 이미지 데이터
            consultation_id: 상담 세션 ID
        
        Returns:
            얼굴 분석 결과
        """
        try:
            # base64 헤더 제거
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            
            # 프레임 버퍼에 추가
            self.frame_buffer.append(image_data)
            
            # 30프레임이 모이면 분석
            if len(self.frame_buffer) == 30:
                result = await self.face_analyzer.analyze_frames(list(self.frame_buffer))
                self.last_analysis_result = result
                
                # 다음 분석을 위해 일부 프레임만 유지 (연속성)
                for _ in range(10):
                    if self.frame_buffer:
                        self.frame_buffer.popleft()
            else:
                # 아직 30프레임이 안 모였으면 이전 결과 또는 기본값 반환
                result = self.last_analysis_result or {
                    "confusion": 1,
                    "confusion_probability": 0.3,
                    "confidence": 0.5
                }
            
            # 기존 인터페이스에 맞게 변환
            confusion_level = result.get("confusion", 1)
            confusion_prob = result.get("confusion_probability", 0.3)
            
            return {
                "status": "success",
                "consultation_id": consultation_id,
                "confusion_detected": confusion_level >= 2,  # 레벨 2 이상이면 혼란
                "confusion_probability": confusion_prob,
                "confidence": result.get("confidence", 0.5),
                "emotions": {
                    "confusion": confusion_prob,
                    "engagement": max(0, 1.0 - confusion_prob),
                    "frustration": min(1.0, confusion_prob * 0.8),
                    "boredom": max(0, confusion_prob - 0.5)
                },
                "analysis_timestamp": self._get_timestamp()
            }
            
        except Exception as e:
            logger.error(f"얼굴 분석 실패: {e}")
            return self._get_fallback_result(consultation_id)
    
    async def analyze_face(self, image_data: str) -> Dict[str, Any]:
        """
        단일 프레임 분석 (호환성 유지)
        """
        return await self.analyze_face_emotion(image_data, "default")
    
    def _get_timestamp(self) -> str:
        """현재 타임스탬프 반환"""
        return datetime.now().isoformat()
    
    def _get_fallback_result(self, consultation_id: str) -> Dict[str, Any]:
        """폴백 결과 반환"""
        return {
            "status": "fallback",
            "consultation_id": consultation_id,
            "confusion_detected": False,
            "confusion_probability": 0.3,
            "confidence": 0.5,
            "emotions": {
                "confusion": 0.3,
                "engagement": 0.7,
                "frustration": 0.2,
                "boredom": 0.1
            },
            "analysis_timestamp": self._get_timestamp()
        }
    
    async def batch_analyze(self, frames: List[str]) -> Dict[str, Any]:
        """
        여러 프레임 배치 분석
        """
        try:
            result = await self.face_analyzer.analyze_frames(frames)
            return result
        except Exception as e:
            logger.error(f"배치 분석 실패: {e}")
            return {
                "confusion": 1,
                "confusion_probability": 0.5,
                "confidence": 0.5,
                "error": str(e)
            }

# 전역 서비스 인스턴스
face_service = FaceAnalysisService()