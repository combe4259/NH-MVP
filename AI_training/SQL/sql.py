
# 1. 환경 설정 및 라이브러리 설치
!pip install transformers[torch] datasets sentencepiece huggingface_hub safetensors accelerate

import json
import torch
import pandas as pd
from datasets import Dataset, DatasetDict
from huggingface_hub import notebook_login
from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
    DataCollatorForSeq2Seq,
    Seq2SeqTrainingArguments,
    Seq2SeqTrainer
)

print("-" * 50)
print(f"PyTorch Device: {'cuda' if torch.cuda.is_available() else 'cpu'}")
print("필요한 라이브러리가 모두 설치되었습니다.")
print("-" * 50)

# ----------------------------------------------------------------------
# 2. Hugging Face 로그인
# ----------------------------------------------------------------------
print("Hugging Face 로그인이 필요합니다 (모델 업로드용)...")
notebook_login()

# ----------------------------------------------------------------------
# paust/pko-t5-base 모델 Fine-tuning
# ----------------------------------------------------------------------
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch

# 한국어 T5 모델
BASE_MODEL_NAME = "paust/pko-t5-base"
NEW_MODEL_REPO_ID = "combe4259/SQLNL"

print(f"새 모델 로드 시작: {BASE_MODEL_NAME}")

# 모델과 토크나이저 로드
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_NAME)
model = AutoModelForSeq2SeqLM.from_pretrained(BASE_MODEL_NAME)

print("모델 로드 완료")
print(f"토크나이저 vocab: {tokenizer.vocab_size}")
print(f"모델 vocab: {model.config.vocab_size}")
print(f"모델 파라미터 수: {sum(p.numel() for p in model.parameters()):,}")

# 모델을 훈련 모드로 설정
model.train()
print(f"훈련 모드 활성화: {model.training}")

# Vocab 크기 확인 및 조정
if tokenizer.vocab_size != model.config.vocab_size:
    print("Vocab 크기 불일치 - 조정")
    model.resize_token_embeddings(tokenizer.vocab_size)
    print(f"조정 완료: {model.config.vocab_size}")
else:
    print("Vocab 크기 일치 - 조정 불필요")

# 기본 테스트
print("\n기본 동작 테스트:")
test_input = "테스트"
inputs = tokenizer(test_input, return_tensors="pt")
print(f"토큰화 성공: {inputs['input_ids'].shape}")

# GPU 이동 및 forward pass 테스트
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = model.to(device)
inputs = {k: v.to(device) for k, v in inputs.items()}

model.eval()
with torch.no_grad():
    try:
        outputs = model(**inputs)
        print(f"Forward pass 성공: logits shape = {outputs.logits.shape}")
        print(f"Logits 범위: {outputs.logits.min().item():.4f} ~ {outputs.logits.max().item():.4f}")
        print(f"Logits에 NaN: {torch.isnan(outputs.logits).any()}")
    except Exception as e:
        print(f"Forward pass 실패: {e}")

print("paust/pko-t5-base 모델 준비 완료")

# ----------------------------------------------------------------------
# 3.5 Google Drive 마운트
# ----------------------------------------------------------------------
from google.colab import drive
import os

print("Google Drive 마운트를 시작")
drive.mount('/content/drive')

DRIVE_SQL_PATH = "/content/drive/MyDrive/sqldataset"

# ----------------------------------------------------------------------
# 4. 데이터셋 준비 및 전처리
# ----------------------------------------------------------------------
import os
import glob
from datasets import Dataset, DatasetDict
import json

ROOT_DATASET_PATH = "/content/drive/MyDrive/sqldataset"
TRAIN_DATA_PATH = os.path.join(ROOT_DATASET_PATH, "Training")
VALIDATION_DATA_PATH = os.path.join(ROOT_DATASET_PATH, "Validation")

