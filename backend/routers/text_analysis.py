from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
import logging
import sys
import os

# eyetrack과 text_simplifier 모듈 import를 위한 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from eyetrack.hybrid_analyzer import HybridTextAnalyzer
    HYBRID_ANALYZER_AVAILABLE = True
except ImportError as e:
    print(f"Warning: hybrid_analyzer 모듈을 찾을 수 없습니다: {e}")
    HYBRID_ANALYZER_AVAILABLE = False

try:
    from text_simplifier_krfinbert_kogpt2 import FinancialTextSimplifier
    TEXT_SIMPLIFIER_AVAILABLE = True
except ImportError as e:
    print(f"Warning: text_simplifier 모듈을 찾을 수 없습니다: {e}")
    TEXT_SIMPLIFIER_AVAILABLE = False

router = APIRouter()
logger = logging.getLogger(__name__)

# Request/Response 모델
class TextAnalysisRequest(BaseModel):
    section_text: str
    consultation_id: str
    current_section: str = ""

class DifficultSentence(BaseModel):
    sentence: str
    sentence_id: str
    difficulty_score: float
    simplified_explanation: str
    original_position: int

class TextAnalysisResponse(BaseModel):
    # 우측 사이드바용 주요 용어
    difficult_terms: List[Dict[str, str]]

    # PDF 밑줄용 어려운 문장들
    difficult_sentences: List[DifficultSentence]

    # 전체 분석 요약
    overall_difficulty: float
    comprehension_level: str

# 전역 분석기 인스턴스 초기화
if HYBRID_ANALYZER_AVAILABLE:
    hybrid_analyzer = HybridTextAnalyzer()
else:
    hybrid_analyzer = None

if TEXT_SIMPLIFIER_AVAILABLE:
    try:
        text_simplifier = FinancialTextSimplifier()
        # 모델이 학습되지 않은 경우를 위한 간단한 테스트
        print("텍스트 간소화 모델 초기화 중...")
    except Exception as e:
        print(f"텍스트 간소화 모델 초기화 실패: {e}")
        text_simplifier = None
else:
    text_simplifier = None

@router.post("/analyze-text", response_model=TextAnalysisResponse)
async def analyze_text(request: TextAnalysisRequest):
    """
    PDF 텍스트를 분석하여 이해도가 낮은 문장과 주요 용어를 추출
    """
    try:
        logger.info(f"텍스트 분석 시작: {request.consultation_id}")

        if not hybrid_analyzer:
            return await fallback_analysis(request)

        # 1. 하이브리드 분석 실행
        analysis_result = hybrid_analyzer.analyze_text_hybrid(
            text=request.section_text,
            fixations=None
        )

        # 2. 이해도 낮은 문장들 처리
        difficult_sentences = []

        for section in analysis_result.underlined_sections:
            sentence_text = section["text"]
            sentence_id = section["section_id"]

            # 문장 간소화 (text_simplifier 사용)
            simplified_text = await simplify_sentence(sentence_text)

            difficult_sentences.append(DifficultSentence(
                sentence=sentence_text,
                sentence_id=sentence_id,
                difficulty_score=0.8,  # hybrid_analyzer에서 이미 필터링됨
                simplified_explanation=simplified_text,
                original_position=section.get("start_position", 0)
            ))

        # 3. 우측 사이드바용 주요 용어 추출
        sidebar_terms = []
        for term_info in analysis_result.difficult_terms[:5]:  # 최대 5개
            sidebar_terms.append({
                "term": term_info["term"],
                "definition": term_info["simple_definition"]
            })

        response = TextAnalysisResponse(
            difficult_terms=sidebar_terms,
            difficult_sentences=difficult_sentences,
            overall_difficulty=analysis_result.overall_difficulty,
            comprehension_level=analysis_result.comprehension_level
        )

        logger.info(f"분석 완료: 어려운 문장 {len(difficult_sentences)}개, 주요 용어 {len(sidebar_terms)}개")
        return response

    except Exception as e:
        logger.error(f"텍스트 분석 실패: {e}")
        raise HTTPException(status_code=500, detail=f"분석 중 오류 발생: {str(e)}")

