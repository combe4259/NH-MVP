import cv2
import numpy as np
import time
from collections import deque
from text_gaze_analyzer import TextGazeAnalyzer

class ImprovedGazeTracker:
    def __init__(self):
        self.analyzer = TextGazeAnalyzer()
        self.h_scale = 200  # 더 큰 기본 수평 스케일
        self.v_scale = 120  # 더 큰 기본 수직 스케일
        self.offset_x = 0   # 수평 오프셋
        self.offset_y = 0   # 수직 오프셋
        self.smoothing_factor = 0.4
        self.gaze_history = deque(maxlen=5)  # 스무딩용 히스토리
        self.calibrated = False
        
    def smooth_gaze(self, x, y):
        """가우시안 가중치로 시선 스무딩"""
        self.gaze_history.append((x, y))
        
        if len(self.gaze_history) < 2:
            return x, y
        
        # 가우시안 가중치 적용
        weights = [0.1, 0.2, 0.3, 0.3, 0.1][-len(self.gaze_history):]
        total_weight = sum(weights)
        
        smoothed_x = sum(p[0] * w for p, w in zip(self.gaze_history, weights)) / total_weight
        smoothed_y = sum(p[1] * w for p, w in zip(self.gaze_history, weights)) / total_weight
        
        return int(smoothed_x), int(smoothed_y)
    
    def calculate_custom_gaze(self, landmarks, frame_shape):
        """개선된 시선 계산 알고리즘"""
        # 눈 중심과 홍채 위치 계산
        left_eye_center = self.analyzer.gaze_tracker.get_eye_center(
            landmarks, self.analyzer.gaze_tracker.LEFT_EYE_INDICES, frame_shape)
        right_eye_center = self.analyzer.gaze_tracker.get_eye_center(
            landmarks, self.analyzer.gaze_tracker.RIGHT_EYE_INDICES, frame_shape)
        
        left_iris = self.analyzer.gaze_tracker.get_iris_position(
            landmarks, self.analyzer.gaze_tracker.LEFT_IRIS_INDICES, frame_shape)
        right_iris = self.analyzer.gaze_tracker.get_iris_position(
            landmarks, self.analyzer.gaze_tracker.RIGHT_IRIS_INDICES, frame_shape)
        
        # 시선 벡터 계산
        left_gaze_vector = left_iris - left_eye_center
        right_gaze_vector = right_iris - right_eye_center
        avg_gaze_vector = (left_gaze_vector + right_gaze_vector) / 2
        
        # 머리 위치 기반 앵커 포인트 (얼굴 중앙)
        face_center_x = landmarks.landmark[9].x * frame_shape[1]  # 얼굴 중앙 랜드마크
        face_center_y = landmarks.landmark[9].y * frame_shape[0]
        
        # 머리 기울기 보정
        left_temple = landmarks.landmark[54].x * frame_shape[1]
        right_temple = landmarks.landmark[284].x * frame_shape[1]
        head_tilt = (right_temple - left_temple) / frame_shape[1]
        
        # 동적 스케일 조정 (머리가 가까우면 스케일 감소, 멀면 증가)
        eye_distance = np.linalg.norm(left_eye_center - right_eye_center)
        scale_factor = 150 / max(eye_distance, 50)  # 눈 간 거리 기반 스케일
        
        # 최종 시선 위치 계산 (좌우 반전 수정: 마이너스 부호 추가)
        gaze_x = face_center_x - avg_gaze_vector[0] * self.h_scale * scale_factor + self.offset_x
        gaze_y = face_center_y + avg_gaze_vector[1] * self.v_scale * scale_factor + self.offset_y
        
        # 스무딩 적용
        gaze_x, gaze_y = self.smooth_gaze(gaze_x, gaze_y)
        
        # 화면 경계 내로 제한
        gaze_x = np.clip(gaze_x, 0, frame_shape[1] - 1)
        gaze_y = np.clip(gaze_y, 0, frame_shape[0] - 1)
        
        return int(gaze_x), int(gaze_y), scale_factor

