"""
통합 분석 서비스
아이트래킹 + 얼굴 표정 + 텍스트 난이도를 종합하여 
고객의 이해도를 판단하고 필요시 문장 간소화 AI를 호출
"""

import logging
from typing import Dict, Optional, Any, Tuple
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class IntegratedAnalysisService:
    """통합 분석 서비스 - 모든 데이터를 종합하여 최종 판단"""
    
    def __init__(self):
        self.analysis_history = {}
        
        # 가중치 설정
        self.weights = {
            'text_difficulty': 0.35,  # 텍스트 난이도
            'face_confusion': 0.35,    # 얼굴 표정
            'gaze_pattern': 0.30       # 시선 패턴
        }
        
        # 임계값 설정
        self.thresholds = {
            'high_confusion': 0.7,     # 매우 혼란
            'moderate_confusion': 0.5, # 보통 혼란
            'low_confusion': 0.3       # 약간 혼란
        }
    
    async def analyze_integrated(
        self,
        consultation_id: str,
        section_name: str,
        section_text: str,
        text_difficulty: float,
        face_data: Optional[Dict] = None,
        gaze_data: Optional[Dict] = None,
        reading_time: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        통합 분석 수행
        
        Args:
            consultation_id: 상담 ID
            section_name: 섹션 이름
            section_text: 섹션 텍스트
            text_difficulty: 텍스트 난이도 (0-1)
            face_data: 얼굴 분석 데이터
            gaze_data: 시선 추적 데이터
            reading_time: 읽기 시간 (초)
            
        Returns:
            통합 분석 결과
        """
        
        # 1. 각 모달리티별 혼란도 계산
        text_confusion = self._calculate_text_confusion(text_difficulty, section_text)
        face_confusion = self._calculate_face_confusion(face_data)
        gaze_confusion = self._calculate_gaze_confusion(gaze_data, reading_time, len(section_text))
        
        # 2. 통합 혼란도 계산
        integrated_confusion = self._calculate_integrated_confusion(
            text_confusion, face_confusion, gaze_confusion
        )
        
        # 3. 이해도 레벨 결정
        comprehension_level, need_ai_help = self._determine_comprehension_level(
            integrated_confusion, face_confusion, gaze_confusion
        )
        
        # 4. AI 간소화 필요 여부 판단
        should_simplify = self._should_trigger_simplification(
            integrated_confusion, face_confusion, gaze_confusion, text_difficulty
        )
        
        # 5. 추천사항 생성
        recommendations = self._generate_recommendations(
            comprehension_level, text_confusion, face_confusion, gaze_confusion
        )
        
        # 6. 분석 이력 저장
        self._save_analysis_history(
            consultation_id, section_name, integrated_confusion, comprehension_level
        )
        
        result = {
            'consultation_id': consultation_id,
            'section_name': section_name,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            
            # 개별 분석 결과
            'individual_scores': {
                'text_difficulty': text_difficulty,
                'text_confusion': text_confusion,
                'face_confusion': face_confusion,
                'gaze_confusion': gaze_confusion
            },
            
            # 통합 분석 결과
            'integrated_confusion': integrated_confusion,
            'comprehension_level': comprehension_level,
            'need_ai_assistance': need_ai_help,
            'should_simplify_text': should_simplify,
            
            # 추천사항
            'recommendations': recommendations,
            
            # 디버그 정보
            'debug_info': {
                'weights_used': self.weights,
                'thresholds': self.thresholds,
                'reading_time': reading_time
            }
        }
        
        logger.info(f"통합 분석 완료 - 상담ID: {consultation_id}, "
                   f"섹션: {section_name}, "
                   f"통합 혼란도: {integrated_confusion:.2f}, "
                   f"AI 도움 필요: {need_ai_help}")
        
        return result
    
    def _calculate_text_confusion(self, difficulty: float, text: str) -> float:
        """텍스트 기반 혼란도 계산"""
        base_confusion = difficulty
        
        # 금융 전문 용어 체크
        complex_terms = [
            '압류', '가압류', '질권', '양도', '상계',
            '연체이자', '가산금리', '변동금리', '고정금리',
            '중도상환수수료', '만기일시상환', '원리금균등상환'
        ]
        
        term_count = sum(1 for term in complex_terms if term in text)
        term_penalty = min(term_count * 0.05, 0.2)  # 최대 0.2 추가
        
        return min(base_confusion + term_penalty, 1.0)
    
    def _calculate_face_confusion(self, face_data: Optional[Dict]) -> float:
        """얼굴 표정 기반 혼란도 계산 - CNN-LSTM 결과 사용"""
        if not face_data:
            return 0.0
        
        # CNN-LSTM에서 나온 confusion 값 직접 사용
        confusion_prob = face_data.get('confusion_probability', 0.0)
        
        # emotions 딕셔너리에서도 confusion 확인 (WebcamFaceDetection에서 오는 경우)
        emotions = face_data.get('emotions', {})
        if emotions and 'confusion' in emotions:
            # 새로운 CNN-LSTM 기반 값 우선 사용
            return emotions.get('confusion', confusion_prob)
        
        return confusion_prob
    
    def _calculate_gaze_confusion(self, gaze_data: Optional[Dict], 
                                  reading_time: Optional[float],
                                  text_length: int) -> float:
        """시선 패턴 기반 혼란도 계산"""
        if not gaze_data:
            return 0.0
        
        confusion = 0.0
        
        # 1. 고정 시간 분석
        fixation_duration = gaze_data.get('avg_fixation_duration', 250)
        if fixation_duration > 400:  # 400ms 이상은 어려움
            confusion += 0.3
        elif fixation_duration > 300:
            confusion += 0.15
        
        # 2. 회귀(재읽기) 분석
        regression_count = gaze_data.get('regression_count', 0)
        if regression_count > 3:
            confusion += 0.3
        elif regression_count > 1:
            confusion += 0.15
        
        # 3. 시선 분산도
        dispersion = gaze_data.get('gaze_dispersion', 50)
        if dispersion > 150:  # 시선이 많이 흩어짐
            confusion += 0.2
        elif dispersion > 100:
            confusion += 0.1
        
        # 4. 읽기 속도 분석
        if reading_time and text_length > 0:
            # 평균 읽기 속도: 분당 200-250 단어 (한글 기준 약 분당 300-400자)
            expected_time = text_length / 6  # 초당 약 6글자
            if reading_time > expected_time * 1.5:
                confusion += 0.2
        
        # 5. 스킵 패턴 (텍스트를 건너뛴 경우)
        skip_count = gaze_data.get('skip_count', 0)
        if skip_count > 2:
            confusion -= 0.1  # 스킵이 많으면 오히려 관심 없음
        
        return max(0, min(confusion, 1.0))
    
    def _calculate_integrated_confusion(self, text: float, face: float, gaze: float) -> float:
        """통합 혼란도 계산 (가중 평균 + 보정)"""
        
        # 기본 가중 평균
        weighted_avg = (
            text * self.weights['text_difficulty'] +
            face * self.weights['face_confusion'] +
            gaze * self.weights['gaze_pattern']
        )
        
        # 극단값 보정: 하나라도 매우 높으면 전체 상향
        max_confusion = max(text, face, gaze)
        if max_confusion > 0.8:
            weighted_avg = max(weighted_avg, max_confusion * 0.85)
        
        # 일치도 보너스: 모든 지표가 비슷하면 신뢰도 높음
        variance = self._calculate_variance([text, face, gaze])
        if variance < 0.1:  # 지표들이 일치
            confidence_bonus = 0.05
            weighted_avg = min(weighted_avg + confidence_bonus, 1.0)
        
        return weighted_avg
    
    def _determine_comprehension_level(self, integrated: float, 
                                       face: float, gaze: float) -> Tuple[str, bool]:
        """이해도 레벨 및 AI 도움 필요 여부 결정"""
        
        need_ai = False
        
        if integrated > self.thresholds['high_confusion']:
            level = 'low'
            need_ai = True
        elif integrated > self.thresholds['moderate_confusion']:
            level = 'medium'
            # 얼굴이나 시선이 특히 혼란스러우면 AI 도움
            if face > 0.7 or gaze > 0.7:
                need_ai = True
        elif integrated > self.thresholds['low_confusion']:
            level = 'medium'
        else:
            level = 'high'
        
        return level, need_ai
    
    def _should_trigger_simplification(self, integrated: float, face: float, 
                                       gaze: float, text_difficulty: float) -> bool:
        """문장 간소화 AI 트리거 여부 결정"""
        
        # 케이스 1: 통합 혼란도가 높음
        if integrated > 0.65:
            return True
        
        # 케이스 2: 얼굴 표정이 매우 혼란스럽고 텍스트도 어려움
        if face > 0.7 and text_difficulty > 0.6:
            return True
        
        # 케이스 3: 시선 패턴이 매우 혼란스럽고 텍스트도 어려움  
        if gaze > 0.7 and text_difficulty > 0.6:
            return True
        
        # 케이스 4: 모든 지표가 중간 이상
        if face > 0.5 and gaze > 0.5 and text_difficulty > 0.5:
            return True
        
        return False
    
    def _generate_recommendations(self, level: str, text: float, 
                                  face: float, gaze: float) -> list:
        """개인화된 추천사항 생성"""
        
        recommendations = []
        
        if level == 'low':
            recommendations.append("이 부분이 어려우신 것 같습니다. 천천히 다시 설명드릴게요.")
            
            if text > 0.7:
                recommendations.append("전문 용어를 쉬운 말로 바꿔드리겠습니다.")
            if face > 0.7:
                recommendations.append("혼란스러워 보이시네요. 질문 있으시면 말씀해주세요.")
            if gaze > 0.7:
                recommendations.append("중요한 부분을 다시 강조해드리겠습니다.")
                
        elif level == 'medium':
            recommendations.append("이해에 도움이 필요하시면 말씀해주세요.")
            
            if text > 0.5:
                recommendations.append("핵심 내용을 요약해드릴 수 있습니다.")
                
        else:  # high
            recommendations.append("잘 이해하고 계신 것 같습니다.")
        
        return recommendations
    
    def _save_analysis_history(self, consultation_id: str, section: str,
                               confusion: float, level: str):
        """분석 이력 저장"""
        if consultation_id not in self.analysis_history:
            self.analysis_history[consultation_id] = []
        
        self.analysis_history[consultation_id].append({
            'section': section,
            'confusion': confusion,
            'level': level,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    
    def _calculate_variance(self, values: list) -> float:
        """분산 계산"""
        if not values:
            return 0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance
    
    def get_consultation_summary(self, consultation_id: str) -> Dict:
        """상담 전체 요약"""
        if consultation_id not in self.analysis_history:
            return {}
        
        history = self.analysis_history[consultation_id]
        if not history:
            return {}
        
        avg_confusion = sum(h['confusion'] for h in history) / len(history)
        low_comprehension_count = sum(1 for h in history if h['level'] == 'low')
        
        return {
            'total_sections': len(history),
            'average_confusion': avg_confusion,
            'low_comprehension_sections': low_comprehension_count,
            'need_follow_up': low_comprehension_count > 2 or avg_confusion > 0.6
        }


# 싱글톤 인스턴스
integrated_analyzer = IntegratedAnalysisService()