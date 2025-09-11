"""
로컬 DAiSEE 데이터셋으로 PyTorch 모델 학습
"""

import os
import cv2
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as models
import torchvision.transforms as transforms
from torch.utils.data import Dataset, DataLoader
import numpy as np
import pandas as pd
from typing import List, Tuple, Dict
from tqdm import tqdm
import glob

# GPU 설정 (Mac M3 Pro의 경우 MPS 사용)
if torch.cuda.is_available():
    device = torch.device("cuda")
elif torch.backends.mps.is_available():
    device = torch.device("mps")
else:
    device = torch.device("cpu")
print(f"Using device: {device}")

class LocalDAiSEEDataset(Dataset):
    """로컬 DAiSEE 데이터셋"""
    
    def __init__(self, 
                 data_root: str = "/Users/inter4259/Desktop/DAiSEE",
                 subset: str = 'Train',
                 sequence_length: int = 30,
                 image_size: Tuple[int, int] = (112, 112),
                 max_samples: int = None):
        """
        Args:
            data_root: DAiSEE 루트 폴더
            subset: 'Train', 'Test', 'Validation'
            sequence_length: 비디오에서 추출할 프레임 수
            image_size: 이미지 크기
            max_samples: 최대 샘플 수 (테스트용)
        """
        self.data_root = data_root
        self.subset = subset
        self.sequence_length = sequence_length
        self.image_size = image_size
        
        # 라벨 파일 경로
        labels_file = os.path.join(data_root, "Labels", f"{subset}Labels.csv")
        print(f"Loading labels from {labels_file}...")
        self.labels_df = pd.read_csv(labels_file)
        
        # 컬럼명 공백 제거
        self.labels_df.columns = self.labels_df.columns.str.strip()
        print(f"Columns: {self.labels_df.columns.tolist()}")
        
        # 비디오 경로와 라벨 매칭
        self.video_paths = []
        self.labels = []
        
        video_dir = os.path.join(data_root, "DataSet", subset)
        print(f"Searching for videos in {video_dir}...")
        
        # 실제 존재하는 비디오 파일 찾기
        found_count = 0
        missing_count = 0
        
        for idx, row in tqdm(self.labels_df.iterrows(), total=len(self.labels_df), desc="Loading videos"):
            clip_id = row['ClipID']
            # .avi 확장자 제거
            if clip_id.endswith('.avi'):
                clip_id = clip_id[:-4]
            
            # 사용자ID와 비디오ID 분리 (예: 1100011002 -> 110001, 1002)
            user_id = clip_id[:-4]  # 마지막 4자리 제외
            video_id = clip_id[-4:]  # 마지막 4자리
            full_video_id = user_id + video_id
            
            # 비디오 파일 경로
            video_path = os.path.join(video_dir, user_id, full_video_id, f"{full_video_id}.avi")
            
            if os.path.exists(video_path):
                self.video_paths.append(video_path)
                self.labels.append({
                    'boredom': row['Boredom'],
                    'engagement': row['Engagement'],
                    'confusion': row['Confusion'],
                    'frustration': row['Frustration']
                })
                found_count += 1
                
                if max_samples and found_count >= max_samples:
                    break
            else:
                missing_count += 1
        
        print(f"✅ Found {found_count} videos")
        if missing_count > 0:
            print(f"⚠️ Missing {missing_count} videos")
        
        # 전처리 변환
        self.transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize(image_size),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                              std=[0.229, 0.224, 0.225])
        ])
    
    def __len__(self):
        return len(self.video_paths)
    
    def __getitem__(self, idx):
        """비디오와 라벨 로드"""
        video_path = self.video_paths[idx]
        labels = self.labels[idx]
        
        # 비디오 로드
        frames = self.load_video(video_path)
        
        return frames, labels
    
    def load_video(self, video_path: str) -> torch.Tensor:
        """비디오 파일 로드 및 프레임 추출"""
        cap = cv2.VideoCapture(video_path)
        
        # 전체 프레임 수 확인
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        if total_frames == 0:
            print(f"Warning: Cannot read video {video_path}")
            cap.release()
            return torch.randn(self.sequence_length, 3, *self.image_size)
        
        # 균등 간격으로 프레임 인덱스 선택
        if total_frames < self.sequence_length:
            indices = list(range(total_frames)) * (self.sequence_length // total_frames + 1)
            indices = indices[:self.sequence_length]
        else:
            indices = np.linspace(0, total_frames-1, self.sequence_length, dtype=int)
        
        frames = []
        for frame_idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            
            if ret and frame is not None:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame = self.transform(frame)
                frames.append(frame)
            else:
                if frames:
                    frames.append(frames[-1])
                else:
                    frames.append(torch.zeros(3, *self.image_size))
        
        cap.release()
        
        return torch.stack(frames)


class DAiSEECNNLSTM(nn.Module):
    """CNN-LSTM 모델"""
    
    def __init__(self, hidden_dim=256, num_layers=2):
        super(DAiSEECNNLSTM, self).__init__()
        
        # MobileNetV2 백본
        self.cnn = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.IMAGENET1K_V1)
        self.cnn.classifier = nn.Identity()
        self.feature_dim = 1280
        
        # 일부 레이어 고정
        for param in list(self.cnn.parameters())[:-10]:
            param.requires_grad = False
        
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
        
        # 분류 헤드
        self.classifiers = nn.ModuleDict({
            'engagement': nn.Linear(hidden_dim, 4),
            'confusion': nn.Linear(hidden_dim, 4),
            'frustration': nn.Linear(hidden_dim, 4),
            'boredom': nn.Linear(hidden_dim, 4)
        })
        
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
        
        # 분류
        outputs = {}
        for name, classifier in self.classifiers.items():
            outputs[name] = classifier(attended)
        
        return outputs