def create_schema_text_map(root_data_path):
    """
    지정된 경로의 모든 하위 폴더를 검색하여
    모든 '...db_annotation.json' 파일을 찾아 하나의 스키마 맵으로
    """
    print(f"  ... 스키마 파일 검색 시작 (전체 경로): {root_data_path}")

    # Training/data와 Validation/data 경로에서 스키마 파일 검색
    schema_files = []
    for sub_path in ['Training/data', 'Validation/data']:
        full_path = os.path.join(root_data_path, sub_path)
        if os.path.exists(full_path):
            schema_files.extend(glob.glob(f"{full_path}/**/*_db_annotation.json", recursive=True))

    if not schema_files:
        print(f"[오류] 스키마 파일(*_db_annotation.json)을 찾을 수 없습니다.")
        return None

    print(f"  ... 총 {len(schema_files)}개의 스키마 파일을 찾았습니다.")

    schema_map = {}
    for file_path in schema_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_schema_data = json.load(f)

            if 'data' not in raw_schema_data:
                continue

            schema_data_list = raw_schema_data['data']
            for db in schema_data_list:
                db_id = db.get('db_id')
                if not db_id: continue

                schema_parts = []
                table_names = db.get('table_names_original', [])
                column_names_data = db.get('column_names_original', [])

                for i, table_name in enumerate(table_names):
                    cols = [col[1] for col in column_names_data if col[0] == i]
                    schema_parts.append(f"{table_name}: {', '.join(cols)}")

                if db_id not in schema_map:
                    schema_map[db_id] = " | ".join(schema_parts)
        except Exception as e:
            print(f"   경고: {file_path} 파일 처리 중 오류 발생: {e}")

    print(f"  ... 총 {len(schema_map)}개의 고유 DB 스키마를 로드했습니다.")
    return schema_map

def load_labels_from_path(specific_data_path, schema_map):
    """
    특정 경로(Training 또는 Validation)에서만 라벨 파일을 검색하여 입력/출력 리스트를 반환하는 헬퍼 함수.
    """
    print(f" 라벨 파일 검색 중: {specific_data_path}")

    # label 폴더에서 라벨 파일 검색
    label_path = os.path.join(specific_data_path, "label")
    label_files = []
    if os.path.exists(label_path):
        label_files = glob.glob(f"{label_path}/**/TEXT_NL2SQL_label_*.json", recursive=True)

    if not label_files:
        print(f"[오류] 라벨 파일을 찾을 수 없습니다.")
        return None

    print(f"  ... {len(label_files)}개의 라벨 파일을 찾았습니다.")

    inputs = []
    outputs = []
    missing_schema_count = 0
    total_items = 0

    for file_path in label_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)

            if 'data' not in raw_data:
                continue

            data_list = raw_data['data']
            total_items += len(data_list)

            for item in data_list:
                db_id = item.get('db_id')
                if db_id in schema_map:
                    schema_text = schema_map[db_id]
                    utterance = item.get('utterance')
                    sql_query = item.get('query')

                    if not all([utterance, sql_query]):
                        continue

                    model_input_text = f"[SCHEMA: {schema_text}] [UTTERANCE: {utterance}]"
                    inputs.append(model_input_text)
                    outputs.append(sql_query)
                else:
                    missing_schema_count += 1
        except Exception as e:
            print(f" 경고: {file_path} 파일 처리 중 오류 발생: {e}")

    print(f"  ... 총 {total_items}개 데이터 중 {len(inputs)}개 처리 완료.")
    if missing_schema_count > 0:
        print(f" 경고: {missing_schema_count}개 데이터의 스키마를 찾지 못해 제외했습니다.")

    return Dataset.from_dict({"input_text": inputs, "target_text": outputs})

# 전처리 함수 - padding을 -100으로 변환
def preprocess_function(examples):
    # 입력 토큰화
    model_inputs = tokenizer(
        examples['input_text'],
        max_length=512,
        padding="max_length",
        truncation=True
    )

    # 타겟 토큰화
    labels = tokenizer(
        examples['target_text'],
        max_length=256,
        padding="max_length",
        truncation=True
    )

    # 라벨 처리
    model_inputs["labels"] = [
        [(label if label != tokenizer.pad_token_id else -100) for label in label_seq]
        for label_seq in labels["input_ids"]
    ]

    return model_inputs

