"""
AI 모델 통합 인터페이스
- 다양한 AI 모델을 쉽게 교체할 수 있는 추상화 레이어
- PyTorch, TensorFlow, OpenAI API 등 모든 모델 지원
"""

import os
import sys
import numpy as np
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

class HuggingFaceModels(AIModelInterface):
    """HuggingFace 모델 통합 래퍼 (난이도 분석 + 얼굴 혼란도)"""
    
    def __init__(self):
        self.difficulty_model = None
        self.difficulty_tokenizer = None
        self.simplifier_model = None
        self.simplifier_tokenizer = None
        self.confusion_model = None
        self.confusion_tracker = None
        self.nl_to_sql_model = None
        self.nl_to_sql_tokenizer = None
        self._load_models()
        
    def _load_models(self):
        """모델 초기화"""
        try:
            # 텍스트 난이도 분석 모델
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            self.difficulty_tokenizer = AutoTokenizer.from_pretrained("combe4259/difficulty_klue")
            self.difficulty_model = AutoModelForSequenceClassification.from_pretrained("combe4259/difficulty_klue")
            self.difficulty_model.eval()
            logger.info("KLUE-BERT 난이도 분석 모델 로드 완료")
            
            # 텍스트 간소화 모델
            from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
            self.simplifier_tokenizer = AutoTokenizer.from_pretrained("combe4259/fin_simplifier")
            self.simplifier_model = AutoModelForSeq2SeqLM.from_pretrained("combe4259/fin_simplifier")
            self.simplifier_model.eval()
            logger.info("금융 텍스트 간소화 모델 로드 완료")
            
            # 얼굴 혼란도 감지 모델
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'face'))
            from realtime_confusion_tracker_hf import RealtimeConfusionTrackerHF
            self.confusion_tracker = RealtimeConfusionTrackerHF(
                repo_id='combe4259/face-comprehension',
                prediction_interval=1.0
            )
            logger.info("얼굴 혼란도 감지 모델 로드 완료")
            
            # NHSQLNL 모델 (자연어 -> SQL 변환)
            try:
                from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
                logger.info("NHSQLNL 모델 로딩 시작...")
                self.nl_to_sql_tokenizer = AutoTokenizer.from_pretrained("combe4259/NHSQLNL")
                self.nl_to_sql_model = AutoModelForSeq2SeqLM.from_pretrained("combe4259/NHSQLNL")
                self.nl_to_sql_model.eval()
                logger.info("NHSQLNL (자연어->SQL) 모델 로드 완료")
            except Exception as e:
                logger.error(f"NHSQLNL 모델 로드 실패: {e}")
                self.nl_to_sql_model = None
                self.nl_to_sql_tokenizer = None
            
        except Exception as e:
            logger.error(f"HuggingFace 모델 로드 실패: {e}")
    
    async def analyze_difficulty(self, text: str) -> float:
        """텍스트 난이도 분석 (0.0 ~ 1.0)"""
        if not self.difficulty_model:
            return 0.5
        
        try:
            import torch
            inputs = self.difficulty_tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True
            )
            
            with torch.no_grad():
                outputs = self.difficulty_model(**inputs)
                prediction = torch.argmax(outputs.logits, dim=-1).item()
                difficulty = (prediction + 1) / 10.0  # 1-10을 0.1-1.0으로 정규화
            
            return difficulty
            
        except Exception as e:
            logger.error(f"난이도 분석 실패: {e}")
            return 0.5
    
    async def analyze_confusion_from_face(self, frame: np.ndarray) -> Dict:
        """얼굴 영상에서 혼란도 분석"""
        if not self.confusion_tracker:
            return {"confused": False, "probability": 0.0}
        
        try:
            # process_frame은 프레임을 반환하므로, 내부 상태를 직접 확인
            processed_frame = self.confusion_tracker.process_frame(frame)
            
            # 현재 상태 가져오기
            confusion_state = self.confusion_tracker.current_confusion_state
            confusion_prob = self.confusion_tracker.confusion_probability
            
            return {
                "confused": confusion_state == "Confused",
                "probability": float(confusion_prob),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"얼굴 혼란도 분석 실패: {e}")
            return {"confused": False, "probability": 0.0}
    
    async def simplify_text(self, text: str) -> str:
        """금융 텍스트를 쉬운 말로 변환"""
        if not self.simplifier_model or not self.simplifier_tokenizer:
            return text
        
        try:
            import torch
            # 입력 텍스트 토큰화
            inputs = self.simplifier_tokenizer(
                text,
                return_tensors="pt",
                max_length=512,
                truncation=True,
                padding=True
            )
            
            # 간소화된 텍스트 생성
            with torch.no_grad():
                outputs = self.simplifier_model.generate(
                    **inputs,
                    max_length=256,
                    num_beams=5,
                    temperature=0.8,
                    do_sample=True,
                    top_p=0.95
                )
            
            # 디코딩
            simplified_text = self.simplifier_tokenizer.decode(outputs[0], skip_special_tokens=True)
            return simplified_text
            
        except Exception as e:
            logger.error(f"텍스트 간소화 실패: {e}")
            return text
    
    async def generate_explanation(self, text: str, difficulty_score: float) -> str:
        """AI 설명 생성 - 간소화 모델 활용"""
        try:
            # 난이도에 따라 간소화 수행
            if difficulty_score > 0.6:
                simplified = await self.simplify_text(text)
                return f"**쉽게 설명해드릴게요:**\n{simplified}"
            elif difficulty_score > 0.4:
                return f"중간 정도 난이도의 텍스트입니다. 천천히 읽어보세요."
            else:
                return f"이해하기 쉬운 내용입니다."
        except:
            # 폴백
            if difficulty_score > 0.7:
                return f"이 부분은 어려운 금융 용어가 포함되어 있습니다. 쉽게 설명해드릴게요."
            elif difficulty_score > 0.4:
                return f"중간 정도 난이도의 텍스트입니다. 천천히 읽어보세요."
            else:
                return f"이해하기 쉬운 내용입니다."
    
    async def identify_confused_sections(self, text: str) -> List[Dict]:
        """혼란스러운 섹션 식별"""
        sentences = text.split('.')
        confused_sections = []
        
        for i, sentence in enumerate(sentences):
            if sentence.strip():
                difficulty = await self.analyze_difficulty(sentence)
                if difficulty > 0.6:
                    confused_sections.append({
                        "sentence_index": i,
                        "text": sentence.strip(),
                        "difficulty": difficulty
                    })
        
        return confused_sections
    
    async def convert_nl_to_sql(self, natural_language_query: str, schema_context: str = "") -> str:
        """자연어를 SQL 쿼리로 변환"""
        logger.info(f"[HF모델] convert_nl_to_sql 호출됨: {natural_language_query}")
        
        if not self.nl_to_sql_model or not self.nl_to_sql_tokenizer:
            logger.warning(f"[HF모델] NHSQLNL 모델 없음. model:{self.nl_to_sql_model is not None}, tokenizer:{self.nl_to_sql_tokenizer is not None}")
            return self._generate_fallback_sql(natural_language_query)
        
        try:
            import torch
            
            # 학습 시와 동일한 형식으로 입력 (스키마 + 자연어)
            if not schema_context:
                # 기본 스키마 (학습 데이터의 스키마)
                schema_context = "customers: id, name, created_at | consultations: id, customer_id, product_type, product_details, consultation_phase, start_time, end_time, status, created_at, detailed_info | reading_analysis: id, consultation_id, customer_id, section_name, section_text, difficulty_score, confusion_probability, comprehension_level, gaze_data, analysis_timestamp, created_at | consultation_summaries: id, consultation_id, overall_difficulty, confused_sections, total_sections, comprehension_high, comprehension_medium, comprehension_low, recommendations, created_at"
            
            # 원래 학습 형식으로 되돌리기
            simple_schema = "consultations: id, customer_id, product_type, start_time, end_time, status"
            
            # Few-shot 예제 하나 추가 (학습 데이터 형식 그대로)
            example_input = "[SCHEMA: consultations: id, customer_id, product_type, start_time, end_time, status] [UTTERANCE: 내 예금 상담 내역]"
            example_output = "SELECT * FROM consultations WHERE customer_id = :current_user_id AND product_type = '정기예금' ORDER BY start_time DESC;"
            
            # 현재 쿼리
            current_input = f"[SCHEMA: {simple_schema}] [UTTERANCE: {natural_language_query}]"
            
            # 예제와 현재 입력을 합쳐서 전달
            input_text = f"{example_input}\n{example_output}\n\n{current_input}"
            
            # 토큰화
            inputs = self.nl_to_sql_tokenizer(
                input_text,
                return_tensors="pt",
                max_length=256,  # 더 짧게
                truncation=True,
                padding=True
            )
            
            # SQL 생성 - Few-shot 예제가 포함된 상태로 생성
            with torch.no_grad():
                outputs = self.nl_to_sql_model.generate(
                    **inputs,
                    max_length=100,
                    num_beams=3,
                    do_sample=False,
                    repetition_penalty=1.3,
                    no_repeat_ngram_size=3,
                    early_stopping=True
                )
            
            # 디코딩
            sql_query = self.nl_to_sql_tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            logger.info(f"[AI모델] 입력: {input_text}")
            logger.info(f"[AI모델] 출력 (원본): {sql_query}")
            logger.info(f"[AI모델] 출력 길이: {len(sql_query)}")
            
            # :current_user_id를 제거 (모든 사용자 데이터 조회)
            if ":current_user_id" in sql_query:
                # customer_id 조건만 제거 (다른 WHERE 조건은 유지)
                sql_query = sql_query.replace("customer_id = :current_user_id AND ", "")
                sql_query = sql_query.replace(" AND customer_id = :current_user_id", "")
                sql_query = sql_query.replace("WHERE customer_id = :current_user_id", "WHERE TRUE")
                sql_query = sql_query.replace("customer_id = :current_user_id", "TRUE")
            
            # 모델이 빈 문자열이나 이상한 값을 반환한 경우 처리
            if len(sql_query) < 10 or "SELECT" not in sql_query.upper():
                logger.warning(f"[AI모델] 유효하지 않은 SQL: '{sql_query}', 폴백 사용")
                return self._generate_fallback_sql(natural_language_query)
            
            # DESC 같은 잘못된 SELECT 처리
            if "SELECT DESC" in sql_query.upper():
                sql_query = sql_query.replace("SELECT DESC", "SELECT *")
            
            # 자연어에서 제품 타입 추출하여 WHERE 절 추가 (SQL 정제 전에 처리)
            if "적금" in natural_language_query and "product_type = '적금'" not in sql_query:
                if "WHERE" not in sql_query.upper():
                    sql_query = sql_query.replace("FROM consultations", "FROM consultations WHERE product_type = '적금'")
                else:
                    sql_query = sql_query.replace("WHERE TRUE", "WHERE product_type = '적금'")
                    if "WHERE TRUE" not in sql_query and "product_type" not in sql_query:
                        sql_query = sql_query + " AND product_type = '적금'"
            
            # 예금도 동일하게 처리
            elif "예금" in natural_language_query and "product_type" not in sql_query:
                if "WHERE" not in sql_query.upper():
                    sql_query = sql_query.replace("FROM consultations", "FROM consultations WHERE product_type = '정기예금'")
                else:
                    sql_query = sql_query.replace("WHERE TRUE", "WHERE product_type = '정기예금'")
                    if "WHERE TRUE" not in sql_query:
                        sql_query = sql_query + " AND product_type = '정기예금'"
            
            # 대출도 처리
            elif "대출" in natural_language_query and "product_type" not in sql_query:
                if "WHERE" not in sql_query.upper():
                    sql_query = sql_query.replace("FROM consultations", "FROM consultations WHERE product_type = '대출'")
                else:
                    sql_query = sql_query.replace("WHERE TRUE", "WHERE product_type = '대출'")
                    if "WHERE TRUE" not in sql_query:
                        sql_query = sql_query + " AND product_type = '대출'"
            
            # SQL 정제 (JOIN 추가 등)
            sql_query = self._refine_sql(sql_query)
            
            return sql_query
            
        except Exception as e:
            logger.error(f"NL to SQL 변환 실패: {e}")
            return self._generate_fallback_sql(natural_language_query)
    
    def _refine_sql(self, sql_query: str) -> str:
        """생성된 SQL 정제 - 고객명 표시를 위해 JOIN 자동 추가"""
        sql_query = sql_query.strip()
        
        # SELECT가 없으면 기본 쿼리 생성
        if not sql_query.upper().startswith("SELECT"):
            logger.warning(f"잘못된 SQL 생성됨: {sql_query}")
            return self._generate_fallback_sql("")
        
        # consultations 테이블 조회 시 고객명도 필요하므로 customers 테이블 JOIN
        if "FROM consultations" in sql_query and "JOIN customers" not in sql_query:
            # SELECT * 를 구체적인 컬럼으로 변경하고 고객명 추가
            if "SELECT *" in sql_query:
                sql_query = sql_query.replace(
                    "SELECT *",
                    "SELECT c.*, cu.name as customer_name"
                )
            
            # FROM 절에 JOIN 추가
            sql_query = sql_query.replace(
                "FROM consultations",
                "FROM consultations c JOIN customers cu ON c.customer_id = cu.id"
            )
            
            # WHERE 절의 customer_id도 별칭 적용
            sql_query = sql_query.replace("WHERE customer_id", "WHERE c.customer_id")
            sql_query = sql_query.replace("AND customer_id", "AND c.customer_id")
        
        return sql_query
    
    def _generate_fallback_sql(self, query: str) -> str:
        """폴백 SQL 생성"""
        logger.info(f"[폴백SQL] 키워드 기반 SQL 생성 중: {query}")
        
        base_sql = """
        SELECT c.id, c.customer_id, cu.name as customer_name, 
               c.product_type, c.status, c.start_time, c.end_time
        FROM consultations c
        JOIN customers cu ON c.customer_id = cu.id
        WHERE 1=1
        """
        
        query_lower = query.lower()
        conditions = []
        
        # 날짜 처리
        if "최근" in query_lower:
            conditions.append("c.start_time >= CURRENT_DATE - INTERVAL '7 days'")
        elif "오늘" in query_lower:
            conditions.append("DATE(c.start_time) = CURRENT_DATE")
        elif "어제" in query_lower:
            conditions.append("DATE(c.start_time) = CURRENT_DATE - INTERVAL '1 day'")
        elif "지난달" in query_lower:
            conditions.append("DATE_TRUNC('month', c.start_time) = DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')")
        
        # 상품 타입 처리
        if "적금" in query_lower:
            conditions.append("c.product_type = '적금'")
        elif "정기예금" in query_lower or "예금" in query_lower:
            conditions.append("c.product_type = '정기예금'")
        elif "펀드" in query_lower:
            conditions.append("c.product_type = '펀드'")
        
        # 상태 처리
        if "완료" in query_lower:
            conditions.append("c.status = 'completed'")
        elif "진행" in query_lower:
            conditions.append("c.status = 'active'")
        
        if conditions:
            base_sql += " AND " + " AND ".join(conditions)
        
        base_sql += " ORDER BY c.start_time DESC LIMIT 20"
        return base_sql

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
        self.hf_models: Optional[HuggingFaceModels] = None
        self._initialize_model()
    
    def _initialize_model(self):
        """환경변수 기반으로 모델 초기화"""
        
        #model_type = os.getenv("AI_MODEL_TYPE", "mock").lower()  # 임시로 mock 사용 huggingface
        model_type = os.getenv("AI_MODEL_TYPE", "huggingface").lower()
        
        if model_type == "huggingface":
            # HuggingFace 모델 사용 (기본값)
            try:
                self.hf_models = HuggingFaceModels()
                self.current_model = self.hf_models
                logger.info("HuggingFace 모델 (KLUE-BERT + Face-Comprehension) 초기화 성공")
            except Exception as e:
                logger.error(f"HuggingFace 모델 초기화 실패: {e}")
                self.current_model = MockAIModel()
                logger.info("Fallback to Mock 모델")
                
        elif model_type == "pytorch" and os.getenv("AI_MODEL_PATH"):
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