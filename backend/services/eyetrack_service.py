import sys
import os
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

from models.schemas import (
    GazePoint,
    FixationData,
    SaccadeData,
    TextElement,
    ReadingMetrics,
    ReadingDataRequest,
    ReadingDataResponse
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.append(str(Path(__file__).parent.parent.parent))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'eyetrack'))

try:
    from reading_data_collector import ReadingDataCollector
    EYETRACK_MODULES_AVAILABLE = True
except ImportError as e:
    logger.warning("Warning: reading_data_collector 모듈을 찾을 수 없습니다. %s", str(e))
    EYETRACK_MODULES_AVAILABLE = False
    ReadingDataCollector = None

class EyeTrackingService:
    """시선 추적 및 분석 서비스"""
    
    def __init__(self):
        self.session_data = {}  # consultation_id별 세션 데이터
        self.reading_data_collectors: Dict[str, Any] = {}  # consultation_id별 collector

    async def analyze_reading_session(self, consultation_id: str, section_name: str,
                                    section_text: str, reading_time: float,
                                    gaze_data: Optional[Dict] = None,
                                    face_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        읽기 세션 분석 - 오케스트레이터

        통합 분석 서비스를 호출하고 필요시 문장 간소화를 수행합니다.
        """

        try:
            from services.ai_model_service import ai_model_manager
            from services.integrated_analysis_service import integrated_analyzer

            # 1. 통합 분석 서비스 호출 (텍스트 + 얼굴 + 시선 모두 분석)
            integrated_result = await integrated_analyzer.analyze_integrated(
                consultation_id=consultation_id,
                section_name=section_name,
                section_text=section_text,
                face_data=face_data,
                gaze_data=gaze_data,
                reading_time=reading_time
            )

            # 2. AI 간소화가 필요한 경우
            ai_explanation = ''
            if integrated_result['should_simplify_text']:
                try:
                    simplified = await ai_model_manager.hf_models.simplify_text(section_text)
                    ai_explanation = f"**쉽게 설명해드릴게요:**\n{simplified}"
                    logger.info(f"문장 간소화 수행: {section_name}")
                except Exception as e:
                    logger.error(f"간소화 실패: {e}")
                    ai_explanation = "이 부분이 어려우실 수 있습니다. 천천히 읽어보시고 궁금한 점은 문의해주세요."

            # 3. 통합 분석 결과에서 필요한 값 추출
            confusion_probability = integrated_result['integrated_confusion']
            comprehension_level = integrated_result['comprehension_level']
            text_difficulty = integrated_result['individual_scores']['text_difficulty']

            # 4. 상태 결정
            if comprehension_level == "low":
                status = "confused"
            elif comprehension_level == "medium":
                status = "moderate"
            else:
                status = "good"

            # 5. 어려운 문장 추출
            confused_sentences = []
            confused_sentences_detail = []

            # 텍스트가 비어있으면 분석 건너뛰기
            if not section_text or len(section_text.strip()) < 10:
                logger.warning(f"텍스트가 비어있거나 너무 짧음 (길이: {len(section_text) if section_text else 0}). 문장 분석 건너뜀")
            # confusion이 높으면 문장 분석
            elif confusion_probability > 0.15:
                sentences = section_text.replace('!', '.').replace('?', '.').split('.')
                sentences = [s.strip() for s in sentences if s.strip()]

                if not sentences:
                    sentences = [section_text]

                for idx, sentence in enumerate(sentences):
                    if len(sentence) > 5:
                        confused_sentences.append(idx)
                        confused_sentences_detail.append({
                            'sentence': sentence,
                            'sentence_id': f'sentence_{idx}',
                            'difficulty_score': max(confusion_probability, 0.5),
                            'simplified_explanation': ai_explanation if ai_explanation else "이 부분을 쉽게 설명해드리겠습니다."
                        })

                logger.info(f"Confused sentences 추가: {len(confused_sentences)}개")

            # 6. 세션 데이터 업데이트
            if consultation_id not in self.session_data:
                self.session_data[consultation_id] = {
                    'sections': [],
                    'start_time': datetime.now(timezone.utc)
                }

            self.session_data[consultation_id]['sections'].append({
                'section_name': section_name,
                'difficulty_score': text_difficulty,
                'confusion_probability': confusion_probability,
                'comprehension_level': comprehension_level,
                'ai_explanation': ai_explanation,  # AI 간소화 텍스트 저장
                'timestamp': datetime.now(timezone.utc)
            })

            # 7. 최종 결과 반환
            result = {
                "status": status,
                "confused_sentences": confused_sentences,
                "confused_sentences_detail": confused_sentences_detail,
                "ai_explanation": ai_explanation,
                "difficulty_score": round(text_difficulty, 2),
                "confusion_probability": round(confusion_probability, 2),
                "comprehension_level": comprehension_level,
                "recommendations": integrated_result.get('recommendations', []),
                "needs_ai_assistance": integrated_result.get('need_ai_assistance', False),

                # 개별 점수들 추가
                "individual_scores": {
                    "text_confusion": round(integrated_result['individual_scores']['text_confusion'], 2),
                    "face_confusion": round(integrated_result['individual_scores']['face_confusion'], 2),
                    "gaze_confusion": round(integrated_result['individual_scores']['gaze_confusion'], 2)
                },
                "integrated_confusion": round(integrated_result['integrated_confusion'], 2),

                "analysis_metadata": {
                    "section_length": len(section_text),
                    "reading_speed_wpm": len(section_text.split()) / (reading_time / 60) if reading_time > 0 else 0,
                    "analyzed_at": datetime.now(timezone.utc).isoformat()
                }
            }

            return result
            
        except Exception as e:
            return {
                "status": "error",
                "error_message": f"분석 중 오류 발생: {str(e)}",
                "confused_sentences": [],
                "ai_explanation": "죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
                "difficulty_score": 0.5,
                "comprehension_level": "medium",
                "recommendations": ["기술적 문제로 인해 분석이 제한됩니다. 직원에게 문의하세요."]
            }
    
    def get_session_summary(self, consultation_id: str) -> Optional[Dict]:
        """세션 전체 요약 정보 반환"""
        if consultation_id not in self.session_data:
            return None
        
        session = self.session_data[consultation_id]
        sections = session['sections']
        
        if not sections:
            return None
        
        # 전체 통계 계산
        avg_difficulty = sum(s['difficulty_score'] for s in sections) / len(sections)
        avg_confusion = sum(s['confusion_probability'] for s in sections) / len(sections)
        
        comprehension_counts = {
            'high': len([s for s in sections if s['comprehension_level'] == 'high']),
            'medium': len([s for s in sections if s['comprehension_level'] == 'medium']),
            'low': len([s for s in sections if s['comprehension_level'] == 'low'])
        }
        
        confused_sections = [s['section_name'] for s in sections if s['confusion_probability'] > 0.6]
        
        return {
            'consultation_id': consultation_id,
            'total_sections': len(sections),
            'avg_difficulty': round(avg_difficulty, 2),
            'avg_confusion': round(avg_confusion, 2),
            'comprehension_summary': comprehension_counts,
            'confused_sections': confused_sections,
            'session_duration': (datetime.now(timezone.utc) - session['start_time']).total_seconds() / 60,
            'last_updated': sections[-1]['timestamp'].isoformat() if sections else None
        }


    def process_gaze_data(self, consultation_id: str, gaze_data: Dict) -> Dict[str, Any]:
        """실시간 시선 데이터 처리 및 분석 (reading_data_collector 통합)"""
        try:
            # 실시간 데이터 컬렉터 초기화
            if consultation_id not in self.reading_data_collectors and EYETRACK_MODULES_AVAILABLE and ReadingDataCollector:
                self.reading_data_collectors[consultation_id] = ReadingDataCollector()

            # 세션 데이터 초기화
            if consultation_id not in self.session_data:
                self.session_data[consultation_id] = {
                    'sections': [],
                    'start_time': datetime.now(timezone.utc),
                    'gaze_points': []
                }

            # 시선 데이터 저장
            gaze_point = {
                'x': gaze_data.get('x', 0),
                'y': gaze_data.get('y', 0),
                'timestamp': gaze_data.get('timestamp', datetime.now().timestamp()),
                'confidence': gaze_data.get('confidence', 0.0)
            }
            self.session_data[consultation_id]['gaze_points'].append(gaze_point)

            # reading_data_collector로 실시간 처리
            ai_data = None
            if consultation_id in self.reading_data_collectors:
                collector = self.reading_data_collectors[consultation_id]
                ai_data = collector.process_gaze_point(
                    gaze_point['x'],
                    gaze_point['y'],
                    current_page=1,
                    timestamp=gaze_point['timestamp']
                )

            # 최근 시선 데이터 분석 (간단한 패턴 분석)
            recent_points = self.session_data[consultation_id]['gaze_points'][-10:]

            # 시선 분산도 계산 (혼란도 지표)
            if len(recent_points) >= 3:
                x_coords = [p['x'] for p in recent_points]
                y_coords = [p['y'] for p in recent_points]

                x_variance = sum([(x - sum(x_coords)/len(x_coords))**2 for x in x_coords]) / len(x_coords)
                y_variance = sum([(y - sum(y_coords)/len(y_coords))**2 for y in y_coords]) / len(y_coords)

                gaze_dispersion = (x_variance + y_variance) / 2
                confusion_indicator = min(gaze_dispersion / 10000, 1.0)  # 정규화
            else:
                confusion_indicator = 0.0

            result = {
                "consultation_id": consultation_id,
                "gaze_quality": "good" if gaze_data.get('confidence', 0) > 0.8 else "poor",
                "confusion_indicator": confusion_indicator,
                "total_gaze_points": len(self.session_data[consultation_id]['gaze_points']),
                "analysis_timestamp": datetime.now(timezone.utc).isoformat()
            }

            # AI용 실시간 데이터 추가 (reading_data_collector에서)
            if ai_data:
                result["ai_ready_data"] = ai_data
                result["behavioral_metrics"] = ai_data.get("behavioral_metrics_window_1min", {})

            return result

        except Exception as e:
            logger.error(f"시선 데이터 처리 오류: {str(e)}")
            return {
                "consultation_id": consultation_id,
                "gaze_quality": "error",
                "confusion_indicator": 0.0,
                "error_message": str(e),
                "analysis_timestamp": datetime.now(timezone.utc).isoformat()
            }

    def get_reading_progress(self, consultation_id: str) -> Dict[str, Any]:
        """읽기 진행률 조회"""
        try:
            if consultation_id not in self.session_data:
                return {
                    "percentage": 0,
                    "current_section": "시작 전",
                    "sections_completed": 0,
                    "total_sections": 0,
                    "time_remaining": 0
                }

            session = self.session_data[consultation_id]
            sections = session.get('sections', [])

            if not sections:
                return {
                    "percentage": 0,
                    "current_section": "분석 대기중",
                    "sections_completed": 0,
                    "total_sections": 0,
                    "time_remaining": 0
                }

            # 가정: 일반적인 금융상품 설명서는 약 8-10개 섹션으로 구성
            estimated_total_sections = 8
            sections_completed = len(sections)

            # 진행률 계산
            progress_percentage = min((sections_completed / estimated_total_sections) * 100, 100)

            # 평균 읽기 시간 기반 남은 시간 추정
            if sections_completed > 0:
                session_duration = (datetime.now(timezone.utc) - session['start_time']).total_seconds() / 60
                avg_time_per_section = session_duration / sections_completed
                remaining_sections = max(estimated_total_sections - sections_completed, 0)
                estimated_time_remaining = remaining_sections * avg_time_per_section
            else:
                estimated_time_remaining = 15  # 기본값: 15분

            return {
                "percentage": round(progress_percentage, 1),
                "current_section": sections[-1]['section_name'] if sections else "진행 중",
                "sections_completed": sections_completed,
                "total_sections": estimated_total_sections,
                "time_remaining": round(estimated_time_remaining, 1)
            }

        except Exception as e:
            logger.error(f"읽기 진행률 조회 오류: {str(e)}")
            return {
                "percentage": 0,
                "current_section": "오류",
                "sections_completed": 0,
                "total_sections": 0,
                "time_remaining": 0
            }

# 전역 서비스 인스턴스
eyetrack_service = EyeTrackingService()