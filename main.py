import cv2
import numpy as np
import time
from text_gaze_analyzer import TextGazeAnalyzer

def main():
    analyzer = TextGazeAnalyzer()
    
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    cv2.namedWindow('Text Gaze Tracker', cv2.WINDOW_NORMAL)
    cv2.namedWindow('Reading Heatmap', cv2.WINDOW_NORMAL)
    cv2.namedWindow('Metrics Dashboard', cv2.WINDOW_NORMAL)
    
    show_text_regions = True
    show_heatmap = False
    recording = False
    
    print("=" * 60)
    print("TEXT GAZE TRACKER - Controls:")
    print("=" * 60)
    print("'q' - Quit")
    print("'t' - Toggle text region display")
    print("'h' - Toggle heatmap display")
    print("'r' - Start/stop recording")
    print("'s' - Save session data")
    print("'c' - Clear buffers")
    print("=" * 60)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame = cv2.flip(frame, 1)
        
        gaze_data = analyzer.gaze_tracker.process_frame(frame)
        
        if gaze_data:
            is_fixation = analyzer.detect_fixation(gaze_data)
            
            text_regions = analyzer.text_detector.detect_text_regions(frame)
            
            if text_regions:
                current_region = analyzer.text_detector.get_region_at_point(
                    int(gaze_data.x), int(gaze_data.y)
                )
                
                if current_region and is_fixation:
                    analyzer.track_word_sequence(current_region)
            
            analyzer.gaze_tracker.draw_gaze(frame, gaze_data)
            
            if is_fixation:
                cv2.putText(frame, "FIXATION", (50, 50), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        if show_text_regions:
            frame = analyzer.text_detector.create_text_overlay(frame, True)
        
        metrics = analyzer.calculate_reading_metrics()
        metrics_display = create_metrics_display(metrics, frame.shape)
        
        cv2.imshow('Text Gaze Tracker', frame)
        cv2.imshow('Metrics Dashboard', metrics_display)
        
        if show_heatmap and len(analyzer.fixation_buffer) > 0:
            heatmap = analyzer.create_reading_heatmap(frame.shape)
            blended = cv2.addWeighted(frame, 0.7, heatmap, 0.3, 0)
            cv2.imshow('Reading Heatmap', blended)
        
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q'):
            break
        elif key == ord('t'):
            show_text_regions = not show_text_regions
            print(f"Text regions: {'ON' if show_text_regions else 'OFF'}")
        elif key == ord('h'):
            show_heatmap = not show_heatmap
            print(f"Heatmap: {'ON' if show_heatmap else 'OFF'}")
        elif key == ord('r'):
            recording = not recording
            print(f"Recording: {'ON' if recording else 'OFF'}")
        elif key == ord('s'):
            analyzer.save_session_data()
            print("Session data saved!")
        elif key == ord('c'):
            analyzer.fixation_buffer.clear()
            analyzer.word_sequence.clear()
            analyzer.regression_count = 0
            print("Buffers cleared!")
    
    cap.release()
    cv2.destroyAllWindows()
    
    print("\n" + "=" * 60)
    print("FINAL READING METRICS:")
    print("=" * 60)
    final_metrics = analyzer.calculate_reading_metrics()
    print(f"Total Fixations: {final_metrics.total_fixations}")
    print(f"Average Fixation Duration: {final_metrics.avg_fixation_duration:.2f}s")
    print(f"Words Read: {len(final_metrics.words_read)}")
    print(f"Reading Speed: {final_metrics.reading_speed_wpm:.1f} WPM")
    print(f"Regressions: {final_metrics.regression_count}")
    print(f"Reading Pattern: {final_metrics.reading_pattern}")
    print("=" * 60)

def create_metrics_display(metrics, frame_shape):
    display = np.zeros((300, 600, 3), dtype=np.uint8)
    display.fill(40)
    
    cv2.putText(display, "READING METRICS", (200, 40), 
               cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    y_offset = 80
    line_height = 35
    
    metrics_text = [
        f"Fixations: {metrics.total_fixations}",
        f"Avg Duration: {metrics.avg_fixation_duration:.2f}s",
        f"Words Read: {len(metrics.words_read)}",
        f"Speed: {metrics.reading_speed_wpm:.1f} WPM",
        f"Regressions: {metrics.regression_count}",
        f"Pattern: {metrics.reading_pattern}"
    ]
    
    for text in metrics_text:
        cv2.putText(display, text, (30, y_offset), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 1)
        y_offset += line_height
    
    if metrics.total_fixations > 0:
        bar_width = min(int(metrics.reading_speed_wpm * 2), 500)
        cv2.rectangle(display, (30, 260), (30 + bar_width, 280), 
                     (0, 255, 0), -1)
        cv2.putText(display, "Reading Speed", (30, 255), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    
    return display

if __name__ == "__main__":
    main()