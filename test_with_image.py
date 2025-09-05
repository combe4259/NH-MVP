import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from text_gaze_analyzer import TextGazeAnalyzer

def create_sample_text_image():
    width, height = 1280, 720
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    try:
        font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 48)
        font_medium = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 32)
        font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
    except:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    draw.text((100, 50), "Text Gaze Tracking Demo", font=font_large, fill='black')
    
    sample_text = [
        "Eye tracking technology enables computers to understand",
        "where users are looking on the screen. This powerful",
        "capability has applications in user experience research,",
        "accessibility tools, and reading comprehension studies.",
        "",
        "By analyzing fixation patterns and gaze paths, we can",
        "gain insights into cognitive processes and attention.",
        "The system tracks eye movements in real-time using",
        "computer vision and machine learning algorithms.",
        "",
        "Key metrics include fixation duration, saccade velocity,",
        "regression count, and reading speed measurement."
    ]
    
    y_offset = 150
    for line in sample_text:
        draw.text((100, y_offset), line, font=font_medium, fill='black')
        y_offset += 45
    
    draw.text((100, 600), "Instructions: Look at different parts of the text", 
              font=font_small, fill='blue')
    draw.text((100, 630), "Press 'q' to quit, 'h' for heatmap, 's' to save", 
              font=font_small, fill='blue')
    
    return np.array(img)

def test_with_static_image():
    analyzer = TextGazeAnalyzer()
    
    text_image = create_sample_text_image()
    
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    cv2.namedWindow('Camera Feed', cv2.WINDOW_NORMAL)
    cv2.namedWindow('Text Display', cv2.WINDOW_NORMAL)
    cv2.namedWindow('Combined View', cv2.WINDOW_NORMAL)
    
    print("=" * 60)
    print("TEXT GAZE TRACKER - Static Text Test")
    print("=" * 60)
    print("Position the text display on a second monitor or")
    print("print it out and place it near your camera.")
    print("The system will track your eye movements as you read.")
    print("=" * 60)
    
    show_heatmap = False
    gaze_trail = []
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame = cv2.flip(frame, 1)
        
        gaze_data = analyzer.gaze_tracker.process_frame(frame)
        
        display_image = text_image.copy()
        
        if gaze_data:
            is_fixation = analyzer.detect_fixation(gaze_data)
            
            gaze_trail.append((int(gaze_data.x), int(gaze_data.y)))
            if len(gaze_trail) > 50:
                gaze_trail.pop(0)
            
            for i in range(1, len(gaze_trail)):
                alpha = i / len(gaze_trail)
                cv2.line(display_image, gaze_trail[i-1], gaze_trail[i], 
                        (0, int(255 * alpha), 0), max(1, int(3 * alpha)))
            
            cv2.circle(display_image, (int(gaze_data.x), int(gaze_data.y)), 
                      15, (0, 255, 0), -1)
            cv2.circle(display_image, (int(gaze_data.x), int(gaze_data.y)), 
                      20, (0, 255, 0), 2)
            
            if is_fixation:
                cv2.circle(display_image, (int(gaze_data.x), int(gaze_data.y)), 
                          25, (255, 0, 0), 2)
            
            analyzer.gaze_tracker.draw_gaze(frame, gaze_data)
            
            text_regions = analyzer.text_detector.detect_text_regions(display_image)
            if text_regions:
                current_region = analyzer.text_detector.get_region_at_point(
                    int(gaze_data.x), int(gaze_data.y)
                )
                
                if current_region:
                    x, y, w, h = current_region.bbox
                    cv2.rectangle(display_image, (x, y), (x + w, y + h), 
                                (255, 255, 0), 2)
                    
                    if is_fixation:
                        analyzer.track_word_sequence(current_region)
        
        metrics = analyzer.calculate_reading_metrics()
        
        info_text = [
            f"Fixations: {metrics.total_fixations}",
            f"Words: {len(metrics.words_read)}",
            f"Pattern: {metrics.reading_pattern}"
        ]
        
        y_pos = 30
        for text in info_text:
            cv2.putText(frame, text, (10, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            y_pos += 30
        
        combined = np.hstack([frame, display_image])
        combined = cv2.resize(combined, (1920, 540))
        
        cv2.imshow('Camera Feed', frame)
        cv2.imshow('Text Display', display_image)
        cv2.imshow('Combined View', combined)
        
        if show_heatmap and len(analyzer.fixation_buffer) > 0:
            heatmap = analyzer.create_reading_heatmap(display_image.shape)
            blended = cv2.addWeighted(display_image, 0.7, heatmap, 0.3, 0)
            cv2.imshow('Reading Heatmap', blended)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('h'):
            show_heatmap = not show_heatmap
            if not show_heatmap:
                cv2.destroyWindow('Reading Heatmap')
        elif key == ord('s'):
            analyzer.save_session_data("test_session.json")
            cv2.imwrite("test_display.png", display_image)
            print("Session saved!")
        elif key == ord('c'):
            analyzer.fixation_buffer.clear()
            analyzer.word_sequence.clear()
            gaze_trail.clear()
            print("Cleared!")
    
    cap.release()
    cv2.destroyAllWindows()
    
    print("\n" + "=" * 60)
    print("Session Complete!")
    if analyzer.word_sequence:
        print(f"Words detected: {' '.join(analyzer.word_sequence[:20])}")
    print("=" * 60)

if __name__ == "__main__":
    test_with_static_image()