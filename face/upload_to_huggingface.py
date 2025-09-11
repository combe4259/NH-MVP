"""
DAiSEE 모델을 HuggingFace Hub에 업로드
"""

import torch
import torch.nn as nn
import torchvision.models as models
from huggingface_hub import HfApi, create_repo, upload_file
import json
import os
from daisee_local_pytorch import DAiSEECNNLSTM

def save_model_for_huggingface(model_path='daisee_local_model.pth', 
                               output_dir='./hf_model'):
    """
    모델을 HuggingFace 형식으로 저장
    """
    
    # 출력 디렉토리 생성
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. 모델 로드
    print("Loading model...")
    model = DAiSEECNNLSTM()
    model.load_state_dict(torch.load(model_path, map_location='cpu'))
    model.eval()
    
    # 2. 전체 모델 저장 (구조 + 가중치)
    torch.save(model, os.path.join(output_dir, 'pytorch_model.bin'))
    print("✅ Model saved")
    
    # 3. 설정 파일 생성
    config = {
        "model_type": "daisee_cnn_lstm",
        "architecture": "MobileNetV2 + LSTM",
        "num_classes": 4,
        "emotions": ["engagement", "confusion", "frustration", "boredom"],
        "levels": ["Very Low", "Low", "High", "Very High"],
        "input_size": [30, 3, 112, 112],  # [sequence_length, channels, height, width]
        "hidden_dim": 256,
        "num_layers": 2,
        "preprocessing": {
            "mean": [0.485, 0.456, 0.406],
            "std": [0.229, 0.224, 0.225]
        }
    }
    
    with open(os.path.join(output_dir, 'config.json'), 'w') as f:
        json.dump(config, f, indent=2)
    print("✅ Config saved")
    
    # 4. 모델 카드 생성
    model_card = """---
tags:
- video-classification
- emotion-recognition
- daisee
- pytorch
license: apache-2.0
datasets:
- DAiSEE
metrics:
- accuracy
---

# DAiSEE Emotion Recognition Model

## Model Description
This model analyzes facial expressions in video sequences to detect learning-related emotional states.

## Emotions Detected
- **Engagement**: Level of attention and interest
- **Confusion**: Difficulty understanding content  
- **Frustration**: Emotional distress
- **Boredom**: Lack of interest

Each emotion is classified into 4 levels:
- 0: Very Low
- 1: Low
- 2: High
- 3: Very High

## Architecture
- **Backbone**: MobileNetV2 (pretrained on ImageNet)
- **Temporal**: LSTM with attention mechanism
- **Input**: 30 frames @ 112x112 pixels
- **Output**: 4 emotion levels (0-3)

## Usage

```python
from huggingface_hub import hf_hub_download
import torch

# Download model
model_path = hf_hub_download(
    repo_id="your-username/daisee-emotion-recognition",
    filename="pytorch_model.bin"
)

# Load model
model = torch.load(model_path)
model.eval()

# Inference
with torch.no_grad():
    # input: [1, 30, 3, 112, 112]
    output = model(video_frames)
    # output: {
    #   'engagement': tensor([[...]]),
    #   'confusion': tensor([[...]]),
    #   'frustration': tensor([[...]]),
    #   'boredom': tensor([[...]])
    # }
```

## Training Data
Trained on DAiSEE dataset (Dataset for Affective States in E-Learning)

## Limitations
- Trained primarily on educational contexts
- May not generalize well to other scenarios
- Requires frontal face view

## Citation
```bibtex
@inproceedings{gupta2016daisee,
  title={DAiSEE: Dataset for Affective States in E-Learning},
  author={Gupta, Abhay and others},
  booktitle={CVPR Workshops},
  year={2016}
}
```
"""
    
    with open(os.path.join(output_dir, 'README.md'), 'w') as f:
        f.write(model_card)
    print("✅ Model card saved")
    
    return output_dir


def upload_to_huggingface(model_dir='./hf_model', 
                         repo_name='daisee-emotion-recognition',
                         private=False):
    """
    HuggingFace Hub에 업로드
    """
    
    print("\n" + "="*50)
    print("📤 Uploading to HuggingFace Hub")
    print("="*50)
    
    # HuggingFace 로그인 확인
    try:
        api = HfApi()
        user_info = api.whoami()
        username = user_info['name']
        print(f"✅ Logged in as: {username}")
    except Exception as e:
        print("❌ Not logged in. Please run: huggingface-cli login")
        return
    
    repo_id = f"{username}/{repo_name}"
    
    # 레포지토리 생성
    try:
        create_repo(repo_id, private=private, repo_type="model")
        print(f"✅ Created repository: {repo_id}")
    except Exception as e:
        print(f"ℹ️ Repository already exists or error: {e}")
    
    # 파일 업로드
    files_to_upload = [
        'pytorch_model.bin',
        'config.json',
        'README.md'
    ]
    
    for filename in files_to_upload:
        file_path = os.path.join(model_dir, filename)
        if os.path.exists(file_path):
            try:
                api.upload_file(
                    path_or_fileobj=file_path,
                    path_in_repo=filename,
                    repo_id=repo_id,
                    repo_type="model"
                )
                print(f"✅ Uploaded: {filename}")
            except Exception as e:
                print(f"❌ Failed to upload {filename}: {e}")
    
    print(f"\n🎉 Model available at: https://huggingface.co/{repo_id}")
    return repo_id


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', default='daisee_local_model.pth', 
                       help='Path to trained model')
    parser.add_argument('--upload', action='store_true',
                       help='Upload to HuggingFace Hub')
    parser.add_argument('--private', action='store_true',
                       help='Make repository private')
    args = parser.parse_args()
    
    # 모델 준비
    output_dir = save_model_for_huggingface(args.model)
    
    # HuggingFace 업로드
    if args.upload:
        # 먼저 로그인 필요
        print("\n⚠️ Make sure you're logged in:")
        print("Run: huggingface-cli login")
        
        proceed = input("\nProceed with upload? (y/n): ")
        if proceed.lower() == 'y':
            upload_to_huggingface(output_dir, private=args.private)