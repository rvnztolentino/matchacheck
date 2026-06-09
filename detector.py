import cv2
import numpy as np


def _detect_with_hsv(frame):
    """Detect matcha-like green regions using OpenCV HSV color masking."""
    hsv_crop = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower_bound = np.array([30, 40, 50])
    upper_bound = np.array([75, 200, 220])
    mask = cv2.inRange(hsv_crop, lower_bound, upper_bound)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))

    total_pixels = frame.shape[0] * frame.shape[1]
    matcha_pixels = cv2.countNonZero(mask)
    confidence = 0.0
    if total_pixels > 0:
        confidence = min((matcha_pixels / total_pixels) * 1000.0, 100.0)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = [contour for contour in contours if cv2.contourArea(contour) > 1200]
    cup_found = len(contours) > 0

    is_matcha = cup_found and confidence > 8.0

    annotated_frame = frame.copy()
    if cup_found:
        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)
        cv2.rectangle(annotated_frame, (x, y), (x + w, y + h), (84, 185, 29), 2)

    return is_matcha, confidence, annotated_frame, cup_found


def detect_matcha(frame):
    """
    Detects if matcha is present in the provided BGR frame.

    Args:
        frame: A BGR image frame from OpenCV.

    Returns:
        is_matcha (bool): True if matcha was detected with sufficient confidence.
        confidence (float): 0-100 detection confidence.
        annotated_frame: Frame with bounding box drawn (if detected).
        cup_found (bool): True if a large matcha-like green region was detected.
    """
    return _detect_with_hsv(frame)