# 메인 데이터 로직 실행
print("\n[2/7] AI Hub 데이터셋 준비 시작...")

# 1. 스키마 맵 생성
schema_dictionary = create_schema_text_map(ROOT_DATASET_PATH)

if schema_dictionary and len(schema_dictionary) > 0:
    # 2. Training 데이터 로드
    train_dataset = load_labels_from_path(TRAIN_DATA_PATH, schema_dictionary)
    # 3. Validation 데이터 로드
    validation_dataset = load_labels_from_path(VALIDATION_DATA_PATH, schema_dictionary)

    if train_dataset and validation_dataset:
        # 4. DatasetDict 생성
        # 4. DatasetDict 생성
        split_dataset = DatasetDict({
            'train': train_dataset,
            'test': validation_dataset
        })

        print(f"✅ 훈련 데이터셋 크기: {len(split_dataset['train'])}")
        print(f"✅ 검증 데이터셋 크기: {len(split_dataset['test'])}")
        print("✅ 데이터셋 준비 완료!")
    else:
        raise Exception("데이터셋 로드 실패")
else:
    raise Exception("스키마 로드 실패")
# 본격적인 훈련 설정
from transformers import Seq2SeqTrainingArguments, DataCollatorForSeq2Seq, Seq2SeqTrainer


DRIVE_OUTPUT_DIR = "/content/ko-t5-nl2sql-stage1-results"

# 훈련 설정
training_args = Seq2SeqTrainingArguments(
    output_dir=DRIVE_OUTPUT_DIR,

    learning_rate=5e-5,

    per_device_train_batch_size=16,
    per_device_eval_batch_size=8,
    gradient_accumulation_steps=2,

    max_grad_norm=1.0,
    warmup_steps=200,
    weight_decay=0.01,

    num_train_epochs=3,

    eval_strategy="steps",
    eval_steps=2000,
    save_strategy="steps",
    save_steps=4000,
    save_total_limit=1,

    logging_steps=500,
    logging_first_step=True,

    fp16=True,
    dataloader_drop_last=True,
    dataloader_num_workers=2,

    load_best_model_at_end=False,

    seed=42,
    push_to_hub=False,
)

# 데이터 콜레이터
data_collator = DataCollatorForSeq2Seq(
    tokenizer=tokenizer,
    model=model,
    label_pad_token_id=-100,
    return_tensors="pt"
)

# 전체 데이터셋 토큰화
print("데이터셋 토큰화 중...")
full_tokenized_datasets = split_dataset.map(
    preprocess_function,
    batched=True,
    remove_columns=["input_text", "target_text"],
    desc="Tokenizing datasets"
)

print(f"전체 데이터셋: 훈련 {len(full_tokenized_datasets['train'])}개, 테스트 {len(full_tokenized_datasets['test'])}개")

# Trainer 생성
trainer = Seq2SeqTrainer(
    model=model,
    args=training_args,
    train_dataset=full_tokenized_datasets["train"],
    eval_dataset=full_tokenized_datasets["test"],
    data_collator=data_collator,
    tokenizer=tokenizer
)

print("본격적인 훈련 준비 완료!")
print("trainer.train() 실행하면 본격적인 훈련이 시작됩니다.")
# ----------------------------------------------------------------------
# 6. 훈련기(Trainer) 초기화 및 훈련 시작
# ----------------------------------------------------------------------
print("\n[4/7] Seq2Seq 훈련기(Trainer) 초기화...")
trainer = Seq2SeqTrainer(
    model=model,
    args=training_args,
    train_dataset=full_tokenized_datasets["train"],
    eval_dataset=full_tokenized_datasets["test"],
    data_collator=data_collator,
    tokenizer=tokenizer
)

print("\n[5/7] Fine-tuning을 시작")
trainer.train()

print(" 훈련이 완료되었습니다!")

