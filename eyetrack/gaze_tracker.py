import cv2
import mediapipe as mp
import numpy as np
from dataclasses import dataclass
from typing import Tuple, Optional

@dataclass
class GazeData:
    x: float
    y: float
    timestamp: float
    confidence: float

class EyeGazeTracker:
    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        self.LEFT_EYE_INDICES = [33, 160, 158, 133, 153, 144]
        self.RIGHT_EYE_INDICES = [362, 385, 387, 263, 373, 380]
        self.LEFT_IRIS_INDICES = [468, 469, 470, 471, 472]
        self.RIGHT_IRIS_INDICES = [473, 474, 475, 476, 477]
        
        self.calibration_points = []
        self.is_calibrated = False
        
    def detect_eyes(self, frame):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)
        
        if results.multi_face_landmarks:
            return results.multi_face_landmarks[0]
        return None
    
    def get_eye_center(self, landmarks, indices, frame_shape):
        h, w = frame_shape[:2]
        points = []
        for idx in indices:
            x = int(landmarks.landmark[idx].x * w)
            y = int(landmarks.landmark[idx].y * h)
            points.append([x, y])
        
        points = np.array(points)
        center = np.mean(points, axis=0).astype(int)
        return center
    
    def get_iris_position(self, landmarks, iris_indices, frame_shape):
        h, w = frame_shape[:2]
        iris_points = []
        
        for idx in iris_indices:
            x = int(landmarks.landmark[idx].x * w)
            y = int(landmarks.landmark[idx].y * h)
            iris_points.append([x, y])
        
        iris_center = np.mean(iris_points, axis=0).astype(int)
        return iris_center
    
    def calculate_gaze_direction(self, landmarks, frame_shape):
        left_eye_center = self.get_eye_center(landmarks, self.LEFT_EYE_INDICES, frame_shape)
        right_eye_center = self.get_eye_center(landmarks, self.RIGHT_EYE_INDICES, frame_shape)
        
        left_iris = self.get_iris_position(landmarks, self.LEFT_IRIS_INDICES, frame_shape)
        right_iris = self.get_iris_position(landmarks, self.RIGHT_IRIS_INDICES, frame_shape)
        
        left_gaze_vector = left_iris - left_eye_center
        right_gaze_vector = right_iris - right_eye_center
        
        avg_gaze_vector = (left_gaze_vector + right_gaze_vector) / 2
        
        # 스케일링 팩터 대폭 증가 (30 -> 100)
        # 머리 위치에 따른 오프셋도 추가
        nose_tip = landmarks.landmark[1]
        nose_x = nose_tip.x * frame_shape[1]
        nose_y = nose_tip.y * frame_shape[0]
        
        # 화면 중심 대신 코 위치 기준으로 계산
        # 수평 움직임은 더 크게, 수직 움직임은 약간 작게
        # 좌우 반전 수정: x에 마이너스 부호 추가
        screen_x = nose_x - avg_gaze_vector[0] * 150  # 수평 민감도 증가 (반전)
        screen_y = nose_y + avg_gaze_vector[1] * 80   # 수직 민감도
        
        screen_x = np.clip(screen_x, 0, frame_shape[1])
        screen_y = np.clip(screen_y, 0, frame_shape[0])
        
        return int(screen_x), int(screen_y)
    
    def calibrate(self, point_x, point_y, gaze_x, gaze_y):
        self.calibration_points.append({
            'screen': (point_x, point_y),
            'gaze': (gaze_x, gaze_y)
        })
        
        if len(self.calibration_points) >= 9:
            self.is_calibrated = True
            self._calculate_calibration_matrix()
    
    def _calculate_calibration_matrix(self):
        pass
    
    def process_frame(self, frame) -> Optional[GazeData]:
        landmarks = self.detect_eyes(frame)
        
        if landmarks:
            gaze_x, gaze_y = self.calculate_gaze_direction(landmarks, frame.shape)
            
            return GazeData(
                x=gaze_x,
                y=gaze_y,
                timestamp=cv2.getTickCount() / cv2.getTickFrequency(),
                confidence=0.8
            )
        
        return None
    
    def draw_gaze(self, frame, gaze_data: GazeData):
        if gaze_data:
            cv2.circle(frame, (int(gaze_data.x), int(gaze_data.y)), 10, (0, 255, 0), -1)
            cv2.circle(frame, (int(gaze_data.x), int(gaze_data.y)), 15, (0, 255, 0), 2)
        
        return frame