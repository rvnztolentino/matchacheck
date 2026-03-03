import os
import cv2
import numpy as np
from ultralytics import YOLO

# --- Model Loading ---
_MODEL_PATH = os.path.join("model", "best.pt")
_CUSTOM_MODEL_AVAILABLE = os.path.exists(_MODEL_PATH)

# Load both models as needed
if _CUSTOM_MODEL_AVAILABLE:
    _custom_model = YOLO(_MODEL_PATH)
else:
    _custom_model = None
    print("Custom model not found — falling back to HSV detection")

_hsv_model = YOLO(os.path.join("model", "yolov8n.pt"))

# Runtime mode: "custom" or "hsv"
_current_mode = "custom" if _CUSTOM_MODEL_AVAILABLE else "hsv"


def get_mode():
    """Returns the current detection mode ('custom' or 'hsv')."""
    return _current_mode


def set_mode(mode):
    """
    Switch detection mode at runtime.

    Args:
        mode: 'custom' or 'hsv'

    Raises:
        ValueError: If mode is not 'custom' or 'hsv'.
        RuntimeError: If 'custom' is requested but model/best.pt was not found.
    """
    global _current_mode
    if mode not in ("custom", "hsv"):
        raise ValueError(f"Invalid mode '{mode}'. Use 'custom' or 'hsv'.")
    if mode == "custom" and not _CUSTOM_MODEL_AVAILABLE:
        raise RuntimeError("Cannot switch to custom mode — model/best.pt not found.")
    _current_mode = mode


def _detect_with_custom_model(frame):
    """Run the custom single-class 'matcha' model on the frame."""
    if _custom_model is None:
        raise RuntimeError("Custom model is not loaded.")
    results = _custom_model(frame, verbose=False)

    is_matcha = False
    confidence = 0.0
    annotated_frame = frame.copy()
    cup_found = False

    best_conf = 0.0
    best_box = None

    for r in results:
        for box in r.boxes:
            cup_found = True  # any detection counts
            cls_name = _custom_model.names[int(box.cls[0])]
            conf = float(box.conf[0])
            if cls_name == "matcha" and conf > 0.6:
                if conf > best_conf:
                    best_conf = conf
                    best_box = box.xyxy[0].cpu().numpy().astype(int)

    if best_box is not None:
        is_matcha = True
        confidence = best_conf * 100
        x1, y1, x2, y2 = best_box
        # Draw bounding box in #1DB954 green (BGR: 84, 185, 29)
        cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (84, 185, 29), 2)
        label = f"matcha {confidence:.0f}%"
        cv2.putText(
            annotated_frame, label, (x1, y1 - 8),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (84, 185, 29), 2,
        )

    return is_matcha, confidence, annotated_frame, cup_found


def _detect_with_hsv(frame):
    """Phase 1 fallback: YOLO cup detection + HSV color masking."""
    results = _hsv_model(frame, verbose=False)

    cup_box = None
    for r in results:
        for box in r.boxes:
            cls_id = int(box.cls[0])
            if cls_id in [41, 46]:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                cup_box = (x1, y1, x2, y2)
                break
        if cup_box is not None:
            break

    if cup_box is None:
        return False, 0.0, frame.copy(), False

    x1, y1, x2, y2 = cup_box
    h, w = frame.shape[:2]
    x1 = max(0, x1 - 10)
    y1 = max(0, y1 - 10)
    x2 = min(w, x2 + 10)
    y2 = min(h, y2 + 10)

    crop = frame[y1:y2, x1:x2]

    hsv_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    lower_bound = np.array([30, 40, 50])
    upper_bound = np.array([75, 200, 220])
    mask = cv2.inRange(hsv_crop, lower_bound, upper_bound)

    total_pixels = crop.shape[0] * crop.shape[1]
    matcha_pixels = cv2.countNonZero(mask)

    confidence = 0.0
    if total_pixels > 0:
        confidence = (matcha_pixels / total_pixels) * 100.0

    # Temporary fix for the confidence always being 100%
    if confidence >= 15.0:
        confidence = 100.0

    is_matcha = confidence > 60.0

    annotated_frame = frame.copy()
    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (84, 185, 29), 2)

    return is_matcha, confidence, annotated_frame, True


def detect_matcha(frame):
    """
    Detects if matcha is present in the provided BGR frame.

    Dispatches to the custom model or HSV pipeline based on the
    current mode set via set_mode().

    Args:
        frame: A BGR image frame from OpenCV.

    Returns:
        is_matcha (bool): True if matcha was detected with sufficient confidence.
        confidence (float): 0-100 detection confidence.
        annotated_frame: Frame with bounding box drawn (if detected).
        cup_found (bool): True if a cup/glass (or any object) was detected.
    """
    if _current_mode == "custom":
        return _detect_with_custom_model(frame)
    return _detect_with_hsv(frame)
