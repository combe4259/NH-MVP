"""
DAiSEE 모델을 pytorch_model.bin으로 저장
"""

import torch
import os
from daisee_local_pytorch import DAiSEECNNLSTM

def save_model_as_bin(model_path='daisee_local_model.pth', 
                      output_dir='./hf_model'):
    """
    모델을 .bin 형식으로 저장 (구조 + 가중치 포함)
    """
    
    # 출력 디렉토리 생성
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. 모델 로드
    print("Loading model...")
    model = DAiSEECNNLSTM()
    model.load_state_dict(torch.load(model_path, map_location='cpu'))
    model.eval()
    
    # 2. 전체 모델 저장 (구조 + 가중치)
    output_path = os.path.join(output_dir, 'pytorch_model.bin')
    torch.save(model, output_path)
    
    print(f"✅ Model saved as: {output_path}")
    print(f"📦 File size: {os.path.getsize(output_path) / 1024 / 1024:.2f} MB")
    
    return output_path


if __name__ == "__main__":
    # 모델을 .bin으로 저장
    save_model_as_bin()