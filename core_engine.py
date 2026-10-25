"""
core_engine.py - Computer Vision & OpenCV Pipeline
"""
import cv2
import numpy as np
from PyQt6.QtGui import QImage

def blank_canvas(width: int, height: int) -> np.ndarray:
    return np.full((height, width, 3), 255, dtype=np.uint8)

def bgr_to_qimage(img_bgr: np.ndarray) -> QImage:
    h, w, ch = img_bgr.shape
    bytes_per_line = ch * w
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    return QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()

def create_stencil(frame_bgr: np.ndarray, max_side: int = 900, border: int = 3) -> np.ndarray:
    """Photo ko coloring stencil banata hai aur line gaps weld karta hai."""
    if frame_bgr is None or frame_bgr.size == 0:
        raise ValueError("Image empty nahi honi chahiye")

    h, w = frame_bgr.shape[:2]
    scale = max_side / max(h, w)
    if scale < 1.0:
        frame_bgr = cv2.resize(frame_bgr, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 9, 75, 75)
    gray = cv2.medianBlur(gray, 5)

    block = max(11, int(min(h, w) * 0.02)) | 1
    lines = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, block, 5
    )

    # Gaps Seal Dilation: Color leakage rokhne ke liye
    kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    lines = cv2.morphologyEx(lines, cv2.MORPH_CLOSE, kernel_close, iterations=2)
    kernel_dilate = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    lines = cv2.dilate(lines, kernel_dilate, iterations=1)

    if border > 0:
        lines[:border, :] = 255
        lines[-border:, :] = 255
        lines[:, :border] = 255
        lines[:, -border:] = 255

    page = 255 - lines
    return cv2.cvtColor(page, cv2.COLOR_GRAY2BGR)

def apply_flood_fill(paint_layer: np.ndarray, stencil_layer: np.ndarray,
                     seed_point: tuple, bgr_color: tuple):
    h, w = paint_layer.shape[:2]
    x, y = seed_point
    if not (0 <= x < w and 0 <= y < h):
        return None

    gray_stencil = cv2.cvtColor(stencil_layer, cv2.COLOR_BGR2GRAY)
    _, bounds = cv2.threshold(gray_stencil, 70, 255, cv2.THRESH_BINARY_INV)

    if bounds[y, x] == 255:
        return None

    mask = np.zeros((h + 2, w + 2), dtype=np.uint8)
    mask[1:-1, 1:-1] = bounds

    out = paint_layer.copy()
    flags = 4 | (255 << 8) | cv2.FLOODFILL_FIXED_RANGE
    cv2.floodFill(out, mask, (x, y), bgr_color, (15, 15, 15), (15, 15, 15), flags)
    return out

def diff_patch(old_img: np.ndarray, new_img: np.ndarray):
    diff = np.any(old_img != new_img, axis=-1)
    if not np.any(diff):
        return None
    ys, xs = np.where(diff)
    y1, y2 = int(ys.min()), int(ys.max() + 1)
    x1, x2 = int(xs.min()), int(xs.max() + 1)
    return (x1, y1, old_img[y1:y2, x1:x2].copy(), new_img[y1:y2, x1:x2].copy())

def compose_canvas(paint_layer: np.ndarray, stencil_layer: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(stencil_layer, cv2.COLOR_BGR2GRAY)
    lines_mask = gray < 80
    comp = paint_layer.copy()
    comp[lines_mask] = stencil_layer[lines_mask]
    return comp