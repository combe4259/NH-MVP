"""
실시간 DAiSEE 기반 얼굴 이해도 추적
웹캠에서 실시간으로 engagement, confusion, frustration, boredom 레벨 예측
"""

import cv2
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as models
import torchvision.transforms as transforms
import numpy as np
from collections import deque
import time
import os
import mediapipe as mp

# GPU 설정
if torch.cuda.is_available():
    device = torch.device("cuda")
elif torch.backends.mps.is_available():
    device = torch.device("mps")
else:
    device = torch.device("cpu")
print(f"Using device: {device}")


class DAiSEECNNLSTM(nn.Module):
    """CNN-LSTM 모델 """
    
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


class RealtimeDAiSEETracker:
    """실시간 DAiSEE 기반 추적기"""
    
    def __init__(self, model_path='daisee_local_model.pth', 
                 sequence_length=30, 
                 buffer_size=30,
                 prediction_interval=0.5):
        """
        Args:
            model_path: 학습된 모델 경로
            sequence_length: 모델에 입력할 프레임 수
            buffer_size: 버퍼 크기
            prediction_interval: 예측 주기 (초)
        """
        self.sequence_length = sequence_length
        self.buffer_size = buffer_size
        self.prediction_interval = prediction_interval
        
        # 프레임 버퍼 (deque로 자동으로 오래된 프레임 제거)
        self.frame_buffer = deque(maxlen=buffer_size)
        
        # 모델 로드
        print(f"Loading model from {model_path}...")
        self.model = DAiSEECNNLSTM().to(device)
        
        if os.path.exists(model_path):
            self.model.load_state_dict(torch.load(model_path, map_location=device))
            self.model.eval()
            print("✅ Model loaded successfully")
        else:
            print("⚠️ No trained model found. Using random initialization.")
        
        # 전처리 변환
        self.transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((112, 112)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                              std=[0.229, 0.224, 0.225])
        ])
        
        # MediaPipe 얼굴 감지 및 메시
        self.mp_face_detection = mp.solutions.face_detection
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        self.face_detection = self.mp_face_detection.FaceDetection(
            min_detection_confidence=0.5
        )
        
        # Face Mesh 추가 (랜드마크 표시용)
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # 마지막 예측 시간
        self.last_prediction_time = 0
        
        # 현재 예측 결과
        self.current_predictions = {
            'engagement': 0,
            'confusion': 0,
            'frustration': 0,
            'boredom': 0
        }
        
        # 감정 레벨 라벨
        self.level_labels = ['Very Low', 'Low', 'High', 'Very High']
    
    def preprocess_frame(self, frame):
        """프레임 전처리"""
        # BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 얼굴 감지 및 크롭 (선택적)
        results = self.face_detection.process(frame_rgb)
        
        if results.detections:
            detection = results.detections[0]
            bbox = detection.location_data.relative_bounding_box
            h, w = frame.shape[:2]
            
            # 바운딩 박스 계산 (여유 공간 추가)
            x1 = max(0, int((bbox.xmin - 0.1) * w))
            y1 = max(0, int((bbox.ymin - 0.1) * h))
            x2 = min(w, int((bbox.xmin + bbox.width + 0.1) * w))
            y2 = min(h, int((bbox.ymin + bbox.height + 0.1) * h))
            
            # 얼굴 영역 크롭
            face_crop = frame_rgb[y1:y2, x1:x2]
            
            # 크롭된 영역이 너무 작으면 전체 프레임 사용
            if face_crop.shape[0] > 50 and face_crop.shape[1] > 50:
                frame_rgb = face_crop
        
        # 텐서로 변환
        tensor = self.transform(frame_rgb)
        return tensor
    
    def add_frame(self, frame):
        """프레임을 버퍼에 추가"""
        processed = self.preprocess_frame(frame)
        self.frame_buffer.append(processed)
    
    def predict(self):
        """현재 버퍼의 프레임으로 예측"""
        if len(self.frame_buffer) < self.sequence_length:
            return None
        
        # 균등 간격으로 프레임 선택
        indices = np.linspace(0, len(self.frame_buffer)-1, 
                            self.sequence_length, dtype=int)
        
        # 선택된 프레임들을 텐서로 스택
        frames = torch.stack([self.frame_buffer[i] for i in indices])
        frames = frames.unsqueeze(0).to(device)  # 배치 차원 추가
        
        # 예측
        with torch.no_grad():
            outputs = self.model(frames)
        
        # 각 감정의 레벨 계산 (0-3)
        predictions = {}
        for emotion in ['engagement', 'confusion', 'frustration', 'boredom']:
            probs = F.softmax(outputs[emotion], dim=1)
            level = torch.argmax(probs, dim=1).item()
            confidence = probs[0, level].item()
            predictions[emotion] = {
                'level': level,
                'label': self.level_labels[level],
                'confidence': confidence
            }
        
        return predictions
    
    def process_frame(self, frame):
        """프레임 처리 및 예측"""
        # 프레임 버퍼에 추가
        self.add_frame(frame)
        
        # 예측 주기 확인
        current_time = time.time()
        if current_time - self.last_prediction_time >= self.prediction_interval:
            predictions = self.predict()
            if predictions:
                self.current_predictions = predictions
                self.last_prediction_time = current_time
        
        return self.current_predictions
    
    def draw_face_landmarks(self, frame):
        """얼굴 랜드마크 표시"""
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(frame_rgb)
        
        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                # 얼굴 메시 그리기
                self.mp_drawing.draw_landmarks(
                    frame,
                    face_landmarks,
                    self.mp_face_mesh.FACEMESH_CONTOURS,
                    landmark_drawing_spec=self.mp_drawing.DrawingSpec(
                        color=(0, 255, 0), thickness=1, circle_radius=1
                    ),
                    connection_drawing_spec=self.mp_drawing.DrawingSpec(
                        color=(0, 255, 0), thickness=1, circle_radius=1
                    )
                )
                
                # 주요 포인트 강조 (눈, 눈썹, 입)
                # 왼쪽 눈
                for idx in [33, 133, 157, 158, 159, 160, 161, 163]:
                    x = int(face_landmarks.landmark[idx].x * frame.shape[1])
                    y = int(face_landmarks.landmark[idx].y * frame.shape[0])
                    cv2.circle(frame, (x, y), 2, (0, 255, 255), -1)
                
                # 오른쪽 눈
                for idx in [362, 263, 387, 388, 389, 390, 391, 393]:
                    x = int(face_landmarks.landmark[idx].x * frame.shape[1])
                    y = int(face_landmarks.landmark[idx].y * frame.shape[0])
                    cv2.circle(frame, (x, y), 2, (0, 255, 255), -1)
                
                # 입
                for idx in [61, 291, 39, 269, 0, 17, 18, 200]:
                    x = int(face_landmarks.landmark[idx].x * frame.shape[1])
                    y = int(face_landmarks.landmark[idx].y * frame.shape[0])
                    cv2.circle(frame, (x, y), 2, (255, 0, 255), -1)
        
        return frame
    
    def draw_predictions(self, frame, predictions):
        """예측 결과를 프레임에 표시"""
        # 먼저 얼굴 랜드마크 그리기
        frame = self.draw_face_landmarks(frame)
        
        if not predictions:
            return frame
        
        # 배경 박스 (반투명)
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, 10), (350, 180), (0, 0, 0), -1)
        frame = cv2.addWeighted(frame, 0.7, overlay, 0.3, 0)
        
        # 타이틀
        cv2.putText(frame, "DAiSEE Emotion Analysis", 
                   (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # 각 감정 표시
        y_offset = 65
        colors = {
            'engagement': (0, 255, 0),   # 녹색
            'confusion': (0, 165, 255),   # 주황색
            'frustration': (0, 0, 255),   # 빨간색
            'boredom': (255, 0, 255)      # 보라색
        }
        
        for emotion, color in colors.items():
            if emotion in predictions and predictions[emotion]:
                pred = predictions[emotion]
                text = f"{emotion.capitalize()}: {pred['label']}"
                confidence = f"({pred['confidence']*100:.1f}%)"
                
                # 감정 이름과 레벨
                cv2.putText(frame, text, 
                           (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 
                           0.5, color, 1)
                
                # 신뢰도
                cv2.putText(frame, confidence, 
                           (220, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 
                           0.4, color, 1)
                
                # 레벨 바
                bar_width = int(pred['level'] * 25 + 25)  # 0-3 -> 25-100
                cv2.rectangle(frame, (280, y_offset-10), 
                            (280 + bar_width, y_offset), 
                            color, -1)
                
                y_offset += 30
        
        # FPS 및 버퍼 상태
        buffer_fill = len(self.frame_buffer)
        cv2.putText(frame, f"Buffer: {buffer_fill}/{self.buffer_size}", 
                   (20, 160), cv2.FONT_HERSHEY_SIMPLEX, 
                   0.4, (200, 200, 200), 1)
        
        return frame


def main():
    """메인 실행 함수"""
    
    print("=" * 50)
    print("🎥 Realtime DAiSEE Emotion Tracker")
    print("=" * 50)
    
    # 트래커 초기화
    tracker = RealtimeDAiSEETracker(
        model_path='daisee_local_model.pth',
        sequence_length=30,
        buffer_size=30,
        prediction_interval=0.5  # 0.5초마다 예측
    )
    
    # 웹캠 시작
    cap = cv2.VideoCapture(0)
    
    # FPS 계산용
    fps_time = time.time()
    fps_counter = 0
    current_fps = 0
    
    print("\n📸 Camera started")
    print("Press 'q' to quit")
    print("\nCollecting frames for initial prediction...")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # FPS 계산
        fps_counter += 1
        if time.time() - fps_time >= 1.0:
            current_fps = fps_counter
            fps_counter = 0
            fps_time = time.time()
        
        # 프레임 처리 및 예측
        predictions = tracker.process_frame(frame)
        
        # 예측 결과 표시
        frame = tracker.draw_predictions(frame, predictions)
        
        # FPS 표시
        cv2.putText(frame, f"FPS: {current_fps}", 
                   (frame.shape[1] - 100, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # 프레임 표시
        cv2.imshow('DAiSEE Realtime Tracker', frame)
        
        # 'q' 키로 종료
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    print("\n✅ Tracker stopped")


if __name__ == "__main__":
    main()