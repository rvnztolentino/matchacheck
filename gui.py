import sys
import os
import time

from pathlib import Path

import cv2
import numpy as np

# MediaPipe tasks API (0.10.x+)
_mp_available = False
_mp_vision = None
_mp_drawing_utils = None
_mp_base_options = None
_mp_hand_connections = None
try:
    import mediapipe as mp
    from mediapipe.tasks.python import vision as _mp_vision
    from mediapipe.tasks.python.core.base_options import BaseOptions as _mp_base_options
    _mp_drawing_utils = _mp_vision.drawing_utils
    _mp_hand_connections = _mp_vision.HandLandmarksConnections.HAND_CONNECTIONS
    _mp_available = True
except Exception:
    pass
from PyQt6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QProgressBar,
    QListWidget,
    QFileDialog,
    QFrame,
    QMenu,
)
from PyQt6.QtCore import (
    QTimer,
    Qt,
    QPropertyAnimation,
    QEasingCurve,
    QRect,
    pyqtProperty,
)
from PyQt6.QtGui import (
    QImage,
    QPixmap,
    QAction,
    QPainter,
    QFont,
    QColor,
)

import detector
from detector import detect_matcha, get_mode, set_mode


class MatchaCheckWindow(QWidget):
    def __init__(self, sp_player):
        super().__init__()
        self.sp_player = sp_player

        # Configure initial window properties
        self.setWindowTitle("MatchaCheck")
        self.setFixedSize(1000, 620)
        self.setStyleSheet("background-color: #121212; color: #FFFFFF;")
        # Keeps the window on top of all other windows (Remove this if you don't want this)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)

        # App state variables
        # Default to HSV mode
        detector.set_mode('hsv')
        self.cap = cv2.VideoCapture(0)
        self.cooldown_end_time = 0.0
        self.last_results = []
        self.is_performative = False
        self._performative_hold_until = 0.0  # holds performative state for 4s
        self._last_frame = None       # for snapshot saving
        self._prev_time = time.time()  # for FPS calculation

        # Hand / finger tracking (MediaPipe HandLandmarker – tasks API)
        self._hand_landmarker = None
        if _mp_available:
            try:
                model_path = os.path.join("model", "hand_landmarker.task")
                if not os.path.exists(model_path):
                    raise FileNotFoundError(
                        f"{model_path} not found. Add hand_landmarker.task to the model/ directory."
                    )

                options = _mp_vision.HandLandmarkerOptions(
                    base_options=_mp_base_options(model_asset_path=model_path),
                    running_mode=_mp_vision.RunningMode.VIDEO,
                    num_hands=2,
                    min_hand_detection_confidence=0.5,
                    min_hand_presence_confidence=0.5,
                    min_tracking_confidence=0.5,
                )
                self._hand_landmarker = _mp_vision.HandLandmarker.create_from_options(options)
                self._frame_ts_ms = 0
                print("MediaPipe HandLandmarker initialized successfully.")
            except Exception as e:
                print(f"MediaPipe HandLandmarker init failed: {e}")
                self._hand_landmarker = None

        self.init_ui()

        # 30fps timer for webcam updates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_feed)
        self.timer.start(33)  # ~30 frames per second

        # Show splash screen after a short delay so the window is visible
        QTimer.singleShot(100, self.show_splash)

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------
    def init_ui(self):
        """Initializes the user interface layout and components."""
        # Outer wrapper so we can stack the main content + status bar vertically
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # Container for the two-panel layout
        content_widget = QWidget()
        main_layout = QHBoxLayout(content_widget)
        main_layout.setContentsMargins(6, 6, 6, 6)

        # --- Left Panel for Video Feed ---
        self.left_panel = QFrame()
        self.left_panel.setFixedWidth(660)
        self.left_panel.setStyleSheet("background-color: #1E1E1E; border-radius: 10px;")
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(8, 8, 8, 8)

        self.video_label = QLabel("Loading webcam feed...")
        self.video_label.setMinimumSize(480, 360)
        self.video_label.setMaximumSize(644, 484)
        self.video_label.setSizePolicy(
            self.video_label.sizePolicy().horizontalPolicy(),
            self.video_label.sizePolicy().verticalPolicy()
        )
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("background-color: #000000; border-radius: 6px;")
        self.video_label.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.video_label.customContextMenuRequested.connect(self._show_context_menu)
        left_layout.addWidget(self.video_label)

        # FPS overlay label (painted on top of video_label)
        self.fps_label = QLabel("0 FPS", self.video_label)
        self.fps_label.setStyleSheet(
            "color: #555555; background: transparent; font-size: 11px; padding: 4px;"
        )
        self.fps_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
        self.fps_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.fps_label.setGeometry(4, 458, 80, 20)

        # --- Right Panel for App Controls and Status ---
        self.right_panel = QFrame()
        self.right_panel.setStyleSheet(
            "background-color: #1E1E1E; border-radius: 10px; padding: 10px;"
        )
        right_layout = QVBoxLayout(self.right_panel)

        # Title
        title = QLabel("MatchaCheck")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        right_layout.addWidget(title)

        # Verdict label
        self.verdict_label = QLabel("Not Performative")  # no emojis
        self.verdict_label.setStyleSheet(
            "font-size: 20px; font-weight: bold; color: #888888;"
        )
        right_layout.addWidget(self.verdict_label)

        # Confidence progress bar
        self.confidence_bar = QProgressBar()
        self.confidence_bar.setRange(0, 100)
        self.confidence_bar.setValue(0)
        self.confidence_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #888888;
                border-radius: 5px;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #1DB954;
            }
        """)
        right_layout.addWidget(self.confidence_bar)

        # Status line (Cooldown)
        self.status_line = QLabel("")
        self.status_line.setStyleSheet("color: #AAAAAA; font-style: italic;")
        right_layout.addWidget(self.status_line)

        # Hint text
        self.hint_label = QLabel("Show me your matcha")
        self.hint_label.setStyleSheet("color: #AAAAAA;")
        right_layout.addWidget(self.hint_label)

        # Upload Button
        self.upload_btn = QPushButton("Upload Photo")
        self.upload_btn.setStyleSheet(
            "background-color: #333333; padding: 10px; border-radius: 5px;"
        )
        self.upload_btn.clicked.connect(self.upload_photo)
        right_layout.addWidget(self.upload_btn)

        # Mode indicator label (read-only display)
        self.mode_label = QLabel()
        self.mode_label.setStyleSheet(
            "color: #AAAAAA; font-size: 11px; font-style: italic;"
        )
        right_layout.addWidget(self.mode_label)

        # Model toggle button
        self.toggle_btn = QPushButton()
        self._update_toggle_label()
        self.toggle_btn.setStyleSheet(
            "background-color: #333333; padding: 10px; border-radius: 5px;"
        )
        self.toggle_btn.clicked.connect(self._toggle_model)
        right_layout.addWidget(self.toggle_btn)

        # Recent results history
        history_label = QLabel("Recent Results:")
        history_label.setStyleSheet("font-size: 14px; margin-top: 10px;")
        right_layout.addWidget(history_label)

        self.history_list = QListWidget()
        self.history_list.setStyleSheet(
            "background-color: #121212; border: 1px solid #333333; border-radius: 5px;"
        )
        right_layout.addWidget(self.history_list, stretch=1)

        main_layout.addWidget(self.left_panel)
        main_layout.addWidget(self.right_panel)

        outer_layout.addWidget(content_widget, stretch=1)

        # No bottom status bar — removed to eliminate residual green line



    # ------------------------------------------------------------------
    # Splash screen
    # ------------------------------------------------------------------
    def show_splash(self):
        """Dark overlay with 'MatchaCheck', fades out over 1.5s."""
        self.splash_overlay = QLabel(self)
        self.splash_overlay.setGeometry(0, 0, self.width(), self.height())
        self.splash_overlay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.splash_overlay.setText("MatchaCheck")
        self.splash_overlay.setStyleSheet(
            "background-color: rgba(0, 0, 0, 220); color: #FFFFFF; "
            "font-size: 48px; font-weight: bold;"
        )
        self.splash_overlay.raise_()
        self.splash_overlay.show()

        from PyQt6.QtWidgets import QGraphicsOpacityEffect
        self._splash_effect = QGraphicsOpacityEffect(self.splash_overlay)
        self._splash_effect.setOpacity(1.0)
        self.splash_overlay.setGraphicsEffect(self._splash_effect)

        self._splash_anim = QPropertyAnimation(self._splash_effect, b"opacity")
        self._splash_anim.setDuration(1500)
        self._splash_anim.setStartValue(1.0)
        self._splash_anim.setEndValue(0.0)
        self._splash_anim.setEasingCurve(QEasingCurve.Type.InQuad)
        self._splash_anim.finished.connect(self.splash_overlay.hide)
        self._splash_anim.start()

    # ------------------------------------------------------------------
    # Model toggle
    # ------------------------------------------------------------------
    def _update_toggle_label(self):
        mode = get_mode()
        if mode == "custom":
            self.toggle_btn.setText("Switch to HSV")
            self.mode_label.setText("Active mode: Custom Model")
        else:
            self.toggle_btn.setText("Switch to Custom Model")
            self.mode_label.setText("Active mode: HSV Detection")

    def _toggle_model(self):
        current = get_mode()
        try:
            new_mode = "hsv" if current == "custom" else "custom"
            set_mode(new_mode)
        except RuntimeError:
            # Custom model not available — stay on HSV
            pass
        self._update_toggle_label()

    # ------------------------------------------------------------------
    # Context menu (right-click on webcam feed)
    # ------------------------------------------------------------------
    def _show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background-color: #1E1E1E; color: #FFFFFF; border: 1px solid #333; }"
            "QMenu::item:selected { background-color: #333333; }"
        )

        save_action = menu.addAction("Save Snapshot")
        clear_action = menu.addAction("Clear History")

        action = menu.exec(self.video_label.mapToGlobal(pos))
        if action == save_action:
            self._save_snapshot()
        elif action == clear_action:
            self._clear_history()

    def _save_snapshot(self):
        if self._last_frame is not None:
            desktop = Path.home() / "Desktop"
            path = str(desktop / "matchacheck_snapshot.png")
            cv2.imwrite(path, self._last_frame)
            print(f"Snapshot saved to {path}")

    def _clear_history(self):
        self.last_results.clear()
        self.history_list.clear()

    # ------------------------------------------------------------------
    # Verdict pulse animation
    # ------------------------------------------------------------------
    def _pulse_verdict(self):
        """Animate the verdict label geometry to 'pulse' (scale up then back)."""
        orig = self.verdict_label.geometry()
        dx = int(orig.width() * 0.05)
        dy = int(orig.height() * 0.05)
        expanded = QRect(
            orig.x() - dx, orig.y() - dy,
            orig.width() + 2 * dx, orig.height() + 2 * dy,
        )

        self._pulse_anim = QPropertyAnimation(self.verdict_label, b"geometry")
        self._pulse_anim.setDuration(400)
        self._pulse_anim.setKeyValueAt(0, orig)
        self._pulse_anim.setKeyValueAt(0.5, expanded)
        self._pulse_anim.setKeyValueAt(1.0, orig)
        self._pulse_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._pulse_anim.start()

    # ------------------------------------------------------------------
    # Frame processing
    # ------------------------------------------------------------------
    def update_feed(self):
        """Called every 33ms to update the webcam feed and process the frame."""
        ret, frame = self.cap.read()
        if not ret:
            print("Failed to grab frame from webcam")
            return

        self._last_frame = frame.copy()

        # FPS calculation
        now = time.time()
        dt = now - self._prev_time
        self._prev_time = now
        fps = int(1.0 / dt) if dt > 0 else 0
        self.fps_label.setText(f"{fps} FPS")

        # Draw hand / finger lines using MediaPipe Hands
        self._annotate_hands(frame)

        # Process the live frame for matcha detection
        self.process_frame(frame)

        # Convert BGR frame to RGB for displaying via QImage
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qt_img = QImage(rgb_frame.data, w, h, bytes_per_line,
                        QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_img)

        # Scale the image to fit inside the video label, always contained
        target = self.video_label.size()
        self.video_label.setPixmap(
            pixmap.scaled(target, Qt.AspectRatioMode.KeepAspectRatio,
                          Qt.TransformationMode.SmoothTransformation)
        )

    def _annotate_hands(self, frame):
        """Runs MediaPipe HandLandmarker on the frame and draws finger/hand connections."""
        if self._hand_landmarker is None:
            return

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        self._frame_ts_ms += 33  # approximate 30 fps timestamps
        try:
            results = self._hand_landmarker.detect_for_video(mp_image, self._frame_ts_ms)
        except Exception:
            return

        if not results.hand_landmarks:
            return

        # Fingertip landmark indices (thumb, index, middle, ring, pinky)
        _FINGERTIPS = {4, 8, 12, 16, 20}

        for landmarks in results.hand_landmarks:
            h, w = frame.shape[:2]
            pts = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks]
            # White connection lines
            for conn in _mp_hand_connections:
                cv2.line(frame, pts[conn.start], pts[conn.end], (255, 255, 255), 2)
            # Green dots for joints, red dots for fingertips
            for i, pt in enumerate(pts):
                color = (0, 0, 220) if i in _FINGERTIPS else (0, 200, 0)
                cv2.circle(frame, pt, 4, color, -1)

    def process_frame(self, frame):
        """Analyzes a single frame for matcha and updates UI state accordingly."""
        current_time = time.time()
        in_cooldown = current_time < self.cooldown_end_time
        in_hold = current_time < self._performative_hold_until

        if in_cooldown:
            remaining = int(self.cooldown_end_time - current_time) + 1
            self.status_line.setText(f"Cooldown... {remaining}s")
        else:
            self.status_line.setText("")

        # Call the detector function
        is_matcha, confidence, _, cup_found = detect_matcha(frame)

        # While the 4-second hold is active, keep showing performative state
        # regardless of whether the cup was removed or detection dropped.
        if in_hold:
            self.hint_label.hide()
            self.confidence_bar.setValue(100)
            # Re-extend hold if still actively detecting matcha
            if is_matcha and not in_cooldown:
                self.trigger_performative()
            return

        # Update confidence bar
        self.confidence_bar.setValue(int(confidence))

        # Update Hint and Verdict logic based on cup_found and is_matcha
        if not cup_found:
            self.hint_label.show()
            self.hint_label.setText("Show me your matcha")
            self.confidence_bar.setValue(0)
            if self.is_performative:
                self.sp_player.stop_playback()
                self.is_performative = False
            self.verdict_label.setText("Not Performative")
            self.verdict_label.setStyleSheet(
                "font-size: 20px; font-weight: bold; color: #888888;"
            )
        else:
            if is_matcha and not in_cooldown:
                self.hint_label.hide()
                self.trigger_performative()
            elif not is_matcha:
                self.hint_label.show()
                self.hint_label.setText("Not a matcha :(")
                if self.is_performative:
                    self.sp_player.stop_playback()
                    self.is_performative = False
                self.verdict_label.setText("Not Performative")
                self.verdict_label.setStyleSheet(
                    "font-size: 20px; font-weight: bold; color: #888888;"
                )

    def trigger_performative(self):
        """Handles the sequence of actions when matcha is confirmed detected."""
        now = time.time()
        self.is_performative = True
        self.verdict_label.setText("PERFORMATIVE")
        self.verdict_label.setStyleSheet(
            "font-size: 20px; font-weight: bold; color: #1DB954;"
        )

        # Verdict pulse animation
        self._pulse_verdict()

        # Run spotify player
        self.sp_player.play_performative()

        # Set 4-second cooldown (prevents re-triggering Spotify)
        self.cooldown_end_time = now + 6.0

        # Set 4-second hold: keeps performative state even if cup is removed
        self._performative_hold_until = now + 6.0

        # Save to history
        self.add_history("PERFORMATIVE")

    def add_history(self, verdict):
        """Adds a result to the verdict history list (keeps max 5)."""
        timestamp = time.strftime("%H:%M:%S")
        self.last_results.insert(0, f"[{timestamp}] {verdict}")

        if len(self.last_results) > 5:
            self.last_results.pop()

        self.history_list.clear()
        self.history_list.addItems(self.last_results)


    def upload_photo(self):
        """Opens file dialog for testing with an existing image."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Image", "", "Image Files (*.png *.jpg *.jpeg)"
        )
        if file_path:
            frame = cv2.imread(file_path)
            if frame is not None:
                self.process_frame(frame)
                is_matcha, conf, _, cup_found = detect_matcha(frame)
                if is_matcha:
                    verdict = "PERFORMATIVE"
                elif cup_found:
                    verdict = f"Not Performative ({conf:.1f}%)"
                else:
                    verdict = "No Cup Detected"
                self.add_history(verdict)

    def closeEvent(self, event):
        """Clean up resources on exit."""
        self.cap.release()
        if self._hand_landmarker is not None:
            self._hand_landmarker.close()
        event.accept()
