import cv2
import numpy as np
from PyQt6.QtGui import QPainterPath
from PyQt6.QtCore import QPointF

class StencilProcessor:
    @staticmethod
    def auto_close_gaps(binary_mask, kernel_size=5):
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        return cv2.morphologyEx(binary_mask, cv2.MORPH_CLOSE, kernel)

    @staticmethod
    def smooth_contour_to_path(contour, epsilon_factor=0.002, close_endpoint_threshold=15.0):
        epsilon = epsilon_factor * cv2.arcLength(contour, False)
        approx = cv2.approxPolyDP(contour, epsilon, False)
        path = QPainterPath()
        if len(approx) == 0: return path
        start_pt = QPointF(float(approx[0][0][0]), float(approx[0][0][1]))
        path.moveTo(start_pt)
        for pt in approx[1:]:
            path.lineTo(QPointF(float(pt[0][0]), float(pt[0][1])))
        end_pt = QPointF(float(approx[-1][0][0]), float(approx[-1][0][1]))
        dx, dy = start_pt.x() - end_pt.x(), start_pt.y() - end_pt.y()
        if (dx * dx + dy * dy) ** 0.5 <= close_endpoint_threshold:
            path.closeSubpath()
        return path

    @staticmethod
    def extract_smart_stencil(bgr_frame, auto_seal=True):
        gray = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 50, 150)
        if auto_seal: edges = StencilProcessor.auto_close_gaps(edges, 5)
        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        unified_path = QPainterPath()
        for cnt in contours:
            if cv2.contourArea(cnt) > 20 or len(cnt) > 10:
                unified_path.addPath(StencilProcessor.smooth_contour_to_path(cnt))
        return unified_path
