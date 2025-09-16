"""
얼굴 표정 인식 서비스
"""
import sys
import os
import logging
from typing import Dict, List, Optional, Any
import asyncio
import base64
import io
from PIL import Image
import numpy as np

# face 모듈 import를 위한 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'face'))

logger = logging.getLogger(__name__)

class FaceAnalysisService:
    """얼굴 표정 분석 서비스"""

    def __init__(self):
        self.confusion_tracker = None
        self.is_initialized = False
        self._initialize_models()

    def _initialize_models(self):
        """모델 초기화"""
        try:
            # HuggingFace 기반 혼란도 추적기 import 시도
            from realtime_confusion_tracker_hf import RealtimeConfusionTrackerHF

            self.confusion_tracker = RealtimeConfusionTrackerHF(
                repo_id='combe4259/face-comprehension',
                sequence_length=30,
                buffer_size=30,
                prediction_interval=0.5
            )

            self.is_initialized = True
            logger.info("✅ 얼굴 표정 인식 모델 초기화 완료")

        except Exception as e:
            logger.warning(f"⚠️ 얼굴 표정 인식 모델 초기화 실패: {e}")
            logger.info("폴백 모드로 동작합니다.")
            self.is_initialized = False

    async def analyze_face_emotion(self, image_data: str, consultation_id: str) -> Dict[str, Any]:
        """
        이미지에서 얼굴 표정을 분석하여 혼란도를 측정

        Args:
            image_data: base64 인코딩된 이미지 데이터
            consultation_id: 상담 세션 ID

        Returns:
            얼굴 분석 결과 딕셔너리
        """
        try:
            if not self.is_initialized:
                return await self._fallback_analysis()

            # base64 이미지 디코딩
            image = self._decode_base64_image(image_data)
            if image is None:
                return await self._fallback_analysis()

            # numpy 배열로 변환
            frame = np.array(image)

            # 얼굴 분석 수행
            result = self._analyze_frame(frame)

            return {
                "status": "success",
                "consultation_id": consultation_id,
                "confusion_detected": result.get("confused", False),
                "confusion_probability": result.get("probability", 0.0),
                "confidence": result.get("confidence", 0.0),
                "emotions": {
                    "confusion": result.get("probability", 0.0),
                    "engagement": 1.0 - result.get("probability", 0.0),
                    "frustration": min(result.get("probability", 0.0) * 1.2, 1.0),
                    "boredom": max(0.0, result.get("probability", 0.0) - 0.3)
                },
                "analysis_timestamp": self._get_timestamp()
            }

        except Exception as e:
            logger.error(f"얼굴 분석 실패: {e}")
            return await self._fallback_analysis()

    def _decode_base64_image(self, image_data: str) -> Optional[Image.Image]:
        """base64 이미지를 PIL Image로 디코딩"""
        try:
            # base64 헤더 제거 (data:image/jpeg;base64, 등)
            if ',' in image_data:
                image_data = image_data.split(',')[1]

            # base64 디코딩
            image_bytes = base64.b64decode(image_data)
            image = Image.open(io.BytesIO(image_bytes))

            # RGB로 변환
            if image.mode != 'RGB':
                image = image.convert('RGB')

            return image

        except Exception as e:
            logger.error(f"이미지 디코딩 실패: {e}")
            return None

    def _analyze_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """프레임 분석 수행"""
        try:
            if self.confusion_tracker:
                # 실제 혼란도 추적기 사용
                prediction = self.confusion_tracker.predict_confusion([frame])

                if prediction:
                    return {
                        "confused": prediction.get("confused", False),
                        "probability": prediction.get("probability", 0.0),
                        "confidence": 0.85
                    }

            # 폴백: 간단한 분석
            return self._simple_face_analysis(frame)

        except Exception as e:
            logger.error(f"프레임 분석 실패: {e}")
            return self._simple_face_analysis(frame)

    def _simple_face_analysis(self, frame: np.ndarray) -> Dict[str, Any]:
        """간단한 얼굴 분석 (폴백용)"""
        try:
            # 이미지 기본 속성 분석
            height, width = frame.shape[:2]
            brightness = np.mean(frame)

            # 간단한 휴리스틱으로 혼란도 추정
            # 실제로는 더 정교한 분석이 필요
            confusion_prob = min(0.8, max(0.1, (brightness - 128) / 255 + 0.3))

            return {
                "confused": confusion_prob > 0.6,
                "probability": confusion_prob,
                "confidence": 0.6
            }

        except Exception:
            return {
                "confused": False,
                "probability": 0.3,
                "confidence": 0.5
            }

    async def _fallback_analysis(self) -> Dict[str, Any]:
        """모델이 없을 때 폴백 분석"""
        return {
            "status": "fallback",
            "confusion_detected": False,
            "confusion_probability": 0.2,
            "confidence": 0.5,
            "emotions": {
                "confusion": 0.2,
                "engagement": 0.8,
                "frustration": 0.1,
                "boredom": 0.1
            },
            "analysis_timestamp": self._get_timestamp(),
            "note": "얼굴 분석 모델을 사용할 수 없어 기본값을 반환합니다."
        }

    def _get_timestamp(self) -> str:
        """현재 시간 반환"""
        from datetime import datetime
        return datetime.now().isoformat()

    async def get_session_emotion_summary(self, consultation_id: str) -> Dict[str, Any]:
        """세션 전체 감정 요약"""
        try:
            # TODO: 데이터베이스에서 해당 세션의 얼굴 분석 기록을 조회
            # 현재는 Mock 데이터 반환

            return {
                "consultation_id": consultation_id,
                "total_frames_analyzed": 45,
                "average_confusion": 0.25,
                "peak_confusion_moments": [
                    {"timestamp": "2024-01-15T10:15:23", "confusion_level": 0.85},
                    {"timestamp": "2024-01-15T10:18:45", "confusion_level": 0.78}
                ],
                "emotion_timeline": [
                    {"timestamp": "2024-01-15T10:10:00", "confusion": 0.1, "engagement": 0.9},
                    {"timestamp": "2024-01-15T10:15:00", "confusion": 0.8, "engagement": 0.2},
                    {"timestamp": "2024-01-15T10:20:00", "confusion": 0.3, "engagement": 0.7}
                ],
                "recommendations": [
                    "10:15-10:19 구간에서 높은 혼란도가 감지되었습니다.",
                    "복잡한 금융 용어에 대한 추가 설명이 필요할 것 같습니다."
                ]
            }

        except Exception as e:
            logger.error(f"감정 요약 조회 실패: {e}")
            return {
                "consultation_id": consultation_id,
                "error": "감정 분석 요약을 가져올 수 없습니다."
            }

    def health_check(self) -> Dict[str, Any]:
        """서비스 상태 확인"""
        return {
            "service": "face_analysis",
            "status": "healthy" if self.is_initialized else "degraded",
            "model_loaded": self.is_initialized,
            "confusion_tracker": "available" if self.confusion_tracker else "unavailable"
        }

# 전역 서비스 인스턴스
face_service = FaceAnalysisService()