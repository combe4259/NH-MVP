"""
Confusion Binary 모델을 pytorch_model.bin으로 저장
"""

import torch
import os
from daisee_confusion_binary import DAiSEEConfusionNet

def save_model_as_bin(model_path='confusion_binary_model.pth',
                      output_dir='./hf_model_confusion'):
    """
    Confusion Binary 모델을 .bin 형식으로 저장 (구조 + 가중치 포함)
    """
    
    # 출력 디렉토리 생성
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. 모델 로드
    print("Loading Confusion Binary model...")
    model = DAiSEEConfusionNet()  # Confusion 이진 분류 모델
    model.load_state_dict(torch.load(model_path, map_location='cpu'))
    model.eval()
    
    # 2. 전체 모델 저장 (구조 + 가중치)
    output_path = os.path.join(output_dir, 'pytorch_model.bin')
    torch.save(model, output_path)
    
    print(f"✅ Confusion Binary Model saved as: {output_path}")
    print(f"📦 File size: {os.path.getsize(output_path) / 1024 / 1024:.2f} MB")
    
    # 모델 정보 저장 (메타데이터)
    metadata = {
        "model_type": "DAiSEEConfusionNet",
        "task": "binary_classification",
        "classes": ["Not Confused (0)", "Confused (1-3)"],
        "input_shape": [30, 3, 112, 112],  # [sequence_length, channels, height, width]
        "source": "daisee_confusion_binary.py"
    }
    
    import json
    metadata_path = os.path.join(output_dir, 'model_metadata.json')
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"📋 Metadata saved as: {metadata_path}")
    
    return output_path


if __name__ == "__main__":
    # Confusion Binary 모델을 .bin으로 저장
    print("Converting confusion_binary_model.pth to .bin format...")
    save_model_as_bin()