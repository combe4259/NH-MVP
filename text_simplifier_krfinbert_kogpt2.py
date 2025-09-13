"""
KLUE/BERT 인코더 + KoGPT2 디코더를 이용한 금융 텍스트 간소화 시스템
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
print(f"Using device: {device}")


class FinancialTextSimplifier:
    """KR-FinBert 인코더 + KoGPT2 디코더 기반 텍스트 간소화"""
    
    def __init__(self, use_dropout: bool = True):
        """
        금융 텍스트 간소화 모델 초기화
        Args:
            use_dropout: 드롭아웃 사용 여부
        """
        print("🔧 Initializing Financial Text Simplifier...")
        
        # 인코더: KR-FinBert (금융 특화)
        self.encoder_name = "snunlp/KR-FinBert-SC"
        print("📈 Using KR-FinBert (Financial domain specialized)")
        
        # 디코더: KoGPT2 (한국어 텍스트 생성)
        self.decoder_name = "skt/kogpt2-base-v2"
        self.use_dropout = use_dropout
        
        # 토크나이저 로드
        print(f"Loading encoder tokenizer: {self.encoder_name}")
        self.encoder_tokenizer = AutoTokenizer.from_pretrained(self.encoder_name)
        
        print(f"Loading decoder tokenizer: {self.decoder_name}")
        self.decoder_tokenizer = AutoTokenizer.from_pretrained(self.decoder_name)
        
        # 특수 토큰 추가
        if self.decoder_tokenizer.pad_token is None:
            self.decoder_tokenizer.pad_token = self.decoder_tokenizer.eos_token
        
        # EncoderDecoder 모델 생성
        self.model = None
        self.create_encoder_decoder_model()
        
    def create_encoder_decoder_model(self):
        """KR-FinBert + KoGPT2 EncoderDecoder 모델 생성"""
        print("🚀 Creating EncoderDecoder model...")
        
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
        
        print(f"✅ Model created successfully on {device}")
        print(f"   Encoder: {self.encoder_name}")
        print(f"   Decoder: {self.decoder_name}")
        print(f"   Encoder vocab size: {len(self.encoder_tokenizer)}")
        print(f"   Decoder vocab size: {len(self.decoder_tokenizer)}")
    
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
                print(f"⚠️ Unexpected data format: {type(data)}")
                examples = []
            
            print(f"📊 Loaded {len(examples)} examples from file")
            
        # 예시 데이터 (data_path가 None인 경우)
        else:
            examples = [
                {
                    "complex": "주가수익비율(PER)은 주가를 주당순이익으로 나눈 지표입니다.",
                    "simple": "PER은 주식 가격이 회사 이익 대비 비싼지 싼지 보는 숫자입니다."
                },
                {
                    "complex": "파생결합증권은 기초자산의 가격변동에 연계하여 수익이 결정되는 증권입니다.",
                    "simple": "파생결합증권은 다른 상품 가격에 따라 수익이 바뀌는 투자 상품입니다."
                },
                {
                    "complex": "환매조건부채권(RP)은 일정기간 후 다시 매입하는 조건으로 매도하는 채권입니다.",
                    "simple": "RP는 나중에 다시 사겠다고 약속하고 일단 파는 채권입니다."
                },
                {
                    "complex": "신용파생상품은 신용위험을 기초자산으로 하는 파생금융상품입니다.",
                    "simple": "신용파생상품은 돈을 못 갚을 위험을 사고파는 금융 상품입니다."
                },
                {
                    "complex": "유동성 리스크는 자산을 적정 가격에 현금화하지 못할 위험입니다.",
                    "simple": "유동성 리스크는 급하게 팔 때 제값을 못 받을 위험입니다."
                }
            ]
        
        # 데이터셋 생성 - Gemma simplified 파일용
        if isinstance(examples, list) and len(examples) > 0:
            # 첫 번째 예제로 키 확인
            first_ex = examples[0]
            if 'complex' in first_ex and 'simple' in first_ex:
                # financial_training_simplified.json 형식
                dataset = Dataset.from_dict({
                    "input_text": [ex["complex"] for ex in examples],
                    "target_text": [ex["simple"] for ex in examples]
                })
            else:
                print(f"⚠️ Unexpected keys in data: {first_ex.keys()}")
                dataset = Dataset.from_dict({"input_text": [], "target_text": []})
        else:
            print("⚠️ No examples found in data")
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
        print("\n🎓 Starting training...")
        
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
        
        print("✅ Training completed!")
        
        # 모델 저장
        self.save_model()
    
    def save_model(self, path: str = "./financial_simplifier_model"):
        """모델 저장"""
        print(f"💾 Saving model to {path}...")
        self.model.save_pretrained(path)
        self.encoder_tokenizer.save_pretrained(f"{path}/encoder_tokenizer")
        self.decoder_tokenizer.save_pretrained(f"{path}/decoder_tokenizer")
        print("✅ Model saved!")
        
        # Google Drive에 복사 (Colab용)
        try:
            import shutil
            import os
            from google.colab import drive
            
            # Drive 마운트 확인 (이미 마운트되어 있을 수 있음)
            if not os.path.exists('/content/drive'):
                print("🔄 Mounting Google Drive (You can choose different account)...")
                drive.mount('/content/drive', force_remount=True)
            
            if os.path.exists('/content/drive/MyDrive'):
                drive_path = '/content/drive/MyDrive/financial_simplifier_model'
                print(f"📤 Copying to Google Drive: {drive_path}")
                shutil.copytree(path, drive_path, dirs_exist_ok=True)
                print("✅ Model copied to Google Drive!")
            else:
                print("⚠️ Google Drive not mounted. Model saved locally only.")
        except Exception as e:
            print(f"⚠️ Could not save to Drive: {e}")
            print("Model saved locally at:", path)
    
    def load_model(self, path: str = "./financial_simplifier_model"):
        """모델 로드"""
        print(f"📂 Loading model from {path}...")
        self.model = EncoderDecoderModel.from_pretrained(path)
        self.encoder_tokenizer = AutoTokenizer.from_pretrained(f"{path}/encoder_tokenizer")
        self.decoder_tokenizer = AutoTokenizer.from_pretrained(f"{path}/decoder_tokenizer")
        self.model = self.model.to(device)
        print("✅ Model loaded!")
    
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
    
    def batch_simplify(self, texts: List[str]) -> List[str]:
        """여러 텍스트 일괄 변환"""
        simplified_texts = []
        
        for text in texts:
            simplified = self.simplify_text(text)
            simplified_texts.append(simplified)
        
        return simplified_texts
    
    def interactive_demo(self):
        """대화형 데모"""
        print("\n🎯 Financial Text Simplifier Demo")
        print("복잡한 금융 용어를 쉬운 말로 바꿔드립니다.")
        print("종료하려면 'quit'를 입력하세요.\n")
        
        while True:
            text = input("복잡한 금융 문장 입력: ").strip()
            
            if text.lower() in ['quit', 'exit', '종료']:
                print("👋 종료합니다.")
                break
            
            if not text:
                continue
            
            # 변환
            simplified = self.simplify_text(text)
            print(f"📝 쉬운 설명: {simplified}\n")


def create_sample_training_data():
    """샘플 학습 데이터 생성"""
    
    training_data = [
        # 기본 금융 용어
        {
            "complex": "시가총액은 발행주식수에 주가를 곱한 값으로 기업의 시장가치를 나타냅니다.",
            "simple": "시가총액은 회사의 모든 주식을 합친 가격입니다."
        },
        {
            "complex": "매출채권회전율은 매출액을 평균매출채권으로 나눈 비율입니다.",
            "simple": "매출채권회전율은 외상값을 얼마나 빨리 받는지 보는 숫자입니다."
        },
        {
            "complex": "자기자본이익률(ROE)은 당기순이익을 자기자본으로 나눈 수익성 지표입니다.",
            "simple": "ROE는 회사가 가진 돈으로 얼마나 벌었는지 보는 비율입니다."
        },
        {
            "complex": "주가수익비율(PER)은 주가를 주당순이익으로 나눈 지표입니다.",
            "simple": "PER은 주식 가격이 회사 이익 대비 비싼지 싼지 보는 숫자입니다."
        },
        {
            "complex": "부채비율은 부채총계를 자기자본으로 나눈 재무안정성 지표입니다.",
            "simple": "부채비율은 회사가 빚을 얼마나 졌는지 보는 숫자입니다."
        },
        {
            "complex": "당좌비율은 당좌자산을 유동부채로 나눈 단기지급능력 지표입니다.",
            "simple": "당좌비율은 회사가 급한 빚을 갚을 수 있는지 보는 숫자입니다."
        },
        {
            "complex": "재고자산회전율은 매출원가를 평균재고자산으로 나눈 효율성 지표입니다.",
            "simple": "재고자산회전율은 물건이 얼마나 빨리 팔리는지 보는 숫자입니다."
        },
        {
            "complex": "총자산순이익률(ROA)은 당기순이익을 총자산으로 나눈 수익성 지표입니다.",
            "simple": "ROA는 회사 전체 재산으로 얼마나 벌었는지 보는 비율입니다."
        },
        
        # 투자 상품
        {
            "complex": "상장지수펀드(ETF)는 특정 지수를 추종하며 거래소에서 매매되는 펀드입니다.",
            "simple": "ETF는 주식처럼 사고팔 수 있는 펀드입니다."
        },
        {
            "complex": "전환사채는 일정 조건하에 주식으로 전환할 수 있는 회사채입니다.",
            "simple": "전환사채는 나중에 주식으로 바꿀 수 있는 채권입니다."
        },
        {
            "complex": "파생결합증권은 기초자산의 가격변동에 연계하여 수익이 결정되는 증권입니다.",
            "simple": "파생결합증권은 다른 상품 가격에 따라 수익이 바뀌는 투자 상품입니다."
        },
        {
            "complex": "환매조건부채권(RP)은 일정기간 후 다시 매입하는 조건으로 매도하는 채권입니다.",
            "simple": "RP는 나중에 다시 사겠다고 약속하고 일단 파는 채권입니다."
        },
        {
            "complex": "신주인수권부사채는 신주인수권이 부여된 회사채입니다.",
            "simple": "신주인수권부사채는 새 주식을 살 권리가 붙은 채권입니다."
        },
        {
            "complex": "주가연계증권(ELS)은 주가지수 변동에 수익이 연동되는 파생결합증권입니다.",
            "simple": "ELS는 주식 가격 움직임에 따라 수익이 정해지는 상품입니다."
        },
        {
            "complex": "양도성예금증서(CD)는 정기예금을 유가증권화한 금융상품입니다.",
            "simple": "CD는 정기예금을 다른 사람에게 팔 수 있게 만든 상품입니다."
        },
        
        # 리스크 관련
        {
            "complex": "신용위험은 거래상대방이 채무를 이행하지 못할 가능성입니다.",
            "simple": "신용위험은 빌려준 돈을 못 받을 위험입니다."
        },
        {
            "complex": "시장위험은 시장가격 변동으로 인한 손실 가능성입니다.",
            "simple": "시장위험은 가격이 떨어져서 손해 볼 위험입니다."
        },
        {
            "complex": "유동성위험은 자산을 적정가격에 현금화하지 못할 위험입니다.",
            "simple": "유동성위험은 급하게 팔 때 제값을 못 받을 위험입니다."
        },
        {
            "complex": "운영위험은 내부프로세스나 시스템 실패로 인한 손실위험입니다.",
            "simple": "운영위험은 회사 내부 실수로 손해 볼 위험입니다."
        },
        {
            "complex": "환위험은 환율변동으로 인한 손실가능성입니다.",
            "simple": "환위험은 환율이 바뀌어서 손해 볼 위험입니다."
        },
        
        # 금융 거래
        {
            "complex": "매도호가는 매도자가 제시하는 판매희망가격입니다.",
            "simple": "매도호가는 파는 사람이 받고 싶은 가격입니다."
        },
        {
            "complex": "매수호가는 매수자가 제시하는 구매희망가격입니다.",
            "simple": "매수호가는 사는 사람이 내고 싶은 가격입니다."
        },
        {
            "complex": "공매도는 주식을 빌려서 매도한 후 하락시 매수하여 상환하는 거래입니다.",
            "simple": "공매도는 주식을 빌려서 팔고 나중에 싸게 사서 갚는 거래입니다."
        },
        {
            "complex": "증거금은 거래의 이행을 보증하기 위해 예치하는 금액입니다.",
            "simple": "증거금은 거래할 때 미리 내는 보증금입니다."
        },
        {
            "complex": "배당금은 기업이 이익의 일부를 주주에게 분배하는 금액입니다.",
            "simple": "배당금은 회사가 번 돈을 주주들에게 나눠주는 것입니다."
        },
        
        # 금융 시장
        {
            "complex": "코스피지수는 한국거래소 유가증권시장 상장종목의 시가총액 가중평균지수입니다.",
            "simple": "코스피는 한국 큰 회사들의 주식 가격을 평균낸 숫자입니다."
        },
        {
            "complex": "코스닥지수는 코스닥시장 상장종목의 시가총액 가중평균지수입니다.",
            "simple": "코스닥은 한국 중소기업들의 주식 가격을 평균낸 숫자입니다."
        },
        {
            "complex": "장외거래는 정규거래소 밖에서 이루어지는 거래입니다.",
            "simple": "장외거래는 증권거래소가 아닌 곳에서 하는 거래입니다."
        },
        {
            "complex": "콜옵션은 특정가격에 기초자산을 매수할 수 있는 권리입니다.",
            "simple": "콜옵션은 정해진 가격에 살 수 있는 권리입니다."
        },
        {
            "complex": "풋옵션은 특정가격에 기초자산을 매도할 수 있는 권리입니다.",
            "simple": "풋옵션은 정해진 가격에 팔 수 있는 권리입니다."
        },
        
        # 대출/예금
        {
            "complex": "원리금균등상환은 매월 동일한 금액으로 원금과 이자를 상환하는 방식입니다.",
            "simple": "원리금균등상환은 매달 같은 금액을 갚는 방식입니다."
        },
        {
            "complex": "원금균등상환은 원금을 균등분할하여 이자와 함께 상환하는 방식입니다.",
            "simple": "원금균등상환은 원금을 똑같이 나누어 갚는 방식입니다."
        },
        {
            "complex": "거치기간은 원금상환을 유예하고 이자만 납부하는 기간입니다.",
            "simple": "거치기간은 이자만 내고 원금은 나중에 갚는 기간입니다."
        },
        {
            "complex": "연체이자는 약정기일에 상환하지 못한 채무에 부과되는 가산이자입니다.",
            "simple": "연체이자는 돈을 제때 안 갚았을 때 더 내는 이자입니다."
        },
        {
            "complex": "만기일시상환은 대출기간 중 이자만 납부하고 만기에 원금을 일시상환하는 방식입니다.",
            "simple": "만기일시상환은 이자만 내다가 마지막에 원금을 한번에 갚는 방식입니다."
        },
        
        # 보험
        {
            "complex": "보험료는 보험계약에 따라 보험계약자가 보험회사에 납입하는 금액입니다.",
            "simple": "보험료는 보험에 가입하고 내는 돈입니다."
        },
        {
            "complex": "보험금은 보험사고 발생시 보험회사가 지급하는 금액입니다.",
            "simple": "보험금은 사고가 나면 보험회사가 주는 돈입니다."
        },
        {
            "complex": "면책기간은 보험사고가 발생해도 보험금을 지급하지 않는 기간입니다.",
            "simple": "면책기간은 보험금을 안 주는 기간입니다."
        },
        {
            "complex": "해약환급금은 보험계약을 중도해지할 때 돌려받는 금액입니다.",
            "simple": "해약환급금은 보험을 중간에 그만둘 때 돌려받는 돈입니다."
        },
        {
            "complex": "보장한도는 보험회사가 지급하는 보험금의 최대한도입니다.",
            "simple": "보장한도는 보험회사가 최대로 줄 수 있는 돈입니다."
        },
        
        # 세금
        {
            "complex": "양도소득세는 자산을 양도하여 발생한 소득에 부과되는 세금입니다.",
            "simple": "양도소득세는 재산을 팔아서 번 돈에 내는 세금입니다."
        },
        {
            "complex": "종합소득세는 모든 소득을 합산하여 부과하는 세금입니다.",
            "simple": "종합소득세는 1년 동안 번 돈 전체에 내는 세금입니다."
        },
        {
            "complex": "부가가치세는 재화나 용역의 공급에 대해 부과되는 세금입니다.",
            "simple": "부가가치세는 물건을 사고팔 때 내는 세금입니다."
        },
        {
            "complex": "원천징수는 소득을 지급할 때 세금을 미리 떼고 지급하는 제도입니다.",
            "simple": "원천징수는 돈을 줄 때 세금을 미리 빼고 주는 것입니다."
        },
        {
            "complex": "세액공제는 산출세액에서 일정금액을 차감하는 제도입니다.",
            "simple": "세액공제는 낼 세금에서 빼주는 금액입니다."
        },
        
        # 추가 금융 용어
        {
            "complex": "신용등급은 채무상환능력을 평가하여 부여하는 등급입니다.",
            "simple": "신용등급은 돈을 잘 갚을지 평가한 점수입니다."
        },
        {
            "complex": "담보대출은 부동산이나 유가증권을 담보로 제공하고 받는 대출입니다.",
            "simple": "담보대출은 집이나 주식을 맡기고 받는 대출입니다."
        },
        {
            "complex": "신용대출은 담보 없이 신용도만으로 받는 대출입니다.",
            "simple": "신용대출은 믿음만으로 받는 대출입니다."
        },
        {
            "complex": "복리는 원금과 이자에 다시 이자가 붙는 이자계산방식입니다.",
            "simple": "복리는 이자에도 또 이자가 붙는 방식입니다."
        },
        {
            "complex": "단리는 원금에만 이자가 붙는 이자계산방식입니다.",
            "simple": "단리는 원금에만 이자가 붙는 방식입니다."
        }
    ]
    
    # JSON 파일로 저장
    with open("financial_training_data.json", "w", encoding="utf-8") as f:
        json.dump(training_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Created training data with {len(training_data)} examples")
    return training_data


if __name__ == "__main__":
    print("=" * 50)
    print("Financial Text Simplifier")
    print("KR-FinBert Encoder + KoGPT2 Decoder")
    print("=" * 50)
    
    # 옵션 선택
    print("\n1. Train new model (새 모델 학습)")
    print("2. Load and test model (모델 로드 후 테스트)")
    print("3. Interactive demo (대화형 데모)")
    print("4. Create sample data (샘플 데이터 생성)")
    
    choice = input("\nSelect option (1/2/3/4): ").strip()
    
    if choice == "1":
        # 모델 생성 및 학습
        simplifier = FinancialTextSimplifier()
        
        # Google Drive 마운트 (Colab용)
        print("\n📚 Preparing training data...")
        import os
        
        # Colab에서 Google Drive 마운트
        try:
            from google.colab import drive
            import os
            
            # Drive 마운트 (다른 계정 선택 가능)
            if not os.path.exists('/content/drive'):
                print("🔄 Please select Google account for Drive access...")
                drive.mount('/content/drive', force_remount=True)
            else:
                print("✅ Google Drive already mounted")
                
            # Google Drive의 파일 경로
            data_path = "/content/drive/MyDrive/financial_training_simplified.json"
            
            if not os.path.exists(data_path):
                print(f"⚠️ File not found at: {data_path}")
                print("Please ensure financial_training_simplified.json is in your Drive's root folder")
                
        except ImportError:
            # 로컬 환경
            data_path = "/Users/inter4259/Downloads/financial_training_simplified.json"
            print("📂 Using local file")
        
        # 데이터 로드
        if os.path.exists(data_path):
            print(f"✅ Loading simplified dataset from: {data_path}")
            dataset = simplifier.prepare_training_data(data_path)
        else:
            print(f"❌ File not found: {data_path}")
            print("Please upload financial_training_simplified.json to Google Drive")
            raise FileNotFoundError(data_path)
        
        print(f"Dataset size: {len(dataset)} examples")
        
        # 학습 - AdamW optimizer 사용, 학습률 스케줄링 적용
        print("\n📊 Training with improved hyperparameters...")
        print(f"  - Epochs: 10")
        print(f"  - Learning rate: 3e-5 with warmup")
        print(f"  - Gradient accumulation: 2 steps")
        print(f"  - Label smoothing: 0.1")
        print(f"  - Beam search: 6 beams")
        simplifier.train(dataset, epochs=10)
        
        # 테스트
        test_text = "주가수익비율(PER)은 주가를 주당순이익으로 나눈 지표입니다."
        result = simplifier.simplify_text(test_text)
        print(f"\n원문: {test_text}")
        print(f"변환: {result}")
        
        print("\n💡 Tip: 모델이 Google Drive에 저장되었습니다!")
        print("   경로: /content/drive/MyDrive/financial_simplifier_model/")
        
    elif choice == "2":
        # 저장된 모델 로드
        import os
        simplifier = FinancialTextSimplifier()
        
        # Google Drive에서 로드 (Colab용)
        try:
            from google.colab import drive
            
            # Google Drive 마운트 (필요시 다른 계정 선택)
            if not os.path.exists('/content/drive'):
                print("🔄 Mounting Google Drive...")
                print("📌 You can select different Google account if needed")
                drive.mount('/content/drive', force_remount=True)
            
            # Google Drive 모델 경로
            drive_model_path = "/content/drive/MyDrive/financial_simplifier_model"
            
            if os.path.exists(drive_model_path):
                print(f"✅ Found model in Google Drive")
                print(f"📂 Loading from: {drive_model_path}")
                simplifier.load_model(drive_model_path)
            else:
                print(f"❌ Model not found in Google Drive: {drive_model_path}")
                print("Please check if the model was saved correctly in option 1")
                # 로컬 시도
                local_path = "/content/financial_simplifier_model"
                if os.path.exists(local_path):
                    print(f"📂 Loading from local: {local_path}")
                    simplifier.load_model(local_path)
                else:
                    print("❌ No model found. Please train a model first (option 1)")
                    exit()
        except ImportError:
            # 로컬 환경 (Colab이 아닌 경우)
            print("📂 Running in local environment")
            local_path = "./financial_simplifier_model"
            if os.path.exists(local_path):
                simplifier.load_model(local_path)
            else:
                print("❌ Model not found. Please train first.")
                exit()
        
        # 테스트
        test_texts = [
            "파생결합증권은 기초자산의 가격변동에 연계하여 수익이 결정되는 증권입니다.",
            "신용파생상품은 신용위험을 기초자산으로 하는 파생금융상품입니다.",
            "환매조건부채권은 일정기간 후 다시 매입하는 조건으로 매도하는 채권입니다."
        ]
        
        for text in test_texts:
            result = simplifier.simplify_text(text)
            print(f"\n원문: {text}")
            print(f"변환: {result}")
    
    elif choice == "3":
        # 대화형 데모
        simplifier = FinancialTextSimplifier()
        
        # 기본 학습 데이터로 빠르게 학습
        print("\n🔧 Quick training with sample data...")
        create_sample_training_data()
        dataset = simplifier.prepare_training_data("financial_training_data.json")
        simplifier.train(dataset, epochs=1)
        
        # 데모 실행
        simplifier.interactive_demo()
    
    elif choice == "4":
        # 샘플 데이터 생성
        create_sample_training_data()
        print("\n📄 Sample data saved to 'financial_training_data.json'")
    
    else:
        print("Invalid choice")