def train_local_daisee(num_epochs=5, batch_size=4, max_samples=None):
    """로컬 DAiSEE 데이터로 학습"""
    
    print("=" * 50)
    print("로컬 DAiSEE 데이터셋으로 학습")
    print("=" * 50)
    
    # 데이터셋 생성
    print("\n📊 Loading datasets...")
    train_dataset = LocalDAiSEEDataset(
        subset='Train',
        max_samples=max_samples
    )
    
    val_dataset = LocalDAiSEEDataset(
        subset='Validation',
        max_samples=min(100, max_samples) if max_samples else None
    )
    
    # DataLoader 생성
    train_loader = DataLoader(
        train_dataset, 
        batch_size=batch_size, 
        shuffle=True,
        num_workers=0  # Windows/Mac 호환성
    )
    
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size * 2,  # Validation은 더 큰 배치 가능
        shuffle=False,
        num_workers=0
    )
    
    print(f"Train samples: {len(train_dataset)}")
    print(f"Validation samples: {len(val_dataset)}")
    
    # 모델 생성
    print("\n🤖 Creating model...")
    model = DAiSEECNNLSTM().to(device)
    
    # 손실 함수와 옵티마이저
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='min', patience=3, factor=0.5
    )
    
    # 학습
    print("\n🚀 Starting training...")
    
    for epoch in range(num_epochs):
        # Training
        model.train()
        train_loss = 0
        train_batches = 0
        
        progress_bar = tqdm(train_loader, desc=f"Epoch {epoch+1}/{num_epochs}")
        
        for batch_idx, (frames, labels) in enumerate(progress_bar):
            frames = frames.to(device)
            
            # Forward
            outputs = model(frames)
            
            # 손실 계산
            loss = 0
            for name in ['engagement', 'confusion', 'frustration', 'boredom']:
                target = torch.as_tensor(labels[name], dtype=torch.long).to(device)
                loss += criterion(outputs[name], target)
            
            # Backward
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
            train_batches += 1
            
            # Progress bar 업데이트
            progress_bar.set_postfix({'loss': f'{loss.item():.4f}'})
        
        # Validation
        model.eval()
        val_loss = 0
        val_batches = 0
        correct = {name: 0 for name in ['engagement', 'confusion', 'frustration', 'boredom']}
        total = 0
        
        with torch.no_grad():
            for frames, labels in tqdm(val_loader, desc="Validation"):
                frames = frames.to(device)
                outputs = model(frames)
                
                # 손실 계산
                loss = 0
                for name in ['engagement', 'confusion', 'frustration', 'boredom']:
                    target = torch.as_tensor(labels[name], dtype=torch.long).to(device)
                    loss += criterion(outputs[name], target)
                    
                    # 정확도 계산
                    _, predicted = torch.max(outputs[name], 1)
                    correct[name] += (predicted == target).sum().item()
                
                val_loss += loss.item()
                total += frames.size(0)
                val_batches += 1
        
        # 평균 계산
        avg_train_loss = train_loss / max(train_batches, 1)
        avg_val_loss = val_loss / max(val_batches, 1)
        
        print(f"\nEpoch {epoch+1}/{num_epochs}")
        print(f"Train Loss: {avg_train_loss:.4f}")
        print(f"Val Loss: {avg_val_loss:.4f}")
        
        if total > 0:
            for name in ['engagement', 'confusion', 'frustration', 'boredom']:
                acc = correct[name] / total * 100
                print(f"  {name}: {acc:.2f}%")
        
        # Learning rate 조정
        scheduler.step(avg_val_loss)
    
    # 모델 저장
    torch.save(model.state_dict(), 'daisee_local_model.pth')
    print("\n✅ Model saved as 'daisee_local_model.pth'")
    
    return model