def main():
    tracker = ImprovedGazeTracker()
    
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS, 60)  # 더 높은 FPS
    
    cv2.namedWindow('Enhanced Gaze Tracker', cv2.WINDOW_NORMAL)
    cv2.namedWindow('Debug View', cv2.WINDOW_NORMAL)
    
    show_debug = True
    auto_adjust = True
    gaze_trail = deque(maxlen=30)
    
    print("=" * 60)
    print("ENHANCED TEXT GAZE TRACKER")
    print("=" * 60)
    print("Controls:")
    print("WASD - Manual offset adjustment")
    print("↑↓ - Vertical scale (+/- 10)")
    print("←→ - Horizontal scale (+/- 10)")
    print("R - Reset all settings")
    print("D - Toggle debug view")
    print("A - Toggle auto-adjustment")
    print("C - Clear trail")
    print("Q - Quit")
    print("=" * 60)
    
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame = cv2.flip(frame, 1)
        frame_count += 1
        
        # 얼굴 랜드마크 감지
        landmarks = tracker.analyzer.gaze_tracker.detect_eyes(frame)
        
        if landmarks:
            # 개선된 시선 계산
            gaze_x, gaze_y, scale_factor = tracker.calculate_custom_gaze(landmarks, frame.shape)
            
            # 시선 궤적 저장
            gaze_trail.append((gaze_x, gaze_y))
            
            # 시선 궤적 그리기
            for i in range(1, len(gaze_trail)):
                alpha = i / len(gaze_trail)
                thickness = max(1, int(3 * alpha))
                color = (0, int(255 * alpha), int(100 * (1-alpha)))
                cv2.line(frame, gaze_trail[i-1], gaze_trail[i], color, thickness)
            
            # 현재 시선 포인트 (크게 표시)
            cv2.circle(frame, (gaze_x, gaze_y), 20, (0, 255, 0), -1)
            cv2.circle(frame, (gaze_x, gaze_y), 25, (0, 255, 0), 3)
            
            # 십자선 표시
            cv2.line(frame, (gaze_x - 30, gaze_y), (gaze_x + 30, gaze_y), (0, 255, 0), 2)
            cv2.line(frame, (gaze_x, gaze_y - 30), (gaze_x, gaze_y + 30), (0, 255, 0), 2)
            
            if show_debug:
                # 디버그 정보 생성
                debug = frame.copy()
                
                # 눈 위치 표시
                left_eye = tracker.analyzer.gaze_tracker.get_eye_center(
                    landmarks, tracker.analyzer.gaze_tracker.LEFT_EYE_INDICES, frame.shape)
                right_eye = tracker.analyzer.gaze_tracker.get_eye_center(
                    landmarks, tracker.analyzer.gaze_tracker.RIGHT_EYE_INDICES, frame.shape)
                left_iris = tracker.analyzer.gaze_tracker.get_iris_position(
                    landmarks, tracker.analyzer.gaze_tracker.LEFT_IRIS_INDICES, frame.shape)
                right_iris = tracker.analyzer.gaze_tracker.get_iris_position(
                    landmarks, tracker.analyzer.gaze_tracker.RIGHT_IRIS_INDICES, frame.shape)
                
                # 눈 중심 (파란색)
                cv2.circle(debug, tuple(left_eye), 8, (255, 0, 0), -1)
                cv2.circle(debug, tuple(right_eye), 8, (255, 0, 0), -1)
                
                # 홍채 위치 (빨간색)
                cv2.circle(debug, tuple(left_iris), 5, (0, 0, 255), -1)
                cv2.circle(debug, tuple(right_iris), 5, (0, 0, 255), -1)
                
                # 시선 벡터 표시
                cv2.arrowedLine(debug, tuple(left_eye), tuple(left_iris), (0, 255, 255), 2)
                cv2.arrowedLine(debug, tuple(right_eye), tuple(right_iris), (0, 255, 255), 2)
                
                cv2.imshow('Debug View', debug)
        
        # 상태 정보 표시
        info_text = [
            f"FPS: {cv2.getTickFrequency() / (cv2.getTickCount() - 0):.1f}" if frame_count > 0 else "FPS: --",
            f"H-Scale: {tracker.h_scale} | V-Scale: {tracker.v_scale}",
            f"Offset: ({tracker.offset_x:+.0f}, {tracker.offset_y:+.0f})",
            f"Smoothing: {tracker.smoothing_factor:.2f}",
            f"Auto-Adjust: {'ON' if auto_adjust else 'OFF'}"
        ]
        
        y_pos = 30
        for text in info_text:
            cv2.putText(frame, text, (10, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(frame, text, (10, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
            y_pos += 25
        
        cv2.imshow('Enhanced Gaze Tracker', frame)
        
        # 키보드 입력 처리
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q'):
            break
        elif key == ord('w'):  # 위로 오프셋
            tracker.offset_y -= 20
            print(f"Offset Y: {tracker.offset_y}")
        elif key == ord('s'):  # 아래로 오프셋
            tracker.offset_y += 20
            print(f"Offset Y: {tracker.offset_y}")
        elif key == ord('a'):  # 왼쪽 오프셋
            tracker.offset_x -= 20
            print(f"Offset X: {tracker.offset_x}")
        elif key == ord('d'):  # 오른쪽 오프셋
            tracker.offset_x += 20
            print(f"Offset X: {tracker.offset_x}")
        elif key == 82:  # ↑ 키 (수직 스케일 증가)
            tracker.v_scale += 10
            print(f"V-Scale: {tracker.v_scale}")
        elif key == 84:  # ↓ 키 (수직 스케일 감소)
            tracker.v_scale = max(10, tracker.v_scale - 10)
            print(f"V-Scale: {tracker.v_scale}")
        elif key == 81:  # ← 키 (수평 스케일 감소)
            tracker.h_scale = max(10, tracker.h_scale - 10)
            print(f"H-Scale: {tracker.h_scale}")
        elif key == 83:  # → 키 (수평 스케일 증가)
            tracker.h_scale += 10
            print(f"H-Scale: {tracker.h_scale}")
        elif key == ord('r'):  # 리셋
            tracker.h_scale = 200
            tracker.v_scale = 120
            tracker.offset_x = 0
            tracker.offset_y = 0
            print("Settings reset to default")
        elif key == ord('D'):  # 디버그 토글
            show_debug = not show_debug
            if not show_debug:
                cv2.destroyWindow('Debug View')
        elif key == ord('A'):  # 자동 조정 토글
            auto_adjust = not auto_adjust
            print(f"Auto-adjust: {'ON' if auto_adjust else 'OFF'}")
        elif key == ord('c'):  # 궤적 클리어
            gaze_trail.clear()
            tracker.gaze_history.clear()
        elif key == ord('1'):  # 스무딩 감소
            tracker.smoothing_factor = max(0.1, tracker.smoothing_factor - 0.1)
            print(f"Smoothing: {tracker.smoothing_factor:.2f}")
        elif key == ord('2'):  # 스무딩 증가
            tracker.smoothing_factor = min(0.9, tracker.smoothing_factor + 0.1)
            print(f"Smoothing: {tracker.smoothing_factor:.2f}")
    
    cap.release()
    cv2.destroyAllWindows()
    
    print("\n" + "=" * 60)
    print("Session ended")
    print(f"Final settings:")
    print(f"  H-Scale: {tracker.h_scale}")
    print(f"  V-Scale: {tracker.v_scale}")
    print(f"  Offset: ({tracker.offset_x}, {tracker.offset_y})")
    print(f"  Smoothing: {tracker.smoothing_factor}")
    print("=" * 60)

if __name__ == "__main__":
    main()