import sys
import os
from typing import Dict, List, Optional, Tuple
import asyncio
from datetime import datetime, timezone

# eyetrack 모듈 import (기존 코드 재사용)
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'eyetrack'))

try:
    from comprehension_analyzer import ComprehensionAnalyzer, ComprehensionMetrics, RealTimeComprehensionMonitor
    from hybrid_analyzer import hybrid_analyzer
except ImportError:
    print("Warning: eyetrack 모듈을 찾을 수 없습니다. 시뮬레이션 모드로 동작합니다.")
    ComprehensionAnalyzer = None
    ComprehensionMetrics = None
    RealTimeComprehensionMonitor = None
    hybrid_analyzer = None

class EyeTrackingService:
    """기존 eyetrack 모듈을 웹 서비스로 감싸는 서비스 레이어"""
    
    def __init__(self):
        self.analyzer = ComprehensionAnalyzer() if ComprehensionAnalyzer else None
        self.monitor = RealTimeComprehensionMonitor() if RealTimeComprehensionMonitor else None
        self.session_data = {}  # consultation_id별 세션 데이터
    
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
        
        # 기본 설명 (키워드가 없는 경우)
        if confused_sentences and len(confused_sentences) > 0:
            return (f"**이 부분이 복잡하신가요?**\n"
                   f"• 금융 약관에는 법적 보호를 위한 중요한 내용들이 포함되어 있습니다.\n"
                   f"• 천천히 읽어보시고, 궁금한 점은 언제든 문의하세요.\n"
                   f"주의: 특히 {len(confused_sentences)}개 문장은 주의 깊게 확인해보세요.")
        
        return ("**약관 내용 안내**\n"
               "• 이 내용은 상품의 중요한 조건들을 설명하고 있습니다.\n"
               "• 이해가 어려우시면 언제든지 직원에게 설명을 요청하세요.\n"
               "주의: 가입 전에 모든 조건을 충분히 이해하시는 것이 중요합니다.")
    
    async def analyze_reading_session(self, consultation_id: str, section_name: str, 
                                    section_text: str, reading_time: float, 
                                    gaze_data: Optional[Dict] = None) -> Dict:
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

# 전역 서비스 인스턴스
eyetrack_service = EyeTrackingService()