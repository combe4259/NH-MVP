"""
Kr-FinBert 인코더 + KoGPT2 디코더를 이용한 금융 텍스트 간소화 시스템
금융 문서를 쉬운 한국어로 변환
"""

import torch
import torch.nn as nn
from transformers import (
    AutoTokenizer, 
    AutoModel,
    AutoModelForCausalLM,
    EncoderDecoderModel,
    Seq2SeqTrainingArguments,
    Seq2SeqTrainer,
    DataCollatorForSeq2Seq
)
from datasets import Dataset
import numpy as np
from typing import List, Dict, Tuple
import json

# GPU 설정
device = torch.device("cuda" if torch.cuda.is_available() else 
                     "mps" if torch.backends.mps.is_available() else "cpu")


class FinancialTextSimplifier:
    """KR-FinBert 인코더 + KoGPT2 디코더 기반 텍스트 간소화"""
    
    def __init__(self, use_dropout: bool = True):
        """
        금융 텍스트 간소화 모델 초기화
        Args:
            use_dropout: 드롭아웃 사용 여부
        """
        
        # 인코더: KR-FinBert (금융 특화)
        self.encoder_name = "snunlp/KR-FinBert-SC"
        
        # 디코더: KoGPT2 (한국어 텍스트 생성)
        self.decoder_name = "skt/kogpt2-base-v2"
        self.use_dropout = use_dropout
        
        # 토크나이저 로드
        self.encoder_tokenizer = AutoTokenizer.from_pretrained(self.encoder_name)
        
        self.decoder_tokenizer = AutoTokenizer.from_pretrained(self.decoder_name)
        
        # 특수 토큰 추가
        if self.decoder_tokenizer.pad_token is None:
            self.decoder_tokenizer.pad_token = self.decoder_tokenizer.eos_token
        
        # EncoderDecoder 모델 생성
        self.model = None
        self.create_encoder_decoder_model()
        
    def create_encoder_decoder_model(self):
        """KR-FinBert + KoGPT2 EncoderDecoder 모델 생성"""
        
        # EncoderDecoderModel 생성
        self.model = EncoderDecoderModel.from_encoder_decoder_pretrained(
            self.encoder_name,
            self.decoder_name
        )
        
        # 디코더 토크나이저 vocabulary 크기 맞추기
        self.model.decoder.resize_token_embeddings(len(self.decoder_tokenizer))
        
        # 설정
        self.model.config.decoder_start_token_id = self.decoder_tokenizer.bos_token_id
        self.model.config.pad_token_id = self.decoder_tokenizer.pad_token_id
        self.model.config.eos_token_id = self.decoder_tokenizer.eos_token_id
        self.model.config.vocab_size = self.model.config.decoder.vocab_size
        
        # Dropout 추가 (정규화)
        if self.use_dropout:
            self.model.encoder.embeddings.dropout = nn.Dropout(0.2)
            self.model.decoder.transformer.drop = nn.Dropout(0.2)
        
        # 디바이스로 이동
        self.model = self.model.to(device)
        
    
    def prepare_training_data(self, data_path: str = None) -> Dataset:
        """학습 데이터 준비"""
        
        # 파일에서 데이터 로드
        if data_path is not None:
            with open(data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 데이터 구조 확인 및 파싱
            if isinstance(data, dict):
                # {"data": [...]} 형식
                if 'data' in data:
                    examples = data['data']
                # {"sentences": [...]} 형식
                elif 'sentences' in data:
                    examples = data['sentences']
                else:
                    examples = list(data.values())[0] if data else []
            elif isinstance(data, list):
                # 리스트 형식
                examples = data
            else:
                examples = []
            
            
        # 예시 데이터 (data_path가 None인 경우)
        else:
            raise ValueError("Training data file is required")
        
        if isinstance(examples, list) and len(examples) > 0:
            first_ex = examples[0]
            if 'complex' in first_ex and 'simple' in first_ex:
                dataset = Dataset.from_dict({
                    "input_text": [ex["complex"] for ex in examples],
                    "target_text": [ex["simple"] for ex in examples]
                })
            else:
                dataset = Dataset.from_dict({"input_text": [], "target_text": []})
        else:
            dataset = Dataset.from_dict({"input_text": [], "target_text": []})
        
        return dataset
    
    def preprocess_function(self, examples):
        """데이터 전처리 함수"""
        
        # 인코더 입력 토큰화
        model_inputs = self.encoder_tokenizer(
            examples["input_text"],
            max_length=128,
            padding="max_length",
            truncation=True,
            return_tensors="pt"
        )
        
        # 디코더 레이블 토큰화
        labels = self.decoder_tokenizer(
            examples["target_text"],
            max_length=128,
            padding="max_length",
            truncation=True,
            return_tensors="pt"
        )
        
        # -100은 loss 계산에서 무시됨
        labels["input_ids"][labels["input_ids"] == self.decoder_tokenizer.pad_token_id] = -100
        
        model_inputs["labels"] = labels["input_ids"]
        return model_inputs
    
    def train(self, train_dataset: Dataset = None, epochs: int = 3):
        """모델 학습"""
        
        if train_dataset is None:
            train_dataset = self.prepare_training_data()
        
        # 데이터 전처리
        train_dataset = train_dataset.map(
            self.preprocess_function,
            batched=True,
            remove_columns=train_dataset.column_names
        )
        
        # 학습 설정 - 개선된 하이퍼파라미터
        training_args = Seq2SeqTrainingArguments(
            output_dir="./financial_simplifier_model",
            per_device_train_batch_size=4,
            per_device_eval_batch_size=4,
            gradient_accumulation_steps=2,  # 실질적 배치 크기 증가
            num_train_epochs=epochs,
            warmup_steps=200,  # warmup 증가
            learning_rate=3e-5,  # 학습률 조정
            weight_decay=0.01,  # weight decay 추가
            logging_steps=10,
            save_steps=500,
            eval_strategy="no",
            save_strategy="steps",
            predict_with_generate=True,
            fp16=torch.cuda.is_available(),
            push_to_hub=False,
            label_smoothing_factor=0.1,  # 레이블 스무딩 추가
        )
        
        # 데이터 콜레이터
        data_collator = DataCollatorForSeq2Seq(
            tokenizer=self.encoder_tokenizer,
            model=self.model,
            padding=True,
            max_length=128
        )
        
        # 커스텀 compute_metrics 함수 추가 (옵션)
        def compute_metrics(eval_preds):
            preds, labels = eval_preds
            # 디코딩된 텍스트로 BLEU 스코어 계산 가능
            return {"perplexity": np.exp(np.mean(preds))}
        
        # 트레이너 생성
        trainer = Seq2SeqTrainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            data_collator=data_collator,
        )
        
        # 학습 실행
        trainer.train()
        
        
        # 모델 저장
        self.save_model()
    
    def save_model(self, path: str = "./financial_simplifier_model"):
        """모델 저장"""
        self.model.save_pretrained(path)
        self.encoder_tokenizer.save_pretrained(f"{path}/encoder_tokenizer")
        self.decoder_tokenizer.save_pretrained(f"{path}/decoder_tokenizer")
        
        # Google Drive에 복사 (Colab용)
        try:
            import shutil
            import os
            from google.colab import drive
            
            # Drive 마운트 확인 (이미 마운트되어 있을 수 있음)
            if not os.path.exists('/content/drive'):
                drive.mount('/content/drive', force_remount=True)
            
            if os.path.exists('/content/drive/MyDrive'):
                drive_path = '/content/drive/MyDrive/financial_simplifier_model'
                shutil.copytree(path, drive_path, dirs_exist_ok=True)
        except Exception as e:
            pass
    
    def simplify_text(self, text: str, max_length: int = 128) -> str:
        """복잡한 금융 텍스트를 쉬운 말로 변환"""
        
        # 인코더 입력 준비
        inputs = self.encoder_tokenizer(
            text,
            return_tensors="pt",
            max_length=max_length,
            padding="max_length",
            truncation=True
        ).to(device)
        
        # 생성 - 개선된 파라미터
        with torch.no_grad():
            generated = self.model.generate(
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                max_length=max_length,
                min_length=10,  # 최소 길이 설정
                num_beams=6,  # 빔 서치 크기 증가
                repetition_penalty=1.2,  # 반복 페널티 추가
                length_penalty=0.8,  # 길이 페널티 조정
                early_stopping=True,
                do_sample=True,
                top_k=50,  # top-k 샘플링
                top_p=0.95,  # nucleus 샘플링
                temperature=0.7  # 낮은 temperature로 더 일관된 출력
            )
        
        # 디코딩
        simplified_text = self.decoder_tokenizer.decode(
            generated[0],
            skip_special_tokens=True
        )
        
        return simplified_text


if __name__ == "__main__":
    simplifier = FinancialTextSimplifier()
    import os
    
    try:
        from google.colab import drive
        if not os.path.exists('/content/drive'):
            drive.mount('/content/drive', force_remount=True)
        data_path = "/content/drive/MyDrive/financial_training_simplified.json"
    except ImportError:
        data_path = "/Users/inter4259/Downloads/financial_training_simplified.json"
    
    if os.path.exists(data_path):
        dataset = simplifier.prepare_training_data(data_path)
        simplifier.train(dataset, epochs=10)
        
        test_text = "주가수익비율(PER)은 주가를 주당순이익으로 나눈 지표입니다."
        result = simplifier.simplify_text(test_text)
        print(f"\n원문: {test_text}")
        print(f"변환: {result}")
    else:
        print(f"File not found: {data_path}")
