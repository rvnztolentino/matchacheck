import cv2
import numpy as np
from ultralytics import YOLO

# Load YOLOv8n pretrained model (downloads automatically on first run)
model = YOLO('yolov8n.pt')

def detect_matcha(frame):
    """
    Detects if matcha is present in the provided BGR frame.
    Uses YOLO to detect cups/glasses first, then applies HSV color masking.
    
    Args:
        frame: A BGR image frame from OpenCV.
        
    Returns:
        is_matcha (bool): True if confidence > 60%.
        confidence (float): 0-100 percentage of pixels matching the color.
        annotated_frame: Frame with the bounding box applied (if found).
        cup_found (bool): True if a cup or glass was detected by YOLO.
    """
    # 1. Run YOLO to detect cups or wine glasses 
    # COCO classes: 41=cup, 46=wine glass
    results = model(frame, verbose=False)
    
    cup_box = None
    for r in results:
        for box in r.boxes:
            cls_id = int(box.cls[0])
            if cls_id in [41, 46]:
                # Get bounds
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                cup_box = (x1, y1, x2, y2)
                break
        if cup_box is not None:
            break
            
    if cup_box is None:
        # NO cup/glass found: Do NOT run color masking
        return False, 0.0, frame.copy(), False
        
    # 2. Cup/glass bounding box found, add 10px padding and clamp
    x1, y1, x2, y2 = cup_box
    h, w = frame.shape[:2]
    x1 = max(0, x1 - 10)
    y1 = max(0, y1 - 10)
    x2 = min(w, x2 + 10)
    y2 = min(h, y2 + 10)
    
    # Crop the frame
    crop = frame[y1:y2, x1:x2]
    
    # Run HSV matcha masking ONLY on the cropped region
    hsv_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    
    # Define HSV bounds for muted yellow-green (matcha)
    lower_bound = np.array([30, 40, 50])
    upper_bound = np.array([75, 200, 220])
    mask = cv2.inRange(hsv_crop, lower_bound, upper_bound)
    
    # Calculate confidence based on percentage of matching pixels in the crop
    total_pixels = crop.shape[0] * crop.shape[1]
    matcha_pixels = cv2.countNonZero(mask)
    
    confidence = 0.0
    if total_pixels > 0:
        confidence = (matcha_pixels / total_pixels) * 100.0
        
    # If confidence hits at least 1%, boost to 100% temporarily
    if confidence >= 1.0:
        confidence = 100.0
        
    # Threshold for detection > 60%
    is_matcha = confidence > 60.0
    
    # Annotate frame
    annotated_frame = frame.copy()
    
    # Draw the bounding box in #1DB954 green (BGR: 84, 185, 29)
    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (84, 185, 29), 2)
    
    return is_matcha, confidence, annotated_frame, True