async def simplify_sentence(sentence: str) -> str:
    """문장을 간소화하여 설명 생성"""

    if text_simplifier:
        try:
            # 텍스트 간소화 모델 사용
            simplified = text_simplifier.simplify_text(sentence)
            return simplified
        except Exception as e:
            logger.warning(f"텍스트 간소화 실패: {e}, 폴백 사용")

    # 폴백: 간단한 키워드 기반 설명
    return generate_simple_explanation(sentence)

def generate_simple_explanation(sentence: str) -> str:
    """간단한 키워드 기반 설명 생성"""

    explanations = {
        '중도해지': '중도해지란 정기예금 만기일 전에 예금을 찾는 것을 말합니다. 이 경우 약속했던 높은 이자율 대신 낮은 이자율이 적용됩니다.',
        '우대금리': '우대금리란 은행에서 정한 특정 조건을 충족할 경우 기본 금리에 추가로 제공하는 이자율입니다.',
        '예금자보호': '예금자보호란 예금보험공사에서 은행이 파산하더라도 예금자 1인당 원금과 이자를 합쳐 최대 5천만원까지 보장해주는 제도입니다.',
        '복리': '복리란 원금에서 발생한 이자를 원금에 합쳐서 다시 이자를 계산하는 방식으로, 시간이 지날수록 이자가 기하급수적으로 증가합니다.',
        '변동금리': '변동금리란 시장 금리나 기준금리 변동에 따라 적용 금리가 주기적으로 조정되는 금리 방식입니다.'
    }

    # 문장에서 키워드 찾기
    for keyword, explanation in explanations.items():
        if keyword in sentence:
            return explanation

    # 키워드가 없으면 일반적인 설명
    return f"이 조건은 예금 상품의 중요한 내용입니다. 자세한 사항은 상담을 통해 확인하실 수 있습니다."

async def fallback_analysis(request: TextAnalysisRequest) -> TextAnalysisResponse:
    """하이브리드 분석기가 없을 때 폴백"""

    # 간단한 키워드 기반 분석
    financial_terms = {
        '중도해지': '만기 전 예금 인출',
        '우대금리': '조건 충족시 추가 이자',
        '예금자보호': '5천만원까지 보장',
        '복리': '이자에 이자가 붙는 방식',
        '변동금리': '시장에 따라 금리 변동'
    }

    found_terms = []
    for term, definition in financial_terms.items():
        if term in request.section_text:
            found_terms.append({
                "term": term,
                "definition": definition
            })

    # 간단한 문장 분석 (임시)
    sentences = request.section_text.split('.')
    difficult_sentences = []

    for i, sentence in enumerate(sentences[:2]):  # 최대 2개 문장
        if sentence.strip() and any(term in sentence for term in financial_terms.keys()):
            difficult_sentences.append(DifficultSentence(
                sentence=sentence.strip(),
                sentence_id=f"sentence_{i+1}",
                difficulty_score=0.7,
                simplified_explanation=generate_simple_explanation(sentence),
                original_position=i * 50
            ))

    return TextAnalysisResponse(
        difficult_terms=found_terms,
        difficult_sentences=difficult_sentences,
        overall_difficulty=0.6,
        comprehension_level="medium"
    )

@router.get("/health")
async def text_analysis_health():
    """텍스트 분석 서비스 상태 확인"""
    return {
        "status": "healthy",
        "service": "text-analysis",
        "hybrid_analyzer": "available" if HYBRID_ANALYZER_AVAILABLE else "unavailable",
        "text_simplifier": "available" if TEXT_SIMPLIFIER_AVAILABLE else "unavailable"
    }