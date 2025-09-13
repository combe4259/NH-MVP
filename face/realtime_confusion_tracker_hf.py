"""
실시간 Confusion Binary 추적기 - HuggingFace 버전
Confusion 이진 분류 모델 사용 (Confused vs Not Confused)
"""

import cv2
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.transforms as transforms
import numpy as np
from collections import deque
import time
import os
import mediapipe as mp
from huggingface_hub import hf_hub_download

# GPU 설정
if torch.cuda.is_available():
    device = torch.device("cuda")
elif torch.backends.mps.is_available():
    device = torch.device("mps")
else:
    device = torch.device("cpu")
print(f"Using device: {device}")


class RealtimeConfusionTrackerHF:
    """실시간 Confusion 이진 분류 추적기"""
    
    def __init__(self, 
                 repo_id='combe4259/face-comprehension',
                 sequence_length=30, 
                 buffer_size=30,
                 prediction_interval=0.5,
                 cache_dir='./model_cache'):
        """
        Args:
            repo_id: HuggingFace 모델 레포지토리 ID
            sequence_length: 모델에 입력할 프레임 수
            buffer_size: 버퍼 크기
            prediction_interval: 예측 주기 (초)
            cache_dir: 모델 캐시 디렉토리
        """
        self.sequence_length = sequence_length
        self.buffer_size = buffer_size
        self.prediction_interval = prediction_interval
        self.repo_id = repo_id
        
        # 프레임 버퍼
        self.frame_buffer = deque(maxlen=buffer_size)
        
        # HuggingFace에서 모델 다운로드 및 로드
        print(f"📥 Downloading Confusion Binary model from: {repo_id}")
        try:
            # 모델 파일 다운로드
            model_path = hf_hub_download(
                repo_id=repo_id,
                filename="pytorch_model.bin",
                cache_dir=cache_dir
            )
            print(f"✅ Model downloaded to: {model_path}")
            
            # 모델 로드 (전체 모델이 저장된 경우)
            print("Loading Confusion Binary model...")
            self.model = torch.load(model_path, map_location=device)
            self.model.to(device)
            self.model.eval()
            print("✅ Confusion Binary model loaded successfully")
            
        except Exception as e:
            print(f"❌ Failed to load model: {e}")
            raise e
        
        # 전처리 변환
        self.transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((112, 112)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                              std=[0.229, 0.224, 0.225])
        ])
        
        # MediaPipe 얼굴 감지
        self.mp_face_detection = mp.solutions.face_detection
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_drawing = mp.solutions.drawing_utils
        
        self.face_detection = self.mp_face_detection.FaceDetection(
            min_detection_confidence=0.5
        )
        
        # Face Mesh (옵션)
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # 상태 변수
        self.last_prediction_time = 0
        self.current_confusion_state = "Unknown"
        self.confusion_probability = 0.0
        
        # 색상 정의
        self.color_not_confused = (0, 255, 0)  # 초록색
        self.color_confused = (0, 0, 255)  # 빨간색
        self.color_neutral = (255, 255, 0)  # 노란색
    
    def predict_confusion(self, frames):
        """Confusion 상태 예측 (이진 분류)"""
        if len(frames) < self.sequence_length:
            return None
        
        # 프레임 준비
        processed_frames = []
        for frame in frames[-self.sequence_length:]:
            processed = self.transform(frame)
            processed_frames.append(processed)
        
        # 배치 생성
        batch = torch.stack(processed_frames).unsqueeze(0).to(device)
        
        # 예측
        with torch.no_grad():
            outputs = self.model(batch)
            probabilities = F.softmax(outputs, dim=1)
            
            # 클래스 0: Not Confused, 클래스 1: Confused
            not_confused_prob = probabilities[0, 0].item()
            confused_prob = probabilities[0, 1].item()
            
            # 예측 클래스
            predicted_class = torch.argmax(probabilities, dim=1).item()
        
        # 결과 저장
        result = {
            'confused': predicted_class == 1,
            'probability': confused_prob,
            'not_confused_probability': not_confused_prob,
            'state': 'Confused' if predicted_class == 1 else 'Not Confused'
        }
        
        return result
    
    def process_frame(self, frame):
        """프레임 처리 및 예측"""
        current_time = time.time()
        
        # 얼굴 감지
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_detection.process(frame_rgb)
        
        if results.detections:
            for detection in results.detections:
                # 바운딩 박스 가져오기
                bbox = detection.location_data.relative_bounding_box
                h, w, _ = frame.shape
                x = int(bbox.xmin * w)
                y = int(bbox.ymin * h)
                width = int(bbox.width * w)
                height = int(bbox.height * h)
                
                # 얼굴 영역 추출
                face_roi = frame[max(0, y):min(h, y+height), 
                                max(0, x):min(w, x+width)]
                
                if face_roi.size > 0:
                    # 버퍼에 추가
                    face_rgb = cv2.cvtColor(face_roi, cv2.COLOR_BGR2RGB)
                    self.frame_buffer.append(face_rgb)
                    
                    # 예측 (주기적으로)
                    if current_time - self.last_prediction_time > self.prediction_interval:
                        if len(self.frame_buffer) >= self.sequence_length:
                            prediction = self.predict_confusion(list(self.frame_buffer))
                            if prediction:
                                self.current_confusion_state = prediction['state']
                                self.confusion_probability = prediction['probability']
                                self.last_prediction_time = current_time
                
                # 시각화
                self.visualize_results(frame, x, y, width, height)
        
        return frame
    
    def visualize_results(self, frame, x, y, width, height):
        """결과 시각화"""
        # 색상 결정
        if self.current_confusion_state == "Confused":
            box_color = self.color_confused
        elif self.current_confusion_state == "Not Confused":
            box_color = self.color_not_confused
        else:
            box_color = self.color_neutral
        
        # 바운딩 박스
        cv2.rectangle(frame, (x, y), (x+width, y+height), box_color, 2)
        
        # 상태 텍스트
        status_text = f"{self.current_confusion_state}"
        prob_text = f"Confusion: {self.confusion_probability:.1%}"
        
        # 배경 박스
        cv2.rectangle(frame, (x, y-50), (x+300, y), (0, 0, 0), -1)
        
        # 텍스트
        cv2.putText(frame, status_text, (x+5, y-30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, box_color, 2)
        cv2.putText(frame, prob_text, (x+5, y-10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        
        # 프로그레스 바
        bar_width = 200
        bar_height = 10
        bar_x = x
        bar_y = y + height + 10
        
        # 배경
        cv2.rectangle(frame, (bar_x, bar_y), 
                     (bar_x + bar_width, bar_y + bar_height), 
                     (100, 100, 100), -1)
        
        # Confusion 레벨
        fill_width = int(bar_width * self.confusion_probability)
        cv2.rectangle(frame, (bar_x, bar_y), 
                     (bar_x + fill_width, bar_y + bar_height), 
                     box_color, -1)
    
    def run(self):
        """실시간 추적 실행"""
        print("\n🎥 Starting Confusion Tracker...")
        print("Press 'q' to quit, 'r' to reset")
        print("-" * 50)
        
        cap = cv2.VideoCapture(0)
        
        # 카메라 설정
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        
        fps_counter = 0
        fps_time = time.time()
        fps = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # 프레임 처리
            frame = self.process_frame(frame)
            
            # FPS 계산
            fps_counter += 1
            if time.time() - fps_time > 1.0:
                fps = fps_counter
                fps_counter = 0
                fps_time = time.time()
            
            # FPS 표시
            cv2.putText(frame, f"FPS: {fps}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
            
            # 모델 정보 표시
            cv2.putText(frame, f"Model: Confusion Binary", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            
            # 화면 표시
            cv2.imshow('Confusion Tracker', frame)
            
            # 키 입력 처리
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                self.current_confusion_state = "Unknown"
                self.confusion_probability = 0.0
                print("Reset confusion state")
        
        cap.release()
        cv2.destroyAllWindows()
        print("\n✅ Confusion Tracker stopped")


if __name__ == "__main__":
    # 실행
    tracker = RealtimeConfusionTrackerHF(
        repo_id='combe4259/face-comprehension',  # HuggingFace 레포지토리
        sequence_length=30,
        buffer_size=30,
        prediction_interval=0.5  # 0.5초마다 예측
    )
    tracker.run()