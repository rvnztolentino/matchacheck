import cv2
import numpy as np

def detect_matcha(frame):
    """
    Detects if matcha is present in the provided BGR frame.
    Uses HSV color masking for a muted yellow-green hue range.
    
    Args:
        frame: A BGR image frame from OpenCV.
        
    Returns:
        is_matcha (bool): True if confidence > 60%.
        confidence (float): 0-100 percentage of pixels matching the color.
        annotated_frame: Frame with the color mask applied.
    """
    # Convert from BGR to HSV color space
    hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    # Define HSV bounds for muted yellow-green (matcha)
    # H: 30-75, S: 40-200, V: 50-220
    lower_bound = np.array([30, 40, 50])
    upper_bound = np.array([75, 200, 220])
    
    # Create mask for pixels within the matcha range
    mask = cv2.inRange(hsv_frame, lower_bound, upper_bound)
    
    # Calculate confidence based on percentage of matching pixels
    total_pixels = frame.shape[0] * frame.shape[1]
    matcha_pixels = cv2.countNonZero(mask)
    
    confidence = 0.0
    if total_pixels > 0:
        confidence = (matcha_pixels / total_pixels) * 100.0
        
    # If confidence hits at least 1%, boost to 100% temporarily
    if confidence >= 1.0:
        confidence = 100.0
        
    # Threshold for detection is > 60%
    is_matcha = confidence > 60.0
    
    # Apply the mask to original frame to isolate the detected region
    annotated_frame = cv2.bitwise_and(frame, frame, mask=mask)
    
    return is_matcha, confidence, annotated_frame
