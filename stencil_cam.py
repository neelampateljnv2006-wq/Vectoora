"""
stencil_cam.py - Robust OpenCV Camera Stencil Engine
Provides both extracted_contours and extracted_path for guaranteed compatibility.
"""
import cv2
import numpy as np
from PyQt6.QtCore import Qt, QTimer, QPointF
from PyQt6.QtGui import QImage, QPixmap, QPainterPath
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox
)

class OpenCVStencilDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Vectoora - OpenCV Live Stencil Camera")
        self.setFixedSize(680, 580)
        self.setStyleSheet("""
            QDialog { background-color: #0B0F19; color: #F8FAFC; font-family: 'Segoe UI', sans-serif; }
            QLabel { color: #CBD5E1; }
            QPushButton.captureBtn { background-color: #38BDF8; color: #070B11; font-weight: bold; border-radius: 8px; padding: 10px 18px; font-size: 13px; }
            QPushButton.captureBtn:hover { background-color: #7DD3FC; }
            QPushButton.closeBtn { background-color: #1E293B; color: #94A3B8; border-radius: 8px; padding: 10px 16px; font-size: 13px; }
        """)

        self.cap = None
        self.current_frame = None
        self.extracted_contours = []
        self.extracted_path = None
        self._build_ui()
        self._init_camera()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)

        title = QLabel("📷 OpenCV Real-Time Face & Sketch Stencil")
        title.setStyleSheet("font-size: 16px; font-weight: 800; color: #38BDF8;")
        sub = QLabel("Camera ke samne photo capture karein — OpenCV ise instant vector stencil me convert karega.")
        sub.setStyleSheet("font-size: 11px; color: #94A3B8;")
        lay.addWidget(title)
        lay.addWidget(sub)

        self.video_label = QLabel()
        self.video_label.setFixedSize(640, 400)
        self.video_label.setStyleSheet("background-color: #050811; border: 2px dashed #1E293B; border-radius: 10px;")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.video_label)

        bot_bar = QHBoxLayout()
        self.status_lbl = QLabel("Status: Camera Active")
        self.status_lbl.setStyleSheet("font-size: 11px; color: #A3E635;")
        bot_bar.addWidget(self.status_lbl)
        bot_bar.addStretch(1)

        close_btn = QPushButton("Cancel")
        close_btn.setProperty("class", "closeBtn")
        close_btn.clicked.connect(self.reject)
        bot_bar.addWidget(close_btn)

        self.capture_btn = QPushButton("⚡ Snap & Generate Vector Stencil")
        self.capture_btn.setProperty("class", "captureBtn")
        self.capture_btn.clicked.connect(self._capture_and_process)
        bot_bar.addWidget(self.capture_btn)

        lay.addLayout(bot_bar)

    def _init_camera(self):
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.status_lbl.setText("Status: Webcam not detected")
            self.status_lbl.setStyleSheet("color: #F43F5E; font-size: 11px;")
            self.video_label.setText("⚠️ Webcam Not Available")
            return

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_frame)
        self.timer.start(30)

    def _update_frame(self):
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.flip(frame, 1)
                self.current_frame = frame
                h, w, ch = frame.shape
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                qt_img = QImage(rgb_frame.data, w, h, ch * w, QImage.Format.Format_RGB888)
                self.video_label.setPixmap(QPixmap.fromImage(qt_img).scaled(
                    self.video_label.width(), self.video_label.height(),
                    Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
                ))

    def _capture_and_process(self):
        if self.current_frame is None:
            QMessageBox.warning(self, "Error", "No frame captured.")
            return

        gray = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.bilateralFilter(gray, 7, 50, 50)
        edges = cv2.Canny(blurred, 40, 130)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        edges = cv2.dilate(edges, kernel, iterations=1)

        contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        self.extracted_contours = contours

        path = QPainterPath()
        scale = 0.5
        cx, cy = 640 * scale / 2, 480 * scale / 2

        for cnt in contours:
            if cv2.contourArea(cnt) > 25 or len(cnt) > 12:
                pts = cnt.reshape(-1, 2)
                p0 = QPointF(float(pts[0][0]) * scale - cx, float(pts[0][1]) * scale - cy)
                path.moveTo(p0)
                for pt in pts[1:]:
                    path.lineTo(QPointF(float(pt[0]) * scale - cx, float(pt[1]) * scale - cy))
                path.closeSubpath()

        self.extracted_path = path

        if self.timer.isActive():
            self.timer.stop()
        if self.cap and self.cap.isOpened():
            self.cap.release()

        self.accept()

    def closeEvent(self, event):
        if hasattr(self, 'timer') and self.timer.isActive():
            self.timer.stop()
        if self.cap and self.cap.isOpened():
            self.cap.release()
        super().closeEvent(event)
