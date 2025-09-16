import sys
import os
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Deque, Tuple
from collections import deque, defaultdict
import numpy as np

# Pydantic 모델 임포트
from models.schemas import (
    GazePoint,
    FixationData,
    SaccadeData,
    TextElement,
    ReadingMetrics,
    ReadingDataRequest,
    ReadingDataResponse
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent directory to path to import text_simplifier
sys.path.append(str(Path(__file__).parent.parent.parent))

try:
    from text_simplifier_krfinbert_kogpt2 import FinancialTextSimplifier
    TEXT_SIMPLIFIER_AVAILABLE = True
except ImportError as e:
    logger.warning("Warning: text_simplifier 모듈을 찾을 수 없습니다. %s", str(e))
    TEXT_SIMPLIFIER_AVAILABLE = False
    FinancialTextSimplifier = None

# eyetrack 모듈 import (기존 코드 재사용)
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'eyetrack'))

try:
    from comprehension_analyzer import ComprehensionAnalyzer, ComprehensionMetrics, RealTimeComprehensionMonitor
    from hybrid_analyzer import hybrid_analyzer
    from reading_data_collector import ReadingDataCollector
    from gaze_tracker import EyeGazeTracker
    from fixation_detector import FixationDetector
    AI_MODELS_AVAILABLE = True
    EYETRACK_MODULES_AVAILABLE = True
except ImportError as e:
    logger.warning("Warning: eyetrack 모듈을 찾을 수 없습니다. 시뮬레이션 모드로 동작합니다. %s", str(e))
    AI_MODELS_AVAILABLE = False
    EYETRACK_MODULES_AVAILABLE = False
    ComprehensionAnalyzer = None
    ComprehensionMetrics = None
    RealTimeComprehensionMonitor = None
    hybrid_analyzer = None
    ReadingDataCollector = None
    EyeGazeTracker = None
    FixationDetector = None