def test_final_model(model_path='daisee_local_model.pth', max_samples=None):
    """학습된 모델을 Test 데이터로 최종 평가"""
    
    print("\n" + "=" * 50)
    print("🧪 Test 데이터로 최종 평가")
    print("=" * 50)
    
    # Test 데이터셋 로드
    test_dataset = LocalDAiSEEDataset(
        subset='Test',
        max_samples=max_samples
    )
    
    test_loader = DataLoader(
        test_dataset,
        batch_size=4,
        shuffle=False,
        num_workers=0
    )
    
    print(f"Test samples: {len(test_dataset)}")
    
    # 모델 로드
    model = DAiSEECNNLSTM().to(device)
    model.load_state_dict(torch.load(model_path))
    model.eval()
    print(f"✅ Model loaded from {model_path}")
    
    # 평가
    correct = {name: 0 for name in ['engagement', 'confusion', 'frustration', 'boredom']}
    total = 0
    all_predictions = []
    all_labels = []
    
    with torch.no_grad():
        for frames, labels in tqdm(test_loader, desc="Testing"):
            frames = frames.to(device)
            outputs = model(frames)
            
            for name in ['engagement', 'confusion', 'frustration', 'boredom']:
                target = torch.as_tensor(labels[name], dtype=torch.long).to(device)
                _, predicted = torch.max(outputs[name], 1)
                correct[name] += (predicted == target).sum().item()
                
                if name == 'engagement':  # 대표로 engagement만 저장
                    all_predictions.extend(predicted.cpu().numpy())
                    all_labels.extend(target.cpu().numpy())
            
            total += frames.size(0)
    
    # 결과 출력
    print("\n📊 Test Results:")
    print("-" * 30)
    
    avg_accuracy = 0
    for name in ['engagement', 'confusion', 'frustration', 'boredom']:
        acc = correct[name] / total * 100
        avg_accuracy += acc
        print(f"{name:12s}: {acc:6.2f}%")
    
    avg_accuracy /= 4
    print("-" * 30)
    print(f"Average     : {avg_accuracy:6.2f}%")
    
    # 혼동 행렬 (Engagement만)
    from sklearn.metrics import confusion_matrix
    cm = confusion_matrix(all_labels, all_predictions)
    print("\n🔍 Confusion Matrix (Engagement):")
    print("Predicted →")
    print("Actual ↓")
    print(cm)
    
    return avg_accuracy


if __name__ == "__main__":
    print("로컬 DAiSEE 데이터셋 학습")
    print("=" * 50)
    
    # 옵션 선택
    print("\n1. Quick test (10 samples)")
    print("2. Small training (100 samples)")
    print("3. Full training (all samples)")
    print("4. Test existing model")
    
    choice = input("\nSelect (1/2/3/4): ").strip()
    
    if choice == '1':
        model = train_local_daisee(num_epochs=2, batch_size=2, max_samples=10)
        # 학습 후 바로 테스트
        test_final_model(max_samples=10)
        
    elif choice == '2':
        model = train_local_daisee(num_epochs=5, batch_size=4, max_samples=100)
        test_final_model(max_samples=100)
        
    elif choice == '3':
        model = train_local_daisee(num_epochs=10, batch_size=8, max_samples=None)
        test_final_model()
        
    elif choice == '4':
        # 이미 학습된 모델만 테스트
        if os.path.exists('daisee_local_model.pth'):
            test_final_model(max_samples=100)
        else:
            print("❌ No saved model found. Train first!")
    else:
        print("Invalid choice")