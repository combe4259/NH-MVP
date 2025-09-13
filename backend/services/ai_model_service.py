"""
AI 모델 통합 인터페이스
- 다양한 AI 모델을 쉽게 교체할 수 있는 추상화 레이어
- PyTorch, TensorFlow, OpenAI API 등 모든 모델 지원
"""

import os
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class AIModelInterface(ABC):
    """AI 모델 인터페이스 - 모든 AI 모델이 구현해야 하는 기본 구조"""
    
    @abstractmethod
    async def analyze_difficulty(self, text: str) -> float:
        """텍스트 난이도 분석 (0.0 ~ 1.0)"""
        pass
    
    @abstractmethod
    async def generate_explanation(self, text: str, difficulty_score: float) -> str:
        """AI 설명 생성"""
        pass
    
    @abstractmethod
    async def identify_confused_sections(self, text: str) -> List[Dict]:
        """혼란스러운 섹션 식별"""
        pass

class PyTorchModel(AIModelInterface):
    """PyTorch 모델 래퍼"""
    
    def __init__(self, model_path: str):
        self.model_path = model_path
        self.model = None
        self.is_loaded = False
        
    def _load_model(self):
        """모델 로딩 (지연 로딩)"""
        if self.is_loaded:
            return
        
        try:
            import torch
            self.model = torch.load(self.model_path, map_location='cpu')
            self.model.eval()
            self.is_loaded = True
            logger.info(f"PyTorch 모델 로드 성공: {self.model_path}")
        except Exception as e:
            logger.error(f"PyTorch 모델 로드 실패: {e}")
            self.model = None
    
    async def analyze_difficulty(self, text: str) -> float:
        self._load_model()
        if not self.model:
            return 0.5  # fallback
        
        # TODO: 실제 모델 추론 구현
        # tokenized = self.tokenizer(text)
        # with torch.no_grad():
        #     output = self.model(tokenized)
        #     return output['difficulty'].item()
        
        return 0.5  # 임시 반환

    async def generate_explanation(self, text: str, difficulty_score: float) -> str:
        # TODO: 실제 설명 생성 구현
        return f"AI 분석 결과: 난이도 {difficulty_score:.1f} 텍스트입니다."

    async def identify_confused_sections(self, text: str) -> List[Dict]:
        # TODO: 실제 섹션 분석 구현
        return []

class OpenAIModel(AIModelInterface):
    """OpenAI API 래퍼"""
    
    def __init__(self, api_key: str, model_name: str = "gpt-4"):
        self.api_key = api_key
        self.model_name = model_name
        
    async def analyze_difficulty(self, text: str) -> float:
        try:
            import openai
            openai.api_key = self.api_key
            
            response = openai.ChatCompletion.create(
                model=self.model_name,
                messages=[{
                    "role": "user",
                    "content": f"다음 금융 텍스트의 난이도를 0.0~1.0으로 분석해주세요: {text}"
                }]
            )
            
            # TODO: 응답 파싱해서 숫자 추출
            return 0.5
            
        except Exception as e:
            logger.error(f"OpenAI API 호출 실패: {e}")
            return 0.5

    async def generate_explanation(self, text: str, difficulty_score: float) -> str:
        # TODO: OpenAI로 설명 생성
        return f"OpenAI 분석: {text[:50]}... (난이도: {difficulty_score})"

    async def identify_confused_sections(self, text: str) -> List[Dict]:
        return []

class MockAIModel(AIModelInterface):
    """개발용 Mock 모델 - AI 모델 개발 전까지 사용"""
    
    async def analyze_difficulty(self, text: str) -> float:
        # 키워드 기반 간단 분석
        difficult_terms = ['중도해지', '우대금리', '복리', '예금자보호']
        term_count = sum(1 for term in difficult_terms if term in text)
        return min(term_count * 0.2 + len(text) / 500, 0.9)

    async def generate_explanation(self, text: str, difficulty_score: float) -> str:
        if difficulty_score > 0.7:
            return "이 부분은 복잡한 금융 용어가 포함되어 있습니다. 직원에게 설명을 요청하세요."
        elif difficulty_score > 0.4:
            return "일반적인 수준의 내용입니다. 천천히 읽어보세요."
        else:
            return "이해하기 쉬운 내용입니다."

    async def identify_confused_sections(self, text: str) -> List[Dict]:
        sentences = text.split('.')
        confused = []
        for i, sentence in enumerate(sentences):
            if any(term in sentence for term in ['중도해지', '우대금리']):
                confused.append({
                    "sentence_id": i,
                    "text": sentence.strip(),
                    "reason": "전문용어 포함"
                })
        return confused

class AIModelManager:
    """AI 모델 관리자 - 설정에 따라 적절한 모델 선택"""
    
    def __init__(self):
        self.current_model: Optional[AIModelInterface] = None
        self._initialize_model()
    
    def _initialize_model(self):
        """환경변수 기반으로 모델 초기화"""
        
        model_type = os.getenv("AI_MODEL_TYPE", "mock").lower()
        
        if model_type == "pytorch" and os.getenv("AI_MODEL_PATH"):
            self.current_model = PyTorchModel(os.getenv("AI_MODEL_PATH"))
            logger.info("PyTorch 모델 초기화됨")
            
        elif model_type == "openai" and os.getenv("OPENAI_API_KEY"):
            self.current_model = OpenAIModel(os.getenv("OPENAI_API_KEY"))
            logger.info("OpenAI 모델 초기화됨")
            
        else:
            self.current_model = MockAIModel()
            logger.info("Mock 모델 초기화됨 (개발 모드)")
    
    async def analyze_text(self, text: str) -> Dict:
        """통합 텍스트 분석 인터페이스"""
        if not self.current_model:
            raise RuntimeError("AI 모델이 초기화되지 않았습니다")
        
        try:
            difficulty = await self.current_model.analyze_difficulty(text)
            explanation = await self.current_model.generate_explanation(text, difficulty)
            confused_sections = await self.current_model.identify_confused_sections(text)
            
            return {
                "difficulty_score": difficulty,
                "ai_explanation": explanation,
                "confused_sections": confused_sections,
                "model_type": type(self.current_model).__name__,
                "analyzed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"AI 모델 분석 실패: {e}")
            return {
                "difficulty_score": 0.5,
                "ai_explanation": "분석 중 오류가 발생했습니다.",
                "confused_sections": [],
                "error": str(e)
            }
    
    def switch_model(self, model_type: str, **kwargs):
        """런타임에 모델 변경"""
        try:
            if model_type == "pytorch":
                self.current_model = PyTorchModel(kwargs.get("model_path"))
            elif model_type == "openai":
                self.current_model = OpenAIModel(kwargs.get("api_key"))
            elif model_type == "mock":
                self.current_model = MockAIModel()
            
            logger.info(f"모델이 {model_type}으로 변경되었습니다")
            
        except Exception as e:
            logger.error(f"모델 변경 실패: {e}")

# 전역 AI 모델 매니저
ai_model_manager = AIModelManager()