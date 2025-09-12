import re
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import time

@dataclass
class WordAnalysis:
    word: str
    difficulty_score: float
    needs_highlight: bool
    fixation_time: float
    position: Tuple[int, int]

@dataclass
class SentenceAnalysis:
    sentence: str
    sentence_id: str
    difficulty_score: float
    key_terms: List[str]
    syntax_complexity: float
    needs_explanation: bool
    confused_reason: str

@dataclass 
class HybridAnalysisResult:
    # 단어별 분석 (오른쪽 사이드바용)
    difficult_terms: List[Dict[str, any]]
    
    # 문장별 분석 (밑줄 및 팝업용)
    underlined_sections: List[Dict[str, any]]
    
    # 상세 설명 (팝업용)
    detailed_explanations: Dict[str, Dict[str, str]]
    
    # 전체 분석 요약
    overall_difficulty: float
    comprehension_level: str

class HybridTextAnalyzer:
    """문장과 단어를 동시에 분석하는 하이브리드 분석기"""
    
    def __init__(self):
        # 어려운 금융 용어 데이터베이스
        self.difficult_financial_terms = {
            # 기본 금융 용어
            '중도해지': {
                'difficulty': 0.8,
                'definition': '만기 전에 예금을 찾는 것',
                'detailed': '정기예금이나 적금의 만기일 이전에 예금을 인출하는 것으로, 이 경우 약정한 이자율보다 낮은 중도해지 이율이 적용됩니다.'
            },
            '우대금리': {
                'difficulty': 0.7, 
                'definition': '조건 충족 시 추가 이자',
                'detailed': '은행에서 정한 특정 조건(급여이체, 카드사용 등)을 충족할 경우 기본 금리에 추가로 제공하는 이자율입니다.'
            },
            '예금자보호': {
                'difficulty': 0.6,
                'definition': '5천만원까지 보장',
                'detailed': '예금보험공사에서 은행이 파산하더라도 예금자 1인당 원금과 이자를 합쳐 최대 5천만원까지 보장해주는 제도입니다.'
            },
            '복리': {
                'difficulty': 0.7,
                'definition': '이자에 다시 이자가 붙는 방식',
                'detailed': '원금에서 발생한 이자를 원금에 합쳐서 다시 이자를 계산하는 방식으로, 시간이 지날수록 이자가 기하급수적으로 증가합니다.'
            },
            '단리': {
                'difficulty': 0.5,
                'definition': '원금에만 이자가 붙는 방식', 
                'detailed': '처음 맡긴 원금에만 이자를 계산하는 방식으로, 복리에 비해 이자 증가폭이 작습니다.'
            },
            '만기자동연장': {
                'difficulty': 0.6,
                'definition': '만기시 자동으로 재예치',
                'detailed': '예금이 만료될 때 별도 해지 신청이 없으면 자동으로 같은 조건으로 재예치되는 서비스입니다.'
            },
            '변동금리': {
                'difficulty': 0.8,
                'definition': '시장상황에 따라 금리 변동',
                'detailed': '시장 금리나 기준금리 변동에 따라 적용 금리가 주기적으로 조정되는 금리 방식입니다.'
            },
            '고정금리': {
                'difficulty': 0.4,
                'definition': '계약기간 중 금리 고정',
                'detailed': '예금 가입시 정한 금리가 만기까지 변하지 않는 금리 방식입니다.'
            }
        }
        
        # 복잡한 문법 패턴
        self.complex_patterns = [
            r'~에 따라(?:서)?', r'~을 제외하고', r'~를 조건으로', r'~에 한하여',
            r'단,', r'다만,', r'또한,', r'따라서,', r'그러나,', r'또는',
            r'상기', r'해당', r'관련', r'준용', r'적용', r'제외', r'포함'
        ]
    
    def analyze_text_hybrid(self, text: str, fixations: List = None) -> HybridAnalysisResult:
        """텍스트를 단어와 문장 단위로 동시 분석"""
        
        # 1. 문장 단위로 분할
        sentences = self._split_into_sentences(text)
        
        # 2. 각 문장 분석
        sentence_analyses = []
        all_difficult_terms = []
        
        for i, sentence in enumerate(sentences):
            if sentence.strip():
                sentence_analysis = self._analyze_sentence(sentence, f"sentence_{i+1}", fixations)
                sentence_analyses.append(sentence_analysis)
                
                # 문장에서 어려운 용어 추출
                sentence_terms = self._extract_difficult_terms(sentence)
                all_difficult_terms.extend(sentence_terms)
        
        # 3. 중복 제거 및 정렬
        unique_terms = self._deduplicate_terms(all_difficult_terms)
        
        # 4. 밑줄 칠 섹션 결정
        underlined_sections = [
            {
                "text": analysis.sentence,
                "section_id": analysis.sentence_id,
                "start_position": 0,  # 실제로는 계산 필요
                "end_position": len(analysis.sentence),
                "difficulty_reason": analysis.confused_reason
            }
            for analysis in sentence_analyses if analysis.needs_explanation
        ]
        
        # 5. 상세 설명 생성
        detailed_explanations = {}
        for analysis in sentence_analyses:
            if analysis.needs_explanation:
                detailed_explanations[analysis.sentence_id] = self._generate_detailed_explanation(analysis)
        
        # 6. 전체 난이도 계산
        overall_difficulty = np.mean([analysis.difficulty_score for analysis in sentence_analyses]) if sentence_analyses else 0.0
        comprehension_level = self._determine_comprehension_level(overall_difficulty)
        
        return HybridAnalysisResult(
            difficult_terms=unique_terms,
            underlined_sections=underlined_sections,
            detailed_explanations=detailed_explanations,
            overall_difficulty=overall_difficulty,
            comprehension_level=comprehension_level
        )
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """텍스트를 문장 단위로 분할"""
        # 한국어 문장 분할 (. ! ? 기준, 단 숫자.숫자는 제외)
        sentences = re.split(r'(?<!\d)\.(?!\d)|[!?]', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _analyze_sentence(self, sentence: str, sentence_id: str, fixations: List = None) -> SentenceAnalysis:
        """개별 문장 분석"""
        
        # 1. 문장 길이 복잡도
        length_complexity = min(len(sentence) / 50, 1.0)  # 50자 기준 정규화
        
        # 2. 어려운 용어 밀도
        difficult_terms = [term for term in self.difficult_financial_terms.keys() if term in sentence]
        term_density = len(difficult_terms) / max(len(sentence.split()), 1)
        
        # 3. 문법 복잡도
        complex_pattern_count = sum(1 for pattern in self.complex_patterns 
                                  if re.search(pattern, sentence))
        syntax_complexity = min(complex_pattern_count / 5, 1.0)
        
        # 4. 숫자/퍼센트 포함도
        numbers = re.findall(r'\d+(?:\.\d+)?%?', sentence)
        number_density = len(numbers) / max(len(sentence.split()), 1)
        
        # 5. 종합 난이도 계산
        difficulty_score = (
            length_complexity * 0.2 +
            term_density * 0.4 + 
            syntax_complexity * 0.25 +
            number_density * 0.15
        )
        
        # 6. 설명 필요 여부 판단
        needs_explanation = difficulty_score > 0.6 or len(difficult_terms) >= 2
        
        # 7. 혼란 이유 생성
        confused_reason = self._generate_confusion_reason(
            difficulty_score, difficult_terms, complex_pattern_count
        )
        
        return SentenceAnalysis(
            sentence=sentence,
            sentence_id=sentence_id,
            difficulty_score=difficulty_score,
            key_terms=difficult_terms,
            syntax_complexity=syntax_complexity,
            needs_explanation=needs_explanation,
            confused_reason=confused_reason
        )
    
    def _extract_difficult_terms(self, sentence: str) -> List[Dict[str, any]]:
        """문장에서 어려운 용어 추출"""
        found_terms = []
        
        for term, info in self.difficult_financial_terms.items():
            if term in sentence:
                found_terms.append({
                    "term": term,
                    "simple_definition": info['definition'],
                    "difficulty_score": info['difficulty'],
                    "detailed_explanation": info['detailed']
                })
        
        return found_terms
    
    def _deduplicate_terms(self, terms_list: List[Dict]) -> List[Dict]:
        """중복 용어 제거 및 난이도순 정렬"""
        unique_terms = {}
        
        for term_info in terms_list:
            term = term_info['term']
            if term not in unique_terms or unique_terms[term]['difficulty_score'] < term_info['difficulty_score']:
                unique_terms[term] = term_info
        
        # 난이도 높은 순으로 정렬, 최대 5개까지
        sorted_terms = sorted(unique_terms.values(), 
                             key=lambda x: x['difficulty_score'], 
                             reverse=True)
        
        return sorted_terms[:5]
    
    def _generate_confusion_reason(self, difficulty: float, terms: List[str], complex_count: int) -> str:
        """혼란 이유 생성"""
        reasons = []
        
        if difficulty > 0.8:
            reasons.append("매우 복잡한 내용")
        elif difficulty > 0.6:
            reasons.append("다소 복잡한 내용")
            
        if len(terms) >= 3:
            reasons.append("여러 전문용어 포함")
        elif len(terms) >= 1:
            reasons.append("전문용어 포함")
            
        if complex_count >= 2:
            reasons.append("복잡한 문법 구조")
            
        return ", ".join(reasons) if reasons else "일반적인 내용"
    
    def _generate_detailed_explanation(self, analysis: SentenceAnalysis) -> Dict[str, str]:
        """상세 설명 생성"""
        
        # 주요 용어들의 설명 조합
        term_explanations = []
        for term in analysis.key_terms:
            if term in self.difficult_financial_terms:
                term_explanations.append(
                    f"{term}: {self.difficult_financial_terms[term]['detailed']}"
                )
        
        # 예시 생성 (간단한 룰 기반)
        example = self._generate_example(analysis.sentence, analysis.key_terms)
        
        # 영향 설명
        impact = self._generate_impact_explanation(analysis.key_terms)
        
        return {
            "title": "문장 상세 설명",
            "explanation": f"이 문장은 {analysis.confused_reason}을 다루고 있습니다. " + 
                          " ".join(term_explanations),
            "example": example,
            "impact": impact
        }
    
    def _generate_example(self, sentence: str, key_terms: List[str]) -> str:
        """간단한 예시 생성"""
        if "중도해지" in key_terms and "우대금리" in key_terms:
            return "예: 1년 약속 4% 예금을 6개월 만에 해지하면 0.5% 정도만 받게 됩니다."
        elif "중도해지" in key_terms:
            return "예: 만기 전에 예금을 찾으면 약정 이자율보다 낮은 이자를 받습니다."
        elif "우대금리" in key_terms:
            return "예: 급여이체 고객은 기본 3%에 0.2% 추가하여 3.2%를 받습니다."
        else:
            return "구체적인 예시는 직원에게 문의하세요."
    
    def _generate_impact_explanation(self, key_terms: List[str]) -> str:
        """영향 설명 생성"""
        if "중도해지" in key_terms:
            return "중도해지시 이자 수익이 크게 줄어들 수 있으니 신중히 결정하세요."
        elif "우대금리" in key_terms:
            return "우대 조건을 충족하면 더 높은 수익을 얻을 수 있습니다."
        else:
            return "이 조건들이 여러분의 수익에 영향을 줄 수 있습니다."
    
    def _determine_comprehension_level(self, difficulty: float) -> str:
        """이해도 수준 결정"""
        if difficulty < 0.3:
            return "high"
        elif difficulty < 0.6: 
            return "medium"
        else:
            return "low"

# 전역 인스턴스
hybrid_analyzer = HybridTextAnalyzer()