class EyeTrackingService:
    """시선 추적 및 분석을 위한 서비스 클래스"""
    
    def __init__(self):
        # 기존 분석기 초기화
        self.analyzer = ComprehensionAnalyzer() if AI_MODELS_AVAILABLE and ComprehensionAnalyzer else None
        self.monitor = RealTimeComprehensionMonitor() if AI_MODELS_AVAILABLE and RealTimeComprehensionMonitor else None
        self.session_data = {}  # consultation_id별 세션 데이터

        # 실시간 시선추적 컴포넌트 초기화
        if EYETRACK_MODULES_AVAILABLE:
            try:
                self.reading_data_collectors: Dict[str, Any] = {}  # consultation_id별 collector
                self.gaze_tracker = EyeGazeTracker() if EyeGazeTracker else None
                logger.info("실시간 시선추적 컴포넌트 로드 완료")
            except Exception as e:
                logger.warning(f"시선추적 컴포넌트 로드 실패: {e}")
                self.reading_data_collectors = {}
                self.gaze_tracker = None
        else:
            self.reading_data_collectors = {}
            self.gaze_tracker = None

        # 시선 추적 관련 초기화
        self.fixation_threshold = 0.02  # 고정점 감지 임계값 (화면 크기의 2%)
        self.min_fixation_duration = timedelta(seconds=0.1)  # 최소 고정 시간
        self.max_fixation_duration = timedelta(seconds=1.0)  # 최대 고정 시간
        self.gaze_history_window = timedelta(seconds=5.0)  # 시선 이력 유지 시간
        
        # text simplifier 실행
        try:
            if TEXT_SIMPLIFIER_AVAILABLE and FinancialTextSimplifier:
                self.text_simplifier = FinancialTextSimplifier()
                # 모델 실행
                model_path = "./financial_simplifier_model"
                if os.path.exists(model_path):
                    self.text_simplifier.load_model(model_path)
                logger.info("FinancialTextSimplifier 실행 완료")
            else:
                logger.info("FinancialTextSimplifier 사용 불가 - 의존성 부족")
                self.text_simplifier = None
        except Exception as e:
            logger.error(f"FinancialTextSimplifier 실행 실패: {str(e)}")
            self.text_simplifier = None
    
    def get_text_difficulty(self, section_text: str) -> float:
        """한국어 금융 약관 텍스트의 난이도 분석 (기존 로직 개선)"""
        
        # 어려운 금융 용어들 (확장)
        difficult_financial_terms = [
            # 기본 금융 용어
            '중도해지', '우대금리', '예금자보호', '만기자동연장', '복리', '단리',
            # 세금 관련
            '세액공제', '원천징수', '과세표준', '소득공제', '비과세',
            # 투자 관련
            '금융투자상품', '파생결합증권', '환매조건부채권', '신탁', '수익증권',
            '펀드', '위험등급', '손실가능성', '원금보장', '변동성', '유동성',
            # 대출 관련
            '담보대출', '신용대출', '한도대출', '거치기간', '상환방식',
            # 보험 관련
            '보험료', '보장내용', '면책기간', '해지환급금', '만기보험금'
        ]
        
        # 복잡한 법률/금융 표현들
        complex_expressions = [
            '~에 따라', '~을 제외하고', '~를 조건으로', '~에 한하여', '~에 관하여',
            '단,', '다만,', '또한,', '따라서,', '그러나,', '또는', '만약',
            '상기', '해당', '관련', '준용', '적용', '제외', '포함'
        ]
        
        # 문장 분석
        sentences = [s.strip() for s in section_text.split('.') if s.strip()]
        words = section_text.split()
        
        difficulty_score = 0.0
        
        # 1. 어려운 금융 용어 비율 (40% 가중치)
        financial_term_count = sum(1 for word in words 
                                  if any(term in word for term in difficult_financial_terms))
        if words:
            difficulty_score += (financial_term_count / len(words)) * 0.4
        
        # 2. 복잡한 표현 사용 빈도 (20% 가중치)
        complex_count = sum(1 for expr in complex_expressions if expr in section_text)
        difficulty_score += min(complex_count / 5, 0.2) * 0.2
        
        # 3. 문장 길이와 복잡성 (25% 가중치)
        if sentences:
            avg_sentence_length = sum(len(s) for s in sentences) / len(sentences)
            long_sentence_ratio = len([s for s in sentences if len(s) > 50]) / len(sentences)
            difficulty_score += min(avg_sentence_length / 100, 0.15) * 0.15
            difficulty_score += long_sentence_ratio * 0.1
        
        # 4. 숫자와 퍼센트 포함도 (15% 가중치)
        import re
        numbers = re.findall(r'\d+(?:\.\d+)?%?', section_text)
        number_density = len(numbers) / max(len(words), 1)
        difficulty_score += min(number_density, 0.15) * 0.15
        
        return min(difficulty_score, 1.0)
    
    def calculate_confusion_probability(self, difficulty_score: float, reading_time: float, 
                                      expected_time: float = 30.0, section_length: int = 100) -> float:
        """더 정교한 혼란도 계산"""
        
        # 텍스트 길이에 따른 기대 시간 조정
        adjusted_expected_time = expected_time * (section_length / 100)
        time_ratio = reading_time / adjusted_expected_time
        
        confusion_prob = 0.0
        
        # 1. 텍스트 난이도 (50% 가중치)
        confusion_prob += difficulty_score * 0.5
        
        # 2. 읽기 시간 패턴 (30% 가중치)
        if time_ratio > 2.5:  # 너무 오래 걸림
            confusion_prob += min((time_ratio - 1) / 4, 0.3) * 0.3
        elif time_ratio < 0.3:  # 너무 빨리 읽음 (대충 읽음)
            confusion_prob += (0.3 - time_ratio) / 0.3 * 0.2
        
        # 3. 시간대별 가중치 (20% 가중치) - 오후에는 집중력 저하
        current_hour = datetime.now().hour
        if 14 <= current_hour <= 16:  # 오후 2-4시
            confusion_prob += 0.1
        elif current_hour >= 18:  # 저녁 6시 이후
            confusion_prob += 0.15
        
        return min(max(confusion_prob, 0.0), 0.95)
    
    def identify_confused_sentences(self, section_text: str, difficulty_score: float) -> List[int]:
        """어려운 문장 식별 (개선된 알고리즘)"""
        sentences = [s.strip() for s in section_text.split('.') if s.strip()]
        confused_sentences = []
        
        for i, sentence in enumerate(sentences):
            sentence_score = 0.0
            
            # 문장별 난이도 계산
            sentence_difficulty = self.get_text_difficulty(sentence)
            sentence_score += sentence_difficulty * 0.6
            
            # 문장 길이 점수
            if len(sentence) > 60:
                sentence_score += 0.3
            
            # 특별히 어려운 패턴
            difficult_patterns = ['단,', '다만,', '그러나', '~을 제외하고']
            if any(pattern in sentence for pattern in difficult_patterns):
                sentence_score += 0.2
            
            # 임계값을 넘으면 어려운 문장으로 분류
            if sentence_score > 0.6:
                confused_sentences.append(i + 1)
        
        # 최대 4개까지만 반환 (UI 고려)
        return confused_sentences[:4]
    
    def generate_ai_explanation(self, section_text: str, confused_sentences: List[int] = None) -> str:
        """
        AI를 사용하여 복잡한 금융 텍스트를 쉽게 설명
        
        Args:
            section_text: 설명이 필요한 텍스트
            confused_sentences: 혼란스러운 문장 인덱스 목록
            
        Returns:
            str: 쉽게 설명된 텍스트
        """
        try:
            # Text simplifier가 있으면 사용
            if self.text_simplifier:
                # 간단한 설명 생성
                simplified = self.text_simplifier.simplify_text(
                    f"다음 금융 용어나 문장을 초등학생도 이해할 수 있게 쉽게 설명해주세요: {section_text}",
                    max_length=200
                )
                
                # 결과 포맷팅
                explanation = f"**쉽게 설명해 드릴게요**\n• {simplified}"
                
                # 혼란스러운 문장이 있으면 추가 정보 제공
                if confused_sentences and len(confused_sentences) > 0:
                    explanation += (f"\n\n**이 부분이 어려우셨나요?**\n"
                                  f"• {len(confused_sentences)}개 문장이 특히 어려울 수 있어요.\n"
                                  "• 천천히 다시 읽어보시고, 궁금한 점은 언제든지 질문해주세요.")
                
                return explanation
            
            # Text simplifier가 없을 경우 기본 설명
            return self._generate_fallback_explanation(section_text, confused_sentences)
            
        except Exception as e:
            logger.error(f"Error generating AI explanation: {str(e)}")
            return self._generate_fallback_explanation(section_text, confused_sentences)
    
    def _generate_fallback_explanation(self, section_text: str, confused_sentences: List[int] = None) -> str:
        """AI 모델을 사용할 수 없을 때 기본 설명 생성"""
        if confused_sentences and len(confused_sentences) > 0:
            return (
                f"**이해가 어려우신가요?**\n"
                f"• 이 부분은 {len(confused_sentences)}개의 어려운 문장이 포함되어 있어요.\n"
                "• 천천히 다시 읽어보시고, 궁금한 점은 언제든지 질문해주세요."
            )
        
        return (
            "**이해를 돕기 위한 설명**\n"
            "• 이 내용은 금융 상품의 중요한 조건을 설명하고 있어요.\n"
            "• 이해가 어려운 부분이 있으시면 언제든지 문의해 주세요."
        )
    
    async def analyze_reading_session(self, consultation_id: str, section_name: str, 
                                    section_text: str, reading_time: float, 
                                    gaze_data: Optional[Dict] = None) -> Dict[str, Any]:
        """읽기 세션 분석 (메인 API 함수)"""
        
        try:
            # 1. 텍스트 난이도 분석
            difficulty_score = self.get_text_difficulty(section_text)
            
            # 2. 혼란도 계산
            confusion_probability = self.calculate_confusion_probability(
                difficulty_score, reading_time, section_length=len(section_text)
            )
            
            # 3. 어려운 문장 식별
            confused_sentences = self.identify_confused_sentences(section_text, difficulty_score)
            
            # 4. AI 설명 생성
            ai_explanation = self.generate_ai_explanation(section_text, confused_sentences)
            
            # 5. 이해도 레벨 결정
            if confusion_probability > 0.7:
                comprehension_level = "low"
                status = "confused"
            elif confusion_probability > 0.4:
                comprehension_level = "medium"
                status = "moderate"
            else:
                comprehension_level = "high"
                status = "good"
            
            # 6. 추천사항 생성
            recommendations = self._generate_recommendations(
                confusion_probability, difficulty_score, reading_time
            )
            
            # 7. 세션 데이터 업데이트
            if consultation_id not in self.session_data:
                self.session_data[consultation_id] = {
                    'sections': [],
                    'start_time': datetime.now(timezone.utc)
                }
            
            self.session_data[consultation_id]['sections'].append({
                'section_name': section_name,
                'difficulty_score': difficulty_score,
                'confusion_probability': confusion_probability,
                'comprehension_level': comprehension_level,
                'timestamp': datetime.now(timezone.utc)
            })
            
            # 7. 하이브리드 분석 추가
            hybrid_data = {}
            if hybrid_analyzer:
                try:
                    hybrid_result = hybrid_analyzer.analyze_text_hybrid(section_text)
                    hybrid_data = {
                        "difficult_terms": hybrid_result.difficult_terms,
                        "underlined_sections": hybrid_result.underlined_sections,
                        "detailed_explanations": hybrid_result.detailed_explanations
                    }
                except Exception as e:
                    print(f"하이브리드 분석 실패: {e}")
                    hybrid_data = {
                        "difficult_terms": [],
                        "underlined_sections": [],
                        "detailed_explanations": {}
                    }
            else:
                hybrid_data = {
                    "difficult_terms": [],
                    "underlined_sections": [],
                    "detailed_explanations": {}
                }
            
            result = {
                "status": status,
                "confused_sentences": confused_sentences,
                "ai_explanation": ai_explanation,
                "difficulty_score": round(difficulty_score, 2),
                "confusion_probability": round(confusion_probability, 2),
                "comprehension_level": comprehension_level,
                "recommendations": recommendations,
                "analysis_metadata": {
                    "section_length": len(section_text),
                    "reading_speed_wpm": len(section_text.split()) / (reading_time / 60) if reading_time > 0 else 0,
                    "analyzed_at": datetime.now(timezone.utc).isoformat()
                }
            }
            
            # 하이브리드 데이터 추가
            result.update(hybrid_data)
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


    # ===== 시선 추적 관련 메서드 =====
    
    def _init_session(self, consultation_id: str):
        """새로운 세션 초기화"""
        self.session_data[consultation_id] = {
            'gaze_history': deque(maxlen=1000),  # 최대 1000개의 시선 이력 유지
            'fixations': [],  # 감지된 고정점 목록
            'current_fixation': None,  # 현재 추적 중인 고정점
            'last_metrics_update': datetime.now(timezone.utc),
            'word_fixation_counts': defaultdict(timedelta),  # 단어별 누적 고정 시간
            'line_fixation_counts': defaultdict(timedelta),  # 줄별 누적 고정 시간
        }
    
    async def process_reading_data(self, reading_data: ReadingDataRequest) -> ReadingDataResponse:
        """
        프론트엔드로부터 받은 읽기 데이터를 처리하고 분석 결과를 반환
        
        Args:
            reading_data: 프론트엔드에서 전송한 시선 추적 데이터
            
        Returns:
            ReadingDataResponse: 분석 결과가 포함된 응답 객체
        """
        # 세션 데이터 초기화 (없는 경우)
        if reading_data.consultation_id not in self.session_data:
            self._init_session(reading_data.consultation_id)
            
        session = self.session_data[reading_data.consultation_id]
        
        # 텍스트 요소 저장 (매 요청마다 업데이트)
        session['text_elements'] = reading_data.text_elements
        
        # 시선 데이터 처리
        fixations = []
        for gaze_point in reading_data.gaze_data:
            fixation = await self._process_gaze_point(
                consultation_id=reading_data.consultation_id,
                gaze_point=gaze_point,
                text_elements=reading_data.text_elements
            )
            if fixation:
                fixations.append(fixation)
        
        # 메트릭 계산
        metrics = self._calculate_metrics(reading_data.consultation_id)
        
        # 응답 생성
        response = ReadingDataResponse(
            **reading_data.dict(),
            fixations=fixations,
            reading_metrics=metrics,
            processed_at=datetime.now(timezone.utc)
        )
        
        return response
    
    async def _process_gaze_point(
        self, 
        consultation_id: str, 
        gaze_point: GazePoint,
        text_elements: List[TextElement] = None
    ) -> Optional[FixationData]:
        """
        개별 시선 좌표를 처리하고 고정점이 감지되면 반환
        
        Args:
            consultation_id: 상담 세션 ID
            gaze_point: 처리할 시선 좌표
            text_elements: 현재 문서의 텍스트 요소 목록
            
        Returns:
            Optional[FixationData]: 감지된 고정점이 있으면 반환, 없으면 None
        """
        session = self.session_data[consultation_id]
        
        # 시선 이력에 추가
        session['gaze_history'].append(gaze_point)
        
        # 현재 고정점이 없으면 새로 시작
        if not session['current_fixation']:
            self._start_new_fixation(session, gaze_point)
            return None
            
        # 현재 고정점에 속하는지 확인
        if self._is_in_fixation(session, gaze_point):
            self._update_fixation(session, gaze_point)
            return None
            
        # 고정점 종료 및 반환 (텍스트 요소 정보 전달)
        return self._finalize_fixation(session, text_elements)
    
    def _start_new_fixation(self, session: dict, gaze_point: GazePoint):
        """새로운 고정점 추적을 시작"""
        session['current_fixation'] = {
            'start_time': gaze_point.timestamp,
            'points': [gaze_point],
            'sum_x': gaze_point.x,
            'sum_y': gaze_point.y,
            'min_x': gaze_point.x,
            'max_x': gaze_point.x,
            'min_y': gaze_point.y,
            'max_y': gaze_point.y,
        }
    
    def _is_in_fixation(self, session: dict, gaze_point: GazePoint) -> bool:
        """주어진 시선 좌표가 현재 고정점에 속하는지 확인"""
        fix = session['current_fixation']
        if not fix:
            return False
            
        # 고정점 내 분산 계산
        dispersion_x = fix['max_x'] - fix['min_x']
        dispersion_y = fix['max_y'] - fix['min_y']
        max_dispersion = max(dispersion_x, dispersion_y)
        
        # 임계값 초과 시 고정점 종료
        if max_dispersion > self.fixation_threshold:
            return False
            
        # 중심점과의 거리 계산
        n = len(fix['points'])
        centroid_x = fix['sum_x'] / n
        centroid_y = fix['sum_y'] / n
        distance = np.sqrt((gaze_point.x - centroid_x)**2 + (gaze_point.y - centroid_y)**2)
        
        return distance <= self.fixation_threshold
    
    def _update_fixation(self, session: dict, gaze_point: GazePoint):
        """현재 고정점을 새로운 시선 좌표로 업데이트"""
        fix = session['current_fixation']
        if not fix:
            return
            
        fix['points'].append(gaze_point)
        fix['sum_x'] += gaze_point.x
        fix['sum_y'] += gaze_point.y
        fix['min_x'] = min(fix['min_x'], gaze_point.x)
        fix['max_x'] = max(fix['max_x'], gaze_point.x)
        fix['min_y'] = min(fix['min_y'], gaze_point.y)
        fix['max_y'] = max(fix['max_y'], gaze_point.y)
    
    def _finalize_fixation(
        self, 
        session: dict, 
        text_elements: List[TextElement] = None
    ) -> Optional[FixationData]:
        """
        현재 고정점을 종료하고 FixationData 객체를 반환합니다.
        
        Args:
            session: 현재 세션 데이터
            text_elements: 텍스트 요소 목록 (선택사항)
            
        Returns:
            Optional[FixationData]: 완성된 고정점 데이터 또는 None
        """
        fix = session.get('current_fixation')
        if not fix or len(fix['points']) < 2:
            return None
            
        # 고정점 지속 시간 계산
        duration = fix['points'][-1].timestamp - fix['points'][0].timestamp
        
        # 최소/최대 지속 시간 검사
        if duration < self.min_fixation_duration or duration > self.max_fixation_duration:
            session['current_fixation'] = None
            return None
            
        # 고정점 데이터 생성
        n = len(fix['points'])
        centroid_x = fix['sum_x'] / n
        centroid_y = fix['sum_y'] / n
        
        # 분산 계산
        sum_sq_diff_x = sum((p.x - centroid_x)**2 for p in fix['points'])
        sum_sq_diff_y = sum((p.y - centroid_y)**2 for p in fix['points'])
        dispersion = np.sqrt((sum_sq_diff_x + sum_sq_diff_y) / n)
        
        fixation = FixationData(
            start_timestamp=fix['points'][0].timestamp,
            end_timestamp=fix['points'][-1].timestamp,
            duration=duration,  # timedelta 객체로 전달
            avg_x=centroid_x,
            avg_y=centroid_y,
            dispersion=dispersion
        )
        
        # 세션에 고정점 추가
        session['fixations'].append(fixation)
        session['current_fixation'] = None
        
        # 단어/줄 고정 시간 업데이트 (텍스트 요소가 제공된 경우에만)
        if text_elements:
            self._update_fixation_counts(session, fixation, text_elements)
        
        return fixation
    
    def _update_fixation_counts(
        self, 
        session: dict, 
        fixation: FixationData, 
        text_elements: List[TextElement]
    ) -> None:
        """
        고정점 정보를 바탕으로 단어/줄별 고정 시간을 업데이트
        
        Args:
            session: 현재 세션 데이터
            fixation: 고정점 데이터
            text_elements: 매핑할 텍스트 요소 목록
        """
        if not text_elements:
            return
            
        # 가장 가까운 텍스트 요소 찾기
        matched_element = self._find_closest_text(
            x=fixation.avg_x,
            y=fixation.avg_y,
            text_elements=text_elements
        )
        
        if matched_element:
            # 단어별 고정 시간 누적
            session['word_fixation_counts'][matched_element.text] += fixation.duration
            
            # 줄별 고정 시간 누적
            if hasattr(matched_element, 'line_number'):
                session['line_fixation_counts'][matched_element.line_number] += fixation.duration
    
    def _find_closest_text(
        self, 
        x: float, 
        y: float, 
        text_elements: List[TextElement],
        tolerance: float = 0.05  # 화면 크기의 5% 이내만 매칭
    ) -> Optional[TextElement]:
        """
        주어진 좌표에서 가장 가까운 텍스트 요소를 찾기
        
        Args:
            x: 정규화된 x 좌표 (0-1)
            y: 정규화된 y 좌표 (0-1)
            text_elements: 검색할 텍스트 요소 목록
            tolerance: 매칭 허용 오차 (0-1, 화면 크기 대비)
            
        Returns:
            Optional[TextElement]: 매칭된 가장 가까운 텍스트 요소 또는 None
        """
        if not text_elements:
            return None
            
        # 1. 경계 상자(bbox) 내에 직접 포함되는 텍스트 찾기
        for element in text_elements:
            x1, y1, x2, y2 = element.bbox
            if x1 <= x <= x2 and y1 <= y <= y2:
                return element
                
        # 2. 직접 포함되는 텍스트가 없을 경우, 가장 가까운 텍스트 찾기
        closest_element = None
        min_distance = float('inf')
        
        for element in text_elements:
            # 텍스트 요소의 중심점 계산
            x1, y1, x2, y2 = element.bbox
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            
            # 유클리드 거리 계산
            distance = np.sqrt((x - center_x)**2 + (y - center_y)**2)
            
            if distance < min_distance:
                min_distance = distance
                closest_element = element
                
        # 허용 오차 내에 있는 경우에만 반환
        return closest_element if min_distance <= tolerance else None
    
    def _calculate_metrics(self, consultation_id: str) -> ReadingMetrics:
        """현재까지의 시선 데이터를 기반으로 메트릭을 계산"""
        session = self.session_data[consultation_id]
        fixations = session['fixations']
        
        if not fixations:
            return ReadingMetrics(
                avg_fixation_duration=0,
                fixations_per_minute=0,
                regression_count=0
            )
        
        # 평균 고정 시간 (밀리초)
        avg_duration = sum(f.duration for f in fixations) / len(fixations)
        
        # 분당 고정점 수
        time_span = (fixations[-1].end_timestamp - fixations[0].start_timestamp).total_seconds()
        fpm = (len(fixations) / time_span) * 60 if time_span > 0 else 0
        
        # 회귀(재읽기) 횟수
        regression_count = self._count_regressions(fixations)
        
        return ReadingMetrics(
            avg_fixation_duration=avg_duration,
            fixations_per_minute=fpm,
            regression_count=regression_count
        )
    
    def _count_regressions(self, fixations: List[FixationData]) -> int:
        """
        고정점 목록에서 회귀(재읽기) 횟수를 계산
        """
        if len(fixations) < 2:
            return 0
            
        regressions = 0
        for i in range(1, len(fixations)):
            curr = fixations[i]
            prev = fixations[i-1]
            
            # y 좌표가 아래로 이동했는지 확인 (줄바꿈)
            if curr.avg_y > prev.avg_y + 0.02:  # 임계값: 화면의 2%
                # 다음 줄로 넘어갔을 때 x 좌표가 크게 왼쪽으로 이동했는지 확인
                if curr.avg_x < prev.avg_x - 0.1:  # 임계값: 화면의 10%
                    regressions += 1
            # 같은 줄에서 왼쪽으로 이동한 경우
            elif curr.avg_x < prev.avg_x - 0.02:  # 임계값: 화면의 2%
                # y 좌표가 크게 변하지 않았는지 확인 (실제로 재읽기인지 확인)
                if abs(curr.avg_y - prev.avg_y) < 0.02:  # 임계값: 화면의 2%
                    regressions += 1
                    
        return regressions

# 전역 서비스 인스턴스
eyetrack_service = EyeTrackingService()