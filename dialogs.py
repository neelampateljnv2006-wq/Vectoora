"""
dialogs.py - Camera capture popup dialog
"""
import cv2
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
import core_engine

class CameraDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Live Camera Snap")
        self.cap = cv2.VideoCapture(0)
        self.captured_frame = None

        layout = QVBoxLayout(self)
        self.video_label = QLabel("Camera initializing...")
        self.video_label.setFixedSize(640, 480)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.video_label)

        snap_btn = QPushButton("📸 CAPTURE PHOTO")
        snap_btn.setFixedHeight(50)
        snap_btn.clicked.connect(self._snap)
        layout.addWidget(snap_btn)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_feed)
        if self.cap.isOpened():
            self.timer.start(33)

    def _update_feed(self):
        ret, frame = self.cap.read()
        if ret:
            self._last_frame = frame
            qimg = core_engine.bgr_to_qimage(frame)
            self.video_label.setPixmap(QPixmap.fromImage(qimg).scaled(640, 480, Qt.AspectRatioMode.KeepAspectRatio))

    def _snap(self):
        self.captured_frame = getattr(self, "_last_frame", None)
        self.timer.stop()
        if self.cap.isOpened():
            self.cap.release()
        self.accept()

    def closeEvent(self, event):
        self.timer.stop()
        if self.cap.isOpened():
            self.cap.release()
        event.accept()