"""
YOLO Detection Logic for Wildlife Monitoring System
Handles object detection for humans and vehicles using YOLOv8
"""

import os
os.environ['TORCH_WEIGHTS_ONLY'] = '0'  # Allow unsafe loading for YOLO

import cv2
import numpy as np
import torch

# Monkey patch torch.load to use weights_only=False
_original_load = torch.load
def _patched_load(*args, **kwargs):
    kwargs.setdefault('weights_only', False)
    return _original_load(*args, **kwargs)
torch.load = _patched_load

from ultralytics import YOLO
import config
from typing import List, Tuple, Dict

# Global model instance
model = None

def load_model():
    """Load the YOLO model (downloads if not present)"""
    global model
    if model is None:
        print(f"Loading YOLO model: {config.YOLO_MODEL}...")
        model = YOLO(config.YOLO_MODEL)
        print("✓ YOLO model loaded successfully")
    return model

def detect_objects(frame: np.ndarray) -> Tuple[np.ndarray, List[Dict]]:
    """
    Detect objects in a frame using YOLO
    
    Args:
        frame: Input image frame (BGR format from OpenCV)
    
    Returns:
        Tuple of (annotated_frame, detections_list)
        - annotated_frame: Frame with bounding boxes drawn
        - detections_list: List of detection dictionaries
    """
    global model
    if model is None:
        model = load_model()
    
    # Run YOLO detection
    results = model(frame, conf=config.CONFIDENCE_THRESHOLD, verbose=False)
    
    detections = []
    annotated_frame = frame.copy()
    
    # Process each detection
    for result in results:
        boxes = result.boxes
        for box in boxes:
            # Get box coordinates
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            
            # Get class name and confidence
            class_id = int(box.cls[0])
            class_name = model.names[class_id]
            confidence = float(box.conf[0])
            
            # Only process if it's a target class
            if class_name in config.DETECTION_CLASSES:
                # Add to detections list
                detections.append({
                    'class': class_name,
                    'confidence': confidence,
                    'bbox': [x1, y1, x2, y2]
                })
                
                # Draw bounding box with different colors
                if class_name == "person":
                    color = (0, 0, 255)  # Red for person
                elif class_name in getattr(config, 'ANIMAL_CLASSES', []):
                    color = (255, 0, 255)  # Magenta/Pink for animals
                else:
                    color = (0, 255, 255)  # Yellow for vehicles
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 3)
                
                # Draw label with background
                label = f"{class_name}: {confidence:.2f}"
                label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
                cv2.rectangle(annotated_frame, (x1, y1 - label_size[1] - 10), 
                            (x1 + label_size[0], y1), color, -1)
                cv2.putText(annotated_frame, label, (x1, y1 - 5), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    return annotated_frame, detections

def is_threat_detected(detections: List[Dict]) -> bool:
    """
    Check if any detections constitute a threat
    
    Args:
        detections: List of detection dictionaries
    
    Returns:
        True if threat detected, False otherwise
    """
    return len(detections) > 0

def get_highest_confidence_detection(detections: List[Dict]) -> Dict:
    """
    Get the detection with highest confidence
    
    Args:
        detections: List of detection dictionaries
    
    Returns:
        Detection dictionary with highest confidence, or None if empty
    """
    if not detections:
        return None
    
    return max(detections, key=lambda x: x['confidence'])

def format_detection_summary(detections: List[Dict]) -> str:
    """
    Create a human-readable summary of detections
    
    Args:
        detections: List of detection dictionaries
    
    Returns:
        Formatted string summary
    """
    if not detections:
        return "No threats detected"
    
    # Count by class
    class_counts = {}
    for det in detections:
        class_name = det['class']
        class_counts[class_name] = class_counts.get(class_name, 0) + 1
    
    # Format summary
    parts = []
    for class_name, count in class_counts.items():
        parts.append(f"{count} {class_name}{'s' if count > 1 else ''}")
    
    return "Detected: " + ", ".join(parts)

def calculate_severity_level(detections: List[Dict]) -> Dict:
    """
    Calculate alert severity level based on quantity and type of detections
    
    Severity Levels:
    - LOW: 1 person OR 1 vehicle
    - MEDIUM: 2-3 persons OR 2-3 vehicles OR mixed (person + vehicle)
    - HIGH: 4+ persons OR 4+ vehicles OR 2+ persons with vehicles
    - CRITICAL: 5+ persons OR multiple vehicles with persons
    
    Args:
        detections: List of detection dictionaries
    
    Returns:
        Dictionary with severity info: {level, score, color, description}
    """
    if not detections:
        return {
            'level': 'NONE',
            'score': 0,
            'color': '#8b949e',
            'description': 'No threats detected'
        }
    
    # Count by class type
    person_count = 0
    vehicle_count = 0
    other_count = 0
    
    vehicle_types = ['car', 'truck', 'bus', 'motorcycle']
    
    for det in detections:
        class_name = det['class'].lower()
        if class_name == 'person':
            person_count += 1
        elif class_name in vehicle_types:
            vehicle_count += 1
        else:
            other_count += 1
    
    total_count = person_count + vehicle_count + other_count
    
    # Calculate severity score (0-100)
    severity_score = 0
    severity_score += person_count * 25  # Each person adds 25 points
    severity_score += vehicle_count * 15  # Each vehicle adds 15 points
    severity_score += other_count * 10    # Other threats add 10 points
    
    # Bonus for mixed threats (person + vehicle = more suspicious)
    if person_count > 0 and vehicle_count > 0:
        severity_score += 20
    
    # Cap at 100
    severity_score = min(severity_score, 100)
    
    # Determine level based on score and counts
    if severity_score >= 75 or person_count >= 4 or (person_count >= 2 and vehicle_count >= 1):
        level = 'CRITICAL'
        color = '#ff0000'
        description = f'🔴 CRITICAL THREAT: {person_count} person(s), {vehicle_count} vehicle(s)'
    elif severity_score >= 50 or person_count >= 2 or vehicle_count >= 2 or (person_count >= 1 and vehicle_count >= 1):
        level = 'HIGH'
        color = '#da3633'
        description = f'🟠 HIGH ALERT: {person_count} person(s), {vehicle_count} vehicle(s)'
    elif severity_score >= 25 or total_count >= 2:
        level = 'MEDIUM'
        color = '#f0883e'
        description = f'🟡 MEDIUM ALERT: {total_count} threat(s) detected'
    else:
        level = 'LOW'
        color = '#58a6ff'
        description = f'🔵 LOW ALERT: {total_count} threat detected'
    
    return {
        'level': level,
        'score': severity_score,
        'color': color,
        'description': description,
        'person_count': person_count,
        'vehicle_count': vehicle_count,
        'total_count': total_count
    }

def draw_alert_banner(frame: np.ndarray, message: str, detections: List[Dict] = None) -> np.ndarray:
    """
    Draw a colored alert banner on the frame based on severity level
    
    Args:
        frame: Input frame
        message: Alert message to display
        detections: List of detections for severity calculation
    
    Returns:
        Frame with alert banner
    """
    height, width = frame.shape[:2]
    
    # Calculate severity if detections provided
    severity = calculate_severity_level(detections) if detections else {'level': 'HIGH', 'color': '#da3633'}
    
    # Color mapping (BGR format for OpenCV)
    color_map = {
        'CRITICAL': (0, 0, 255),      # Red
        'HIGH': (51, 54, 218),         # Dark red/orange
        'MEDIUM': (62, 136, 240),      # Orange
        'LOW': (255, 166, 88),         # Blue
        'NONE': (158, 148, 139)        # Gray
    }
    
    banner_color = color_map.get(severity['level'], (0, 0, 255))
    
    # Draw colored banner at top
    cv2.rectangle(frame, (0, 0), (width, 80), banner_color, -1)
    
    # Draw severity level badge
    severity_text = f"[{severity['level']}]"
    
    # Draw alert text (using FONT_HERSHEY_DUPLEX for bold-like appearance)
    cv2.putText(frame, f"! THREAT DETECTED {severity_text} !", (20, 35), 
                cv2.FONT_HERSHEY_DUPLEX, 1.0, (255, 255, 255), 2)
    cv2.putText(frame, message, (20, 65), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    return frame

# Test function
if __name__ == "__main__":
    print("Testing YOLO detection...")
    load_model()
    print("Model loaded successfully!")
    
    # Test with a sample image (if available)
    import os
    if os.path.exists("test_image.jpg"):
        img = cv2.imread("test_image.jpg")
        annotated, detections = detect_objects(img)
        print(f"Detections: {detections}")
        cv2.imshow("Detection Test", annotated)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
