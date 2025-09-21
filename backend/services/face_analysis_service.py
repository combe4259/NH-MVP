"""
CNN-LSTM 기반 얼굴 표정 분석 서비스
"""

import torch
import torch.nn as nn
import torchvision.models as models
import torchvision.transforms as transforms
import numpy as np
import base64
from PIL import Image
from io import BytesIO
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class DAiSEECNNLSTM(nn.Module):
    """CNN-LSTM 모델 (face.py와 동일한 구조)"""
    
    def __init__(self, hidden_dim=256, num_layers=2):
        super(DAiSEECNNLSTM, self).__init__()
        
        # MobileNetV2 백본
        self.cnn = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.IMAGENET1K_V1)
        self.cnn.classifier = nn.Identity()
        self.feature_dim = 1280
        
        # LSTM
        self.lstm = nn.LSTM(
            input_size=self.feature_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=0.3 if num_layers > 1 else 0
        )
        
        # Attention
        self.attention = nn.Sequential(
            nn.Linear(hidden_dim, 128),
            nn.Tanh(),
            nn.Linear(128, 1),
            nn.Softmax(dim=1)
        )
        
        # 분류 헤드 (confusion만 사용)
        self.confusion_classifier = nn.Linear(hidden_dim, 4)
        self.dropout = nn.Dropout(0.4)
    
    def forward(self, x):
        batch_size, seq_len, c, h, w = x.size()
        
        # CNN 특징 추출
        x = x.view(-1, c, h, w)
        features = self.cnn(x)
        features = features.view(batch_size, seq_len, -1)
        
        # LSTM
        lstm_out, _ = self.lstm(features)
        
        # Attention
        attention_weights = self.attention(lstm_out)
        attended = torch.sum(lstm_out * attention_weights, dim=1)
        
        # Dropout
        attended = self.dropout(attended)
        
        # Confusion 분류
        confusion_output = self.confusion_classifier(attended)
        
        return confusion_output


class FaceAnalysisService:
    """얼굴 표정 분석 서비스"""
    
    def __init__(self, model_path: str = None):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = DAiSEECNNLSTM().to(self.device)
        
        # 모델 가중치 로드 (학습된 모델이 있다면)
        if model_path:
            try:
                self.model.load_state_dict(torch.load(model_path, map_location=self.device))
                self.model.eval()
                logger.info(f"CNN-LSTM 모델 로드 완료: {model_path}")
            except Exception as e:
                logger.warning(f"모델 로드 실패, 기본 가중치 사용: {e}")
        else:
            self.model.eval()
            logger.info("CNN-LSTM 모델 초기화 (기본 가중치)")
        
        # 이미지 전처리 변환
        self.transform = transforms.Compose([
            transforms.Resize((112, 112)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                              std=[0.229, 0.224, 0.225])
        ])
    
    def decode_base64_image(self, base64_str: str) -> Image.Image:
        """Base64 이미지 디코딩"""
        try:
            image_data = base64.b64decode(base64_str)
            image = Image.open(BytesIO(image_data))
            if image.mode != 'RGB':
                image = image.convert('RGB')
            return image
        except Exception as e:
            logger.error(f"이미지 디코딩 실패: {e}")
            return None
    
    async def analyze_frames(self, frames: List[str]) -> Dict[str, Any]:
        """
        프레임 시퀀스 분석
        
        Args:
            frames: Base64 인코딩된 프레임 리스트 (30개)
        
        Returns:
            분석 결과 (confusion 레벨 등)
        """
        try:
            # Base64 프레임을 텐서로 변환
            frame_tensors = []
            
            for frame_base64 in frames:
                image = self.decode_base64_image(frame_base64)
                if image:
                    tensor = self.transform(image)
                    frame_tensors.append(tensor)
                else:
                    # 빈 프레임 대체
                    frame_tensors.append(torch.zeros(3, 112, 112))
            
            # 부족한 프레임 패딩
            while len(frame_tensors) < 30:
                if frame_tensors:
                    frame_tensors.append(frame_tensors[-1])
                else:
                    frame_tensors.append(torch.zeros(3, 112, 112))
            
            # 초과 프레임 자르기
            frame_tensors = frame_tensors[:30]
            
            # 배치 텐서 생성 (1, 30, 3, 112, 112)
            input_tensor = torch.stack(frame_tensors).unsqueeze(0).to(self.device)
            
            # 모델 추론
            with torch.no_grad():
                confusion_logits = self.model(input_tensor)
                confusion_probs = torch.softmax(confusion_logits, dim=1)
                confusion_level = torch.argmax(confusion_probs, dim=1).item()
                confidence = torch.max(confusion_probs).item()
            
            result = {
                "confusion": confusion_level,  # 0-3 레벨
                "confusion_probability": confusion_probs[0, confusion_level].item(),
                "confidence": confidence,
                "all_probabilities": {
                    "level_0": confusion_probs[0, 0].item(),
                    "level_1": confusion_probs[0, 1].item(),
                    "level_2": confusion_probs[0, 2].item(),
                    "level_3": confusion_probs[0, 3].item()
                }
            }
            
            logger.info(f"얼굴 분석 완료 - Confusion Level: {confusion_level}")
            return result
            
        except Exception as e:
            logger.error(f"프레임 분석 실패: {e}")
            # 에러 시 기본값 반환
            return {
                "confusion": 1,  # 중간 레벨
                "confusion_probability": 0.5,
                "confidence": 0.5,
                "error": str(e)
            }

# 전역 서비스 인스턴스
face_analyzer = FaceAnalysisService()