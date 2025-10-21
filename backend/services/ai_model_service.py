"""
AI 모델 통합 인터페이스
HuggingFace 모델을 사용한 텍스트 분석 및 간소화
"""

import os
import sys
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class HuggingFaceModels:
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
            inputs = self.simplifier_tokenizer(
                text,
                return_tensors="pt",
                max_length=256,
                truncation=True,
                padding=True
            )

            with torch.no_grad():
                outputs = self.simplifier_model.generate(
                    **inputs,
                    max_length=128,
                    num_beams=5,
                    do_sample=False,
                    repetition_penalty=2.5,
                    no_repeat_ngram_size=4,
                    length_penalty=1.2,
                    early_stopping=True,
                    min_length=10
                )

            simplified_text = self.simplifier_tokenizer.decode(outputs[0], skip_special_tokens=True)
            return simplified_text.strip()

        except Exception as e:
            logger.error(f"텍스트 간소화 실패: {e}")
            return text
    
    async def convert_nl_to_sql(self, natural_language_query: str, schema_context: str = "") -> str:
        """자연어를 SQL 쿼리로 변환"""
        logger.info(f"[HF모델] convert_nl_to_sql 호출됨: {natural_language_query}")

        if not self.nl_to_sql_model or not self.nl_to_sql_tokenizer:
            logger.error(f"[HF모델] NHSQLNL 모델 없음. model:{self.nl_to_sql_model is not None}, tokenizer:{self.nl_to_sql_tokenizer is not None}")
            raise RuntimeError("NHSQLNL 모델이 로드되지 않았습니다.")
        
        try:
            import torch
            
            # 학습 시와 동일한 형식으로 입력 (스키마 + 자연어)
            if not schema_context:
                # 기본 스키마 (학습 데이터의 스키마)
                schema_context = "customers: id, name, created_at | consultations: id, customer_id, product_type, product_details, consultation_phase, start_time, end_time, status, created_at, detailed_info | reading_analysis: id, consultation_id, customer_id, section_name, section_text, difficulty_score, confusion_probability, comprehension_level, gaze_data, analysis_timestamp, created_at | consultation_summaries: id, consultation_id, overall_difficulty, confused_sections, total_sections, comprehension_high, comprehension_medium, comprehension_low, recommendations, created_at"
            
            # 스키마 정의 (실제 사용 컬럼 포함)
            full_schema = "consultations: id, customer_id, product_type, product_details, start_time, end_time, status | customers: id, name"

            # Few-shot 예제 (실제 사용 패턴에 맞춤)
            examples = [
                # 예제 1: ELS 상품 검색
                (
                    f"[SCHEMA: {full_schema}] [UTTERANCE: 최근 ELS 상품 보여줘]",
                    "SELECT c.*, cu.name as customer_name FROM consultations c JOIN customers cu ON c.customer_id = cu.id WHERE c.product_details->>'name' LIKE '%ELS%' ORDER BY c.start_time DESC LIMIT 20;"
                ),
                # 예제 2: 적금 상담 내역
                (
                    f"[SCHEMA: {full_schema}] [UTTERANCE: 적금 상담 내역]",
                    "SELECT c.*, cu.name as customer_name FROM consultations c JOIN customers cu ON c.customer_id = cu.id WHERE c.product_type = '적금' ORDER BY c.start_time DESC LIMIT 20;"
                ),
                # 예제 3: 완료된 상담
                (
                    f"[SCHEMA: {full_schema}] [UTTERANCE: 완료된 상담 보여줘]",
                    "SELECT c.*, cu.name as customer_name FROM consultations c JOIN customers cu ON c.customer_id = cu.id WHERE c.status = 'completed' ORDER BY c.start_time DESC LIMIT 20;"
                )
            ]

            # Few-shot 예제 포맷팅
            few_shot_text = "\n\n".join([f"{inp}\n{out}" for inp, out in examples])

            # 현재 쿼리
            current_input = f"[SCHEMA: {full_schema}] [UTTERANCE: {natural_language_query}]"

            # 예제와 현재 입력을 합쳐서 전달
            input_text = f"{few_shot_text}\n\n{current_input}"
            
            # 토큰화
            inputs = self.nl_to_sql_tokenizer(
                input_text,
                return_tensors="pt",
                max_length=512,  # Few-shot 예제를 위해 충분한 길이
                truncation=True,
                padding=True
            )

            # SQL 생성 - Few-shot 예제가 포함된 상태로 생성
            with torch.no_grad():
                outputs = self.nl_to_sql_model.generate(
                    **inputs,
                    max_length=150,  # SQL 길이 충분히
                    num_beams=5,  # 탐색 폭 넓게
                    do_sample=False,
                    repetition_penalty=1.5,  # 반복 더 억제
                    no_repeat_ngram_size=3,
                    early_stopping=True,
                    length_penalty=1.0  # 길이 페널티 추가
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
                logger.error(f"[AI모델] 유효하지 않은 SQL 생성됨: '{sql_query}'")
                raise ValueError(f"AI 모델이 유효하지 않은 SQL을 생성했습니다: {sql_query}")
            
            # DESC 같은 잘못된 SELECT 처리
            if "SELECT DESC" in sql_query.upper():
                sql_query = sql_query.replace("SELECT DESC", "SELECT *")
            
            logger.info(f"[AI모델] 생성된 SQL (정제 전): {sql_query}")

            return sql_query

        except Exception as e:
            logger.error(f"NL to SQL 변환 실패: {e}")
            raise  # 예외를 상위로 전달

class AIModelManager:
    """AI 모델 관리자"""

    def __init__(self):
        self.hf_models: Optional[HuggingFaceModels] = None
        self._initialize_model()

    def _initialize_model(self):
        """HuggingFace 모델 초기화"""
        try:
            self.hf_models = HuggingFaceModels()
            logger.info("HuggingFace 모델 초기화 성공")
        except Exception as e:
            logger.error(f"HuggingFace 모델 초기화 실패: {e}")
            raise


ai_model_manager = AIModelManager()