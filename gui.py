import sys
import os
import time
import cv2
from PyQt6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QProgressBar, QListWidget, QFileDialog, QFrame)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap, QShortcut, QKeySequence

from detector import detect_matcha

class MatchaCheckWindow(QWidget):
    def __init__(self, sp_player):
        super().__init__()
        self.sp_player = sp_player
        
        # Configure initial window properties
        self.setWindowTitle("MatchaCheck")
        self.setFixedSize(900, 600)
        self.setStyleSheet("background-color: #121212; color: #FFFFFF;")
        
        # App state variables
        self.cap = cv2.VideoCapture(0)
        self.cooldown_end_time = 0.0
        self.last_results = []
        self.is_performative = False
        
        self.init_ui()
        
        # 30fps timer for webcam updates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_feed)
        self.timer.start(33) # ~30 frames per second
        
        # 1-second timer for flashing border
        self.border_timer = QTimer(self)
        self.border_timer.setSingleShot(True)
        self.border_timer.timeout.connect(self.reset_border)
        
    def init_ui(self):
        """Initializes the user interface layout and components."""
        main_layout = QHBoxLayout(self)
        
        # --- Left Panel for Video Feed ---
        self.left_panel = QFrame()
        self.left_panel.setStyleSheet("background-color: #1E1E1E; border-radius: 10px;")
        left_layout = QVBoxLayout(self.left_panel)
        
        self.video_label = QLabel("Loading webcam feed...")
        self.video_label.setFixedSize(640, 480)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("background-color: #000000;")
        left_layout.addWidget(self.video_label)
        
        # --- Right Panel for App Controls and Status ---
        self.right_panel = QFrame()
        self.right_panel.setStyleSheet("background-color: #1E1E1E; border-radius: 10px; padding: 10px;")
        right_layout = QVBoxLayout(self.right_panel)
        
        # Title
        title = QLabel("🍵 MatchaCheck")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        right_layout.addWidget(title)
        
        # Verdict label
        self.verdict_label = QLabel("Not Performative")
        self.verdict_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #888888;")
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
        self.hint_label = QLabel("Show me your matcha ☕")
        self.hint_label.setStyleSheet("color: #AAAAAA;")
        right_layout.addWidget(self.hint_label)
        
        # Scan Button
        self.scan_btn = QPushButton("Scan")
        self.scan_btn.setStyleSheet("background-color: #333333; padding: 10px; border-radius: 5px;")
        self.scan_btn.clicked.connect(self.scan_snapshot)
        right_layout.addWidget(self.scan_btn)
        
        # Upload Button
        self.upload_btn = QPushButton("Upload Photo")
        self.upload_btn.setStyleSheet("background-color: #333333; padding: 10px; border-radius: 5px;")
        self.upload_btn.clicked.connect(self.upload_photo)
        right_layout.addWidget(self.upload_btn)
        
        # Recent results history
        history_label = QLabel("Recent Results:")
        history_label.setStyleSheet("font-size: 14px; margin-top: 10px;")
        right_layout.addWidget(history_label)
        
        self.history_list = QListWidget()
        self.history_list.setStyleSheet("background-color: #121212; border: 1px solid #333333; border-radius: 5px;")
        right_layout.addWidget(self.history_list)
        
        main_layout.addWidget(self.left_panel)
        main_layout.addWidget(self.right_panel)
        
        # Global Spacebar shortcut mapped to scanning
        shortcut = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        shortcut.activated.connect(self.scan_snapshot)

    def update_feed(self):
        """Called every 33ms to update the webcam feed and process the frame."""
        ret, frame = self.cap.read()
        if not ret:
            print("Failed to grab frame from webcam")
            return
            
        # Process the live frame for matcha detection
        self.process_frame(frame)
        
        # Convert BGR frame to RGB for displaying via QImage
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qt_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_img)
        
        # Scale the image to fit the 640x480 box
        self.video_label.setPixmap(pixmap.scaled(640, 480, Qt.AspectRatioMode.KeepAspectRatio))

    def process_frame(self, frame):
        """Analyzes a single frame for matcha and updates UI state accordingly."""
        current_time = time.time()
        in_cooldown = current_time < self.cooldown_end_time
        
        if in_cooldown:
            remaining = int(self.cooldown_end_time - current_time) + 1
            self.status_line.setText(f"⏳ Cooldown... {remaining}s")
        else:
            self.status_line.setText("")
            
        # Call the detector function with new return signature
        is_matcha, confidence, _, cup_found = detect_matcha(frame)
        
        # Update confidence bar
        self.confidence_bar.setValue(int(confidence))
        
        # Update Hint and Verdict logic based on cup_found and is_matcha
        if not cup_found:
            self.hint_label.show()
            self.confidence_bar.setValue(0)
            if self.is_performative:
                self.sp_player.stop_playback()
                self.is_performative = False
            self.verdict_label.setText("Not Performative")
            self.verdict_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #888888;")
        else:
            self.hint_label.hide()
            
            # Handle state transitions
            if is_matcha and not in_cooldown:
                self.trigger_performative()
            elif not is_matcha:
                if self.is_performative:
                    self.sp_player.stop_playback()
                    self.is_performative = False
                self.verdict_label.setText("❌ Not Performative")
                self.verdict_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #888888;")

    def trigger_performative(self):
        """Handles the sequence of actions when matcha is confirmed detected."""
        self.is_performative = True
        self.verdict_label.setText("✅ PERFORMATIVE")
        self.verdict_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #1DB954;")
        
        # Visual flare
        self.flash_border()
        
        # Run spotify player
        self.sp_player.play_performative()
        
        # Set 4-second cooldown
        self.cooldown_end_time = time.time() + 4.0
        
        # Save to history
        self.add_history("PERFORMATIVE")

    def flash_border(self):
        """Flashes a green border around the main window."""
        self.setStyleSheet("background-color: #121212; color: #FFFFFF; border: 3px solid #1DB954;")
        self.border_timer.start(1000)
        
    def reset_border(self):
        """Removes the green border after flashing."""
        self.setStyleSheet("background-color: #121212; color: #FFFFFF; border: none;")

    def add_history(self, verdict):
        """Adds a result to the verdict history list (keeps max 5)."""
        timestamp = time.strftime("%H:%M:%S")
        self.last_results.insert(0, f"[{timestamp}] {verdict}")
        
        if len(self.last_results) > 5:
            self.last_results.pop()
        
        self.history_list.clear()
        self.history_list.addItems(self.last_results)

    def scan_snapshot(self):
        """Manual snapshot scan triggered by button or spacebar."""
        ret, frame = self.cap.read()
        if ret:
            self.process_frame(frame)
            is_matcha, conf, _, cup_found = detect_matcha(frame)
            if not is_matcha:
                if cup_found:
                    self.add_history(f"❌ Not Performative ({conf:.1f}%)")
                else:
                    self.add_history("No Cup Detected")
                
    def upload_photo(self):
        """Opens file dialog for testing with an existing image."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Image Files (*.png *.jpg *.jpeg)")
        if file_path:
            frame = cv2.imread(file_path)
            if frame is not None:
                self.process_frame(frame)
                is_matcha, conf, _, cup_found = detect_matcha(frame)
                if is_matcha:
                    verdict = "✅ PERFORMATIVE"
                elif cup_found:
                    verdict = f"❌ Not Performative ({conf:.1f}%)"
                else:
                    verdict = "No Cup Detected"
                self.add_history(verdict)

    def closeEvent(self, event):
        """Clean up resources on exit."""
        self.cap.release()
        event.accept()
