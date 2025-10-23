"""
금융 문장 리스크 분석 서비스
고위험 키워드 사전 기반으로 문장의 위험도 평가
"""
import re
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class RiskAnalyzer:
    """금융 문장 리스크 분석기"""

    # 고위험 키워드 사전 (키워드: 가중치)
    CRITICAL_KEYWORDS = {
        # 원금 손실 관련
        "원금손실": 1.0,
        "원금보장 안됨": 1.0,
        "원금 전액 손실": 1.0,
        "투자원금": 0.9,
        "손실 가능": 0.8,

        # 녹인(Knock-in) 관련
        "녹인": 1.0,
        "knock-in": 1.0,
        "knock in": 1.0,
        "낙인": 1.0,
        "배리어": 0.9,
        "barrier": 0.9,

        # 조기상환/만기 관련
        "조기상환": 0.7,
        "만기": 0.6,
        "상환불가": 0.9,
        "중도상환": 0.7,

        # 파생상품 리스크
        "파생결합증권": 0.8,
        "파생상품": 0.8,
        "레버리지": 0.9,
        "leverage": 0.9,
        "인버스": 0.9,
        "inverse": 0.9,

        # 기타 고위험 용어
        "원금보장 불가": 1.0,
        "손실률": 0.8,
        "최대손실": 0.9,
        "투자위험": 0.8,
        "환율변동": 0.7,
        "신용위험": 0.8,
        "발행회사 부도": 1.0,
        "디폴트": 0.9,
        "default": 0.9,
    }

    # 고위험 패턴 (정규표현식)
    CRITICAL_PATTERNS = [
        r"원금.*손실",
        r"손실.*발생",
        r"\d+%.*손실",
        r"투자.*위험",
        r"보장.*않",
        r"보장.*없",
    ]

    # 리스크 레벨 임계값
    RISK_THRESHOLDS = {
        "critical": 0.8,  # 치명적 위험
        "high": 0.6,      # 높은 위험
        "medium": 0.4,    # 중간 위험
        "low": 0.0        # 낮은 위험
    }

    def __init__(self):
        self.keyword_dict = self.CRITICAL_KEYWORDS
        self.patterns = [re.compile(p, re.IGNORECASE) for p in self.CRITICAL_PATTERNS]
        logger.info(f"✅ RiskAnalyzer 초기화 완료 (키워드: {len(self.keyword_dict)}개)")

    def analyze_text(self, text: str) -> Dict:
        """
        텍스트의 리스크 분석

        Args:
            text: 분석할 텍스트

        Returns:
            {
                'risk_score': float (0-1),
                'risk_level': str ('critical'|'high'|'medium'|'low'),
                'risk_keywords': Dict[str, float],
                'risk_tags': List[str],
                'matched_patterns': List[str]
            }
        """
        if not text:
            return self._get_default_result()

        # 1. 키워드 매칭
        risk_keywords = {}
        total_weight = 0.0

        for keyword, weight in self.keyword_dict.items():
            if keyword in text:
                risk_keywords[keyword] = weight
                total_weight += weight

        # 2. 패턴 매칭
        matched_patterns = []
        for pattern in self.patterns:
            matches = pattern.findall(text)
            if matches:
                matched_patterns.extend(matches)
                total_weight += 0.3  # 패턴 매칭당 가중치

        # 3. 리스크 점수 계산 (0-1 스케일로 정규화)
        risk_score = min(total_weight / 3.0, 1.0)  # 최대 3개 키워드 기준

        # 4. 리스크 레벨 결정
        risk_level = self._determine_risk_level(risk_score)

        # 5. 리스크 태그 생성
        risk_tags = list(risk_keywords.keys())

        return {
            'risk_score': round(risk_score, 2),
            'risk_level': risk_level,
            'risk_keywords': risk_keywords,
            'risk_tags': risk_tags,
            'matched_patterns': list(set(matched_patterns))
        }

    def _determine_risk_level(self, score: float) -> str:
        """리스크 점수를 레벨로 변환"""
        if score >= self.RISK_THRESHOLDS['critical']:
            return 'critical'
        elif score >= self.RISK_THRESHOLDS['high']:
            return 'high'
        elif score >= self.RISK_THRESHOLDS['medium']:
            return 'medium'
        else:
            return 'low'

    def _get_default_result(self) -> Dict:
        """기본 결과 반환"""
        return {
            'risk_score': 0.0,
            'risk_level': 'low',
            'risk_keywords': {},
            'risk_tags': [],
            'matched_patterns': []
        }

    def analyze_sections(self, sections: List[Dict]) -> List[Dict]:
        """
        여러 섹션의 리스크 분석

        Args:
            sections: [{'section_name': str, 'section_text': str, ...}, ...]

        Returns:
            원본 섹션 + 리스크 분석 결과
        """
        results = []

        for section in sections:
            section_text = section.get('section_text', '') or section.get('text', '')
            risk_result = self.analyze_text(section_text)

            # 원본 섹션에 리스크 정보 추가
            enriched_section = {**section, **risk_result}
            results.append(enriched_section)

        return results

    def filter_high_risk_sections(
        self,
        sections: List[Dict],
        min_level: str = 'high'
    ) -> List[Dict]:
        """
        고위험 섹션만 필터링

        Args:
            sections: 분석된 섹션 리스트
            min_level: 최소 위험 레벨 ('critical', 'high', 'medium', 'low')

        Returns:
            고위험 섹션만 포함된 리스트
        """
        level_order = ['low', 'medium', 'high', 'critical']
        min_index = level_order.index(min_level)

        return [
            section for section in sections
            if level_order.index(section.get('risk_level', 'low')) >= min_index
        ]


# 전역 인스턴스
risk_analyzer = RiskAnalyzer()


# 사용 예시
if __name__ == "__main__":
    # 테스트
    test_texts = [
        "투자기간 중 종가 기준으로 최초기준가격의 50% 미만으로 하락한 기초자산이 있는 경우 원금손실이 발생합니다.",
        "예금자보호법에 따라 5천만원까지 보호됩니다.",
        "조기상환 평가일에 모든 기초자산이 조기상환가격 이상이면 조기상환됩니다.",
        "knock-in 배리어 터치 시 원금 전액 손실 가능합니다."
    ]

    for i, text in enumerate(test_texts, 1):
        result = risk_analyzer.analyze_text(text)
        print(f"\n=== 테스트 {i} ===")
        print(f"텍스트: {text[:50]}...")
        print(f"리스크 점수: {result['risk_score']}")
        print(f"리스크 레벨: {result['risk_level']}")
        print(f"키워드: {result['risk_tags']}")
