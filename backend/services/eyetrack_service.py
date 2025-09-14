import sys
import os
from typing import Dict, List, Optional, Tuple
import asyncio
from datetime import datetime, timezone
import numpy as np

# eyetracking 모듈 import
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from eyetrack.gaze_tracker import EyeGazeTracker, GazeData
    from eyetrack.comprehension_analyzer import ComprehensionAnalyzer
    from eyetrack.hybrid_analyzer import HybridTextAnalyzer, HybridAnalysisResult
    EYETRACK_AVAILABLE = True
    print("Eyetrack 모듈들이 성공적으로 로드되었습니다")
except ImportError as e:
    print(f"Warning: eyetrack 모듈을 찾을 수 없습니다: {e}")
    EyeGazeTracker = None
    GazeData = None
    ComprehensionAnalyzer = None
    HybridTextAnalyzer = None
    HybridAnalysisResult = None
    EYETRACK_AVAILABLE = False

# AI 모델 매니저 import
try:
    from .ai_model_service import ai_model_manager
    AI_MODEL_AVAILABLE = True
except ImportError:
    print("Warning: AI 모델 서비스를 찾을 수 없습니다.")
    ai_model_manager = None
    AI_MODEL_AVAILABLE = False

class EyeTrackingService:
    """기존 eyetrack 모듈을 웹 서비스로 감싸는 서비스 레이어"""
    
    def __init__(self):
        self.analyzer = ComprehensionAnalyzer() if ComprehensionAnalyzer else None
        self.hybrid_analyzer = HybridTextAnalyzer() if HybridTextAnalyzer else None
        self.session_data = {}  # consultation_id별 세션 데이터
    
    def get_text_difficulty(self, section_text: str) -> float:
        """텍스트 난이도 분석 (기존 ComprehensionAnalyzer 활용 + 간단 fallback)"""
        
        # 기존 모듈 사용 (시선 데이터가 있을 때)
        if self.analyzer:
            # TODO: 실제 시선 데이터로 분석할 때는 이 부분 사용
            # 지금은 텍스트만으로 간단 분석
            pass
        
        # 간단한 키워드 기반 분석 (AI 모델 완성 전까지 임시)
        difficult_terms = [
            '중도해지', '우대금리', '복리', '예금자보호', '만기자동연장',
            '변동금리', '세액공제', '원천징수', '담보대출', '신용대출'
        ]
        
        term_count = sum(1 for term in difficult_terms if term in section_text)
        sentence_count = len([s for s in section_text.split('.') if s.strip()])
        
        # 간단한 난이도 계산
        base_difficulty = min(term_count * 0.15, 0.6)
        length_factor = min(len(section_text) / 200, 0.3)
        
        return min(base_difficulty + length_factor, 0.9)
    
    def calculate_confusion_probability(self, difficulty_score: float, reading_time: float, 
                                      expected_time: float = 30.0, section_length: int = 100) -> float:
        """간소화된 혼란도 계산 (기존 모듈로 대체 예정)"""
        
        # 기존 모듈 사용 가능시 사용
        if self.analyzer:
            # TODO: ComprehensionAnalyzer의 calculate_cognitive_load 메소드 활용
            pass
        
        # 간단한 혼란도 계산 (임시)
        time_factor = min(reading_time / expected_time, 2.0) - 1.0  # -1.0 ~ 1.0
        time_adjustment = abs(time_factor) * 0.2  # 너무 빠르거나 느리면 혼란도 증가
        
        confusion_prob = difficulty_score * 0.7 + time_adjustment * 0.3
        
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
        """AI 설명 생성 (GPT 스타일 시뮬레이션)"""
        
        # 키워드 기반 설명 매핑
        explanations_db = {
            "중도해지": {
                "simple": "약속한 기간 전에 예금을 찾는 것입니다.",
                "example": "1년 약속으로 넣은 돈을 6개월 만에 찾으면 중도해지예요.",
                "impact": "약속한 높은 이자 대신 낮은 이자만 받게 됩니다."
            },
            "우대금리": {
                "simple": "조건을 맞추면 더 높은 이자를 주는 혜택입니다.",
                "example": "급여통장으로 쓰거나 카드 사용하면 추가 이자를 받을 수 있어요.",
                "impact": "조건 미충족시 기본 이자만 적용됩니다."
            },
            "예금자보호": {
                "simple": "은행이 문제가 생겨도 돈을 보장해주는 제도입니다.",
                "example": "개인당 최대 5천만원까지 정부가 보장해줍니다.",
                "impact": "5천만원 초과 금액은 보장받기 어려울 수 있습니다."
            },
            "복리": {
                "simple": "이자에 다시 이자가 붙는 방식입니다.",
                "example": "100만원에 10% 이자가 붙으면, 다음엔 110만원에 10%가 붙어요.",
                "impact": "시간이 지날수록 이자가 점점 더 많이 받게 됩니다."
            },
            "변동금리": {
                "simple": "시장 상황에 따라 이자율이 바뀌는 방식입니다.",
                "example": "처음엔 3%였다가 나중에 4%로 오르거나 2%로 내릴 수 있어요.",
                "impact": "금리가 오르면 좋지만, 내리면 수익이 줄어들 수 있습니다."
            }
        }
        
        # 텍스트에서 키워드 찾기
        for keyword, explanation in explanations_db.items():
            if keyword in section_text:
                return (f"**{keyword}**란?\n"
                       f"• {explanation['simple']}\n"
                       f"• {explanation['example']}\n"
                       f"주의: {explanation['impact']}")
        
        # 키워드가 없으면 간단한 안내만
        return "궁금한 점이 있으시면 언제든 직원에게 문의하세요."
    
    async def analyze_reading_session(self, consultation_id: str, section_name: str, 
                                    section_text: str, reading_time: float, 
                                    gaze_data: Optional[Dict] = None,
                                    face_frame: Optional[np.ndarray] = None) -> Dict:
        """읽기 세션 분석 (메인 API 함수) - AI 모델 우선 사용"""
        
        try:
            # AI 모델 사용 가능시 AI 분석 우선
            if AI_MODEL_AVAILABLE and ai_model_manager:
                ai_result = await ai_model_manager.analyze_text(section_text)
                difficulty_score = ai_result.get('difficulty_score', 0.5)
                ai_explanation = ai_result.get('ai_explanation', '')
                confused_sentences = [s.get('sentence_id', 0) for s in ai_result.get('confused_sections', [])]
                
                # 얼굴 혼란도 분석 (face_frame이 있을 때만)
                face_confusion = {"confused": False, "probability": 0.0}
                if face_frame is not None and hasattr(ai_model_manager, 'hf_models'):
                    if ai_model_manager.hf_models:
                        try:
                            face_confusion = await ai_model_manager.hf_models.analyze_confusion_from_face(face_frame)
                        except Exception as e:
                            print(f"얼굴 분석 오류: {e}")
            else:
                # Fallback: 기존 로직 사용
                difficulty_score = self.get_text_difficulty(section_text)
                confused_sentences = self.identify_confused_sentences(section_text, difficulty_score)
                ai_explanation = self.generate_ai_explanation(section_text, confused_sentences)
                face_confusion = {"confused": False, "probability": 0.0}
            
            # 혼란도는 읽기 시간 고려해서 계산 (AI와 결합)
            confusion_probability = self.calculate_confusion_probability(
                difficulty_score, reading_time, section_length=len(section_text)
            )
            
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
            
            # 7. 텍스트 분석 (문장 + 단어 동시 분석)
            analysis_data = {}
            if self.hybrid_analyzer:
                try:
                    analysis_result = self.hybrid_analyzer.analyze_text_hybrid(section_text)
                    analysis_data = {
                        "difficult_terms": analysis_result.difficult_terms,
                        "underlined_sections": analysis_result.underlined_sections,
                        "detailed_explanations": analysis_result.detailed_explanations,
                        "overall_difficulty": analysis_result.overall_difficulty,
                        "comprehension_level": analysis_result.comprehension_level
                    }

                    # 분석 결과로 기존 값들 보완
                    if analysis_result.overall_difficulty > 0:
                        difficulty_score = (difficulty_score + analysis_result.overall_difficulty) / 2
                    if analysis_result.comprehension_level in ['high', 'medium', 'low']:
                        comprehension_level = analysis_result.comprehension_level

                except Exception as e:
                    print(f"텍스트 분석 실패: {e}")
                    analysis_data = {
                        "difficult_terms": [],
                        "underlined_sections": [],
                        "detailed_explanations": {},
                        "overall_difficulty": 0.0,
                        "comprehension_level": "medium"
                    }
            else:
                analysis_data = {
                    "difficult_terms": [],
                    "underlined_sections": [],
                    "detailed_explanations": {},
                    "overall_difficulty": 0.0,
                    "comprehension_level": "medium"
                }
            
            # 8. 세션 데이터 업데이트
            if consultation_id not in self.session_data:
                self.session_data[consultation_id] = {
                    'sections': [],
                    'start_time': datetime.now(timezone.utc)
                }
            
            # 세션 데이터 업데이트 (하이브리드 결과 포함)
            section_data = {
                'section_name': section_name,
                'difficulty_score': difficulty_score,
                'confusion_probability': confusion_probability,
                'comprehension_level': comprehension_level,
                'timestamp': datetime.now(timezone.utc)
            }

            # 텍스트 분석 결과도 세션에 저장
            if analysis_data:
                section_data.update({
                    'difficult_terms': analysis_data.get('difficult_terms', []),
                    'detailed_explanations': analysis_data.get('detailed_explanations', {})
                })

                # 세션 레벨에서도 업데이트
                self.session_data[consultation_id].update({
                    'current_section': section_name,
                    'difficult_terms': analysis_data.get('difficult_terms', []),
                    'detailed_explanations': analysis_data.get('detailed_explanations', {})
                })

            self.session_data[consultation_id]['sections'].append(section_data)
            
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
            
            # 분석 데이터 추가
            result.update(analysis_data)
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
    
    def _generate_recommendations(self, confusion_prob: float, difficulty: float, reading_time: float) -> List[str]:
        """간소화된 추천사항 생성 (AI 모델로 대체 예정)"""
        
        if confusion_prob > 0.7:
            return ["이해하기 어려운 부분이 있으시면 직원에게 설명을 요청하세요."]
        elif confusion_prob > 0.5:
            return ["중요한 내용이니 충분한 시간을 들여 확인해보세요."]
        else:
            return ["잘 이해하고 계십니다."]
    
    def get_session_summary(self, consultation_id: str) -> Optional[Dict]:
        """세션 전체 요약 정보 반환"""
        if consultation_id not in self.session_data:
            return None

        session = self.session_data[consultation_id]
        sections = session['sections']

        if not sections:
            return None

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

    def process_gaze_data(self, consultation_id: str, gaze_data: Dict) -> Dict:
        """실시간 시선 데이터 처리"""
        if consultation_id not in self.session_data:
            self.session_data[consultation_id] = {
                'gaze_points': [],
                'current_section': '',
                'confusion_level': 0.0,
                'start_time': datetime.now(timezone.utc)
            }

        session = self.session_data[consultation_id]
        session['gaze_points'].append({
            'x': gaze_data['x'],
            'y': gaze_data['y'],
            'timestamp': gaze_data['timestamp'],
            'confidence': gaze_data['confidence']
        })

        # 최근 시선 패턴 분석
        if len(session['gaze_points']) > 10:
            recent_points = session['gaze_points'][-10:]
            analysis = self._analyze_gaze_pattern(recent_points)
            session['confusion_level'] = analysis.get('confusion_level', 0.0)

        return {
            'processed': True,
            'gaze_points_count': len(session['gaze_points']),
            'current_confusion': session['confusion_level']
        }

    def get_current_confusion_status(self, consultation_id: str) -> Dict:
        """현재 혼란도 상태 반환 (프론트엔드 AI 도우미용)"""
        if consultation_id not in self.session_data:
            return {
                'is_confused': False,
                'confusion_probability': 0.0,
                'current_section': '',
                'ai_suggestion': None,
                'difficult_terms': [],
                'suggested_explanations': []
            }

        session = self.session_data[consultation_id]
        confusion_level = session.get('confusion_level', 0.0)
        is_confused = confusion_level > 0.7

        # AI 도우미 제안 생성
        ai_suggestion = None
        difficult_terms = session.get('difficult_terms', [])
        if is_confused:
            current_section = session.get('current_section', '현재 섹션')
            ai_suggestion = {
                'section': current_section,
                'explanation': f'{current_section}에서 어려운 부분이 감지되었습니다.',
                'simpleExample': '전문 용어나 복잡한 조건이 포함되어 있을 수 있습니다.'
            }

            # 어려운 용어가 있으면 구체적인 설명 추가
            if difficult_terms:
                ai_suggestion['explanation'] = f"'{difficult_terms[0].get('term', '용어')}'와 같은 금융 용어가 어려울 수 있습니다."

        return {
            'is_confused': is_confused,
            'confusion_probability': confusion_level,
            'current_section': session.get('current_section', ''),
            'ai_suggestion': ai_suggestion,
            'difficult_terms': difficult_terms[:3],  # 최대 3개까지
            'suggested_explanations': session.get('detailed_explanations', {})
        }

    def get_reading_progress(self, consultation_id: str) -> Dict:
        """읽기 진행률 반환"""
        if consultation_id not in self.session_data:
            return {
                'percentage': 0,
                'current_section': '',
                'sections_completed': 0,
                'total_sections': 0,
                'time_remaining': 0
            }

        session = self.session_data[consultation_id]
        sections_completed = len(session.get('sections', []))
        total_sections = 10

        percentage = min((sections_completed / total_sections) * 100, 100) if total_sections > 0 else 0
        time_remaining = max((total_sections - sections_completed) * 2, 0)

        return {
            'percentage': round(percentage),
            'current_section': session.get('current_section', ''),
            'sections_completed': sections_completed,
            'total_sections': total_sections,
            'time_remaining': time_remaining
        }

    def _analyze_gaze_pattern(self, gaze_points: List[Dict]) -> Dict:
        """시선 패턴 분석"""
        if len(gaze_points) < 3:
            return {'confusion_level': 0.0}

        total_distance = 0
        for i in range(1, len(gaze_points)):
            prev = gaze_points[i-1]
            curr = gaze_points[i]
            distance = ((curr['x'] - prev['x'])**2 + (curr['y'] - prev['y'])**2)**0.5
            total_distance += distance

        avg_distance = total_distance / (len(gaze_points) - 1)
        confusion_level = min(avg_distance / 100.0, 1.0)

        return {'confusion_level': confusion_level}

# 전역 서비스 인스턴스
eyetrack_service = EyeTrackingService()