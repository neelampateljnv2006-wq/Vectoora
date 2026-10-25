"""
ui_components.py  -  Presentation layer

Custom PyQt6 widgets for a text-free, high-contrast, touch-friendly editor:

* Theme / APP_STYLESHEET - every colour and size lives here
* Tool                   - tool vocabulary shared with the controller
* IconButton             - big (>= 56 px) painted-icon button, hover/active states
* SizePicker             - four dots of increasing size (brush size)
* ColorPalette           - 8 bold circular swatches
* ShapeItem              - draggable / scalable vector stamp
* CanvasView             - QGraphicsView handling mouse press/move/release
* CameraDialog           - webcam preview with a big shutter button

This module knows nothing about OpenCV.  Frames are supplied through
injected callables, and the controller (main.py) wires in core_engine.
"""

from __future__ import annotations

import math
from enum import Enum, auto
from typing import Callable, List, Optional

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (QBrush, QColor, QKeyEvent, QPainter, QPainterPath,
                         QPen, QPixmap, QPolygonF)
from PyQt6.QtWidgets import (QAbstractButton, QButtonGroup, QDialog,
                             QGraphicsItem, QGraphicsPathItem,
                             QGraphicsPixmapItem, QGraphicsScene,
                             QGraphicsView, QGridLayout, QHBoxLayout, QLabel,
                             QSizePolicy, QVBoxLayout, QWidget)


# --------------------------------------------------------------------------- #
# Theme
# --------------------------------------------------------------------------- #
class Theme:
    INK = "#111111"
    PAPER = "#FFFFFF"
    PANEL = "#ECEFF1"
    CANVAS_BG = "#37474F"
    ACTIVE_BG = "#0D47A1"       # deep blue
    ACTIVE_RING = "#FFEB3B"     # bright yellow (21:1 contrast on the blue)
    HOVER_BG = "#FFF3C4"
    PRESS_BG = "#FFD54F"
    FOCUS = "#00B0FF"
    DISABLED_BG = "#CFD8DC"
    DISABLED_FG = "#78909C"

    MIN_TARGET = 56             # absolute minimum touch target (px)
    BUTTON = 80                 # standard big button
    BUTTON_PRIMARY = 96         # Undo
    SWATCH = 64


APP_STYLESHEET = f"""
QMainWindow, QDialog {{ background: {Theme.PANEL}; }}
QWidget#panel {{ background: {Theme.PANEL}; }}
QToolTip {{ background: {Theme.INK}; color: white; border: 2px solid white;
            padding: 6px; font-size: 18px; }}
"""


class Tool(Enum):
    BRUSH = auto()
    FILL = auto()
    STAMP = auto()
    CAMERA = auto()
    SELECT = auto()

from PyQt6.QtWidgets import QColorDialog

def open_full_color_picker(self):
    color = QColorDialog.getColor()
    if color.isValid():
        # Selected hex ya RGB code engine ko pass ho jayega
        self.set_active_color(color.name())


# --------------------------------------------------------------------------- #
# Icon drawing (100 x 100 design grid, no image files needed)
# --------------------------------------------------------------------------- #
def _pen(color, width: float) -> QPen:
    pen = QPen(QColor(color), width)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return pen


def _contrast(color: QColor) -> QColor:
    return QColor("#FFFFFF") if color.lightness() < 128 else QColor("#111111")


def star_points(cx: float, cy: float, outer: float, inner: float) -> List[QPointF]:
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        r = outer if i % 2 == 0 else inner
        pts.append(QPointF(cx + r * math.cos(ang), cy + r * math.sin(ang)))
    return pts


def _icon_camera(p, fg, accent):
    p.setPen(_pen(fg, 6))
    p.setBrush(accent)
    p.drawRoundedRect(QRectF(34, 16, 32, 18), 5, 5)
    p.drawRoundedRect(QRectF(8, 28, 84, 58), 12, 12)
    p.setBrush(_contrast(fg))
    p.drawEllipse(QPointF(50, 57), 20, 20)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(fg)
    p.drawEllipse(QPointF(50, 57), 9, 9)


def _icon_nocamera(p, fg, accent):
    _icon_camera(p, fg, QColor("#90A4AE"))
    p.setPen(_pen("#E53935", 11))
    p.drawLine(QPointF(14, 92), QPointF(88, 10))


def _icon_brush(p, fg, accent):
    p.setPen(_pen(fg, 9))
    p.drawLine(QPointF(84, 14), QPointF(52, 46))
    p.setPen(_pen(fg, 6))
    p.setBrush(accent)
    p.drawEllipse(QPointF(36, 64), 18, 18)
    p.setPen(_pen(fg, 5))
    p.drawLine(QPointF(12, 90), QPointF(40, 90))


def _icon_fill(p, fg, accent):
    p.setPen(_pen(fg, 6))
    p.save()
    p.translate(44, 54)
    p.rotate(-18)
    bucket = QPainterPath()
    bucket.moveTo(-28, -16)
    bucket.lineTo(28, -16)
    bucket.lineTo(20, 28)
    bucket.lineTo(-20, 28)
    bucket.closeSubpath()
    p.setBrush(accent)
    p.drawPath(bucket)
    handle = QPainterPath()
    handle.moveTo(-28, -16)
    handle.cubicTo(-28, -48, 28, -48, 28, -16)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(handle)
    p.restore()
    drop = QPainterPath()
    drop.moveTo(84, 52)
    drop.cubicTo(72, 66, 72, 82, 84, 82)
    drop.cubicTo(96, 82, 96, 66, 84, 52)
    p.setBrush(accent)
    p.drawPath(drop)


def _icon_stamp(p, fg, accent):
    p.setPen(_pen(fg, 6))
    p.setBrush(accent)
    p.drawEllipse(QPointF(50, 24), 15, 15)
    p.drawRect(QRectF(42, 36, 16, 22))
    p.drawRoundedRect(QRectF(18, 56, 64, 16), 5, 5)
    p.setBrush(fg)
    p.drawRoundedRect(QRectF(10, 76, 80, 12), 4, 4)


def _icon_select(p, fg, accent):
    arrow = QPolygonF([QPointF(26, 10), QPointF(26, 80), QPointF(44, 64),
                       QPointF(56, 90), QPointF(68, 84), QPointF(56, 58),
                       QPointF(80, 56)])
    p.setPen(_pen(fg, 6))
    p.setBrush(accent)
    p.drawPolygon(arrow)


def _icon_undo(p, fg, accent):
    rect = QRectF(22, 28, 56, 56)
    arc = QPainterPath()
    arc.arcMoveTo(rect, -60)
    arc.arcTo(rect, -60, 190)
    p.setPen(_pen(fg, 11))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(arc)
    p.setPen(_pen(fg, 4))
    p.setBrush(fg)
    p.drawPolygon(QPolygonF([QPointF(20, 46), QPointF(45, 46), QPointF(25, 20)]))


def _icon_redo(p, fg, accent):
    p.translate(100, 0)
    p.scale(-1, 1)
    _icon_undo(p, fg, accent)


def _icon_trash(p, fg, accent):
    p.setPen(_pen(fg, 7))
    p.setBrush(accent)
    body = QPolygonF([QPointF(26, 34), QPointF(74, 34), QPointF(68, 88), QPointF(32, 88)])
    p.drawPolygon(body)
    p.drawLine(QPointF(16, 26), QPointF(84, 26))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPolyline(QPolygonF([QPointF(40, 26), QPointF(40, 14), QPointF(60, 14), QPointF(60, 26)]))
    p.drawLine(QPointF(42, 46), QPointF(43, 76))
    p.drawLine(QPointF(58, 46), QPointF(57, 76))


def _icon_plus(p, fg, accent):
    p.setPen(_pen(fg, 14))
    p.drawLine(QPointF(50, 20), QPointF(50, 80))
    p.drawLine(QPointF(20, 50), QPointF(80, 50))


def _icon_minus(p, fg, accent):
    p.setPen(_pen(fg, 14))
    p.drawLine(QPointF(20, 50), QPointF(80, 50))


def _icon_close(p, fg, accent):
    p.setPen(_pen(fg, 14))
    p.drawLine(QPointF(24, 24), QPointF(76, 76))
    p.drawLine(QPointF(76, 24), QPointF(24, 76))


def _icon_check(p, fg, accent):
    p.setPen(_pen(fg, 14))
    p.drawPolyline(QPolygonF([QPointF(20, 54), QPointF(42, 76), QPointF(82, 28)]))


def _icon_circle(p, fg, accent):
    p.setPen(_pen(fg, 7))
    p.setBrush(accent)
    p.drawEllipse(QPointF(50, 50), 34, 34)


def _icon_rect(p, fg, accent):
    p.setPen(_pen(fg, 7))
    p.setBrush(accent)
    p.drawRect(QRectF(14, 26, 72, 48))


def _icon_star(p, fg, accent):
    p.setPen(_pen(fg, 6))
    p.setBrush(accent)
    p.drawPolygon(QPolygonF(star_points(50, 54, 42, 17)))


_ICONS = {
    "camera": _icon_camera, "nocamera": _icon_nocamera, "brush": _icon_brush,
    "fill": _icon_fill, "stamp": _icon_stamp, "select": _icon_select,
    "undo": _icon_undo, "redo": _icon_redo, "trash": _icon_trash,
    "plus": _icon_plus, "minus": _icon_minus, "close": _icon_close,
    "check": _icon_check, "circle": _icon_circle, "rect": _icon_rect,
    "star": _icon_star,
}


def paint_icon(painter: QPainter, kind: str, rect: QRectF,
               fg: QColor, accent: QColor) -> None:
    """Draw the named icon into *rect* using the 100x100 design grid."""
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.translate(rect.topLeft())
    painter.scale(rect.width() / 100.0, rect.height() / 100.0)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    _ICONS[kind](painter, QColor(fg), QColor(accent))
    painter.restore()


# --------------------------------------------------------------------------- #
# IconButton
# --------------------------------------------------------------------------- #
class IconButton(QAbstractButton):
    """Large icon-only button.

    States
    ------
    normal   white, thick black border
    hover    pale-yellow fill + thicker border
    pressed  amber fill, icon nudged down
    active   deep-blue fill, yellow ring, white icon + yellow check badge
    focus    dashed cyan outline (keyboard users)
    disabled grey
    """

    VARIANTS = {
        "default": dict(bg=Theme.PAPER, hover=Theme.HOVER_BG, fg=Theme.INK),
        "primary": dict(bg="#FFB300", hover="#FFCA28", fg=Theme.INK),
        "danger":  dict(bg="#E53935", hover="#EF5350", fg="#FFFFFF"),
        "confirm": dict(bg="#43A047", hover="#66BB6A", fg="#FFFFFF"),
    }

    def __init__(self, icon: str, size: int = Theme.BUTTON, *,
                 accent: Optional[str] = None, description: str = "",
                 checkable: bool = False, variant: str = "default",
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        size = max(size, Theme.MIN_TARGET)
        self._icon = icon
        self._variant = variant
        self._accent = QColor(accent or "#FFB300")
        self.setCheckable(checkable)
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setToolTip(description)
        self.setAccessibleName(description or icon)

    def sizeHint(self) -> QSize:
        return QSize(self.width(), self.height())

    # -- hook so SizeDot can draw something other than a named icon ---------- #
    def _paint_glyph(self, p: QPainter, rect: QRectF, fg: QColor, accent: QColor):
        paint_icon(p, self._icon, rect, fg, accent)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        v = self.VARIANTS[self._variant]
        enabled, checked = self.isEnabled(), self.isChecked()
        down, hover = self.isDown(), self.underMouse()

        if not enabled:
            bg, border, fg, accent, bw = (QColor(Theme.DISABLED_BG), QColor(Theme.DISABLED_FG),
                                          QColor(Theme.DISABLED_FG), QColor(Theme.DISABLED_BG), 3)
        elif checked:
            bg, border = QColor(Theme.ACTIVE_BG), QColor(Theme.ACTIVE_RING)
            fg, accent, bw = QColor("#FFFFFF"), QColor(Theme.ACTIVE_RING), 7
        else:
            bg = QColor(Theme.PRESS_BG if down else (v["hover"] if hover else v["bg"]))
            border, fg, accent = QColor(Theme.INK), QColor(v["fg"]), QColor(self._accent)
            bw = 6 if hover else 4

        rect = QRectF(self.rect()).adjusted(5, 5, -5, -5)
        p.setPen(QPen(border, bw))
        p.setBrush(bg)
        p.drawRoundedRect(rect, 18, 18)

        pad = rect.width() * 0.16
        glyph = rect.adjusted(pad, pad, -pad, -pad)
        if down:
            glyph.translate(0, 2)
        self._paint_glyph(p, glyph, fg, accent)

        if checked and enabled:  # check badge: not colour-only feedback
            c = QPointF(self.width() - 17, 17)
            p.setPen(QPen(QColor(Theme.INK), 3))
            p.setBrush(QColor(Theme.ACTIVE_RING))
            p.drawEllipse(c, 11, 11)
            p.setPen(_pen(Theme.INK, 3.5))
            p.drawPolyline(QPolygonF([QPointF(c.x() - 5, c.y()), QPointF(c.x() - 1, c.y() + 4),
                                      QPointF(c.x() + 6, c.y() - 4)]))

        if self.hasFocus() and enabled:
            pen = QPen(QColor(Theme.FOCUS), 3, Qt.PenStyle.DashLine)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5), 20, 20)

    def keyPressEvent(self, e: QKeyEvent):
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.click()
        else:
            super().keyPressEvent(e)


class SizeDot(IconButton):
    """Checkable button showing a dot of a given diameter (brush size)."""

    def __init__(self, diameter: int, description: str, parent: Optional[QWidget] = None):
        super().__init__("circle", Theme.MIN_TARGET + 8, checkable=True,
                         description=description, parent=parent)
        self.diameter = diameter

    def _paint_glyph(self, p, rect, fg, accent):
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(fg)
        shown = 8 + (rect.width() - 8) * (self.diameter / 40.0)
        p.drawEllipse(rect.center(), shown / 2, shown / 2)


class SizePicker(QWidget):
    """Four dots of increasing size.  Emits the chosen stroke width in px."""

    sizeChanged = pyqtSignal(int)
    SIZES = (4, 10, 22, 40)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._dots: List[SizeDot] = []
        for i, size in enumerate(self.SIZES):
            dot = SizeDot(size, "Brush size %d" % (i + 1))
            dot.clicked.connect(lambda _=False, s=size: self.sizeChanged.emit(s))
            self._group.addButton(dot)
            lay.addWidget(dot)
            self._dots.append(dot)
        self._dots[1].setChecked(True)

    def current_size(self) -> int:
        for dot in self._dots:
            if dot.isChecked():
                return dot.diameter
        return self.SIZES[1]


# --------------------------------------------------------------------------- #
# ColorPalette
# --------------------------------------------------------------------------- #
class ColorSwatch(QAbstractButton):
    """Bold circular colour button. Selected = double ring + check mark."""

    def __init__(self, name: str, hex_color: str, size: int = Theme.SWATCH,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.color = QColor(hex_color)
        self.setCheckable(True)
        self.setFixedSize(max(size, Theme.MIN_TARGET), max(size, Theme.MIN_TARGET))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setToolTip(name)
        self.setAccessibleName(name + " colour")

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QPointF(self.width() / 2, self.height() / 2)
        radius = min(self.width(), self.height()) / 2 - 3
        base = radius if (self.isChecked() or self.underMouse()) else radius - 3
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(Theme.INK))
        p.drawEllipse(c, base, base)
        if self.isChecked():
            p.setBrush(QColor("#FFFFFF"))
            p.drawEllipse(c, base - 4, base - 4)
            p.setBrush(self.color)
            p.drawEllipse(c, base - 9, base - 9)
            p.setPen(_pen(_contrast(self.color), 6))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPolyline(QPolygonF([QPointF(c.x() - 11, c.y() + 1), QPointF(c.x() - 3, c.y() + 10),
                                      QPointF(c.x() + 12, c.y() - 9)]))
        else:
            p.setBrush(self.color)
            p.drawEllipse(c, base - 3, base - 3)
        if self.hasFocus():
            p.setPen(QPen(QColor(Theme.FOCUS), 3, Qt.PenStyle.DashLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(c, radius + 1, radius + 1)

    def keyPressEvent(self, e: QKeyEvent):
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.click()
        else:
            super().keyPressEvent(e)


class ColorPalette(QWidget):
    """Eight circular swatches in a grid; emits ``colorChanged(QColor)``."""

    colorChanged = pyqtSignal(QColor)

    def __init__(self, columns: int = 2, parent: Optional[QWidget] = None):
        super().__init__(parent)
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(12)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._swatches: List[ColorSwatch] = []
        for i, (name, hex_color) in enumerate(PALETTE_COLORS):
            sw = ColorSwatch(name, hex_color)
            sw.clicked.connect(lambda _=False, s=sw: self.colorChanged.emit(QColor(s.color)))
            self._group.addButton(sw)
            grid.addWidget(sw, i // columns, i % columns)
            self._swatches.append(sw)
        self._swatches[0].setChecked(True)

    def current_color(self) -> QColor:
        for sw in self._swatches:
            if sw.isChecked():
                return QColor(sw.color)
        return QColor(self._swatches[0].color)


# --------------------------------------------------------------------------- #
# Draggable / scalable stamps
# --------------------------------------------------------------------------- #
class ShapeItem(QGraphicsItem):
    """Vector stamp (circle / rect / star) centred on its own origin.

    When selected it shows a dashed frame and a yellow resize handle on the
    bottom-right corner.  The *view* implements the handle drag.
    """

    KINDS = ("circle", "rect", "star")
    HALF = 50.0

    def __init__(self, kind: str, color: QColor):
        super().__init__()
        self.kind = kind
        self._color = QColor(color)
        self._path = self._build_path(kind)
        self._box = self._path.boundingRect()
        self.setZValue(10)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)

    @classmethod
    def _build_path(cls, kind: str) -> QPainterPath:
        r = cls.HALF
        path = QPainterPath()
        if kind == "circle":
            path.addEllipse(QPointF(0, 0), r, r)
        elif kind == "rect":
            path.addRoundedRect(QRectF(-r, -r * 0.7, 2 * r, 1.4 * r), 6, 6)
        else:
            path.addPolygon(QPolygonF(star_points(0, 4, r, r * 0.4)))
            path.closeSubpath()
        return path

    @property
    def color(self) -> QColor:
        return QColor(self._color)

    def set_color(self, color: QColor) -> None:
        self._color = QColor(color)
        self.update()

    def handle_point(self) -> QPointF:
        return self._box.bottomRight()

    def boundingRect(self) -> QRectF:
        m = self.HALF + 40
        return QRectF(-m, -m, 2 * m, 2 * m)

    def shape(self) -> QPainterPath:  # generous hit-box = whole bounding box
        path = QPainterPath()
        path.addRect(self._box)
        return path

    def paint(self, painter: QPainter, _option, _widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        outline = QPen(QColor(Theme.INK), 3)
        outline.setCosmetic(True)
        outline.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(outline)
        painter.setBrush(self._color)
        painter.drawPath(self._path)

        if self.isSelected():
            frame = QPen(QColor(Theme.FOCUS), 4, Qt.PenStyle.DashLine)
            frame.setCosmetic(True)
            painter.setPen(frame)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self._box.adjusted(-4, -4, 4, 4))
            lod = painter.worldTransform().m11() or 1.0
            radius = min(16.0 / lod, 38.0)
            ring = QPen(QColor(Theme.INK), 3)
            ring.setCosmetic(True)
            painter.setPen(ring)
            painter.setBrush(QColor(Theme.ACTIVE_RING))
            painter.drawEllipse(self.handle_point(), radius, radius)


# --------------------------------------------------------------------------- #
# CanvasView
# --------------------------------------------------------------------------- #
class CanvasView(QGraphicsView):
    """Drawing surface.  Interprets mouse input according to the active Tool
    and reports *intent* through signals; the controller owns undo history.
    """

    strokeFinished = pyqtSignal(QPainterPath, QColor, float)
    fillRequested = pyqtSignal(int, int)
    stampRequested = pyqtSignal(QPointF)
    itemsMoved = pyqtSignal(list)            # [(item, old_pos, new_pos), ...]
    itemScaled = pyqtSignal(object, float, float)  # item, old, new
    deleteRequested = pyqtSignal()
    shapeSelectionChanged = pyqtSignal()

    MIN_SCALE, MAX_SCALE = 0.2, 10.0
    HANDLE_HIT_PX = 32

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._bg_item = QGraphicsPixmapItem()
        self._bg_item.setZValue(-100)
        self._scene.addItem(self._bg_item)
        self._canvas_rect = QRectF(0, 0, 900, 675)

        self._tool = Tool.BRUSH
        self._brush_color = QColor("#E53935")
        self._brush_width = 10.0

        self._preview: Optional[QGraphicsPathItem] = None
        self._stroke_path = QPainterPath()
        self._stroke_pts: List[QPointF] = []

        self._press_positions: dict = {}
        self._scaling = None  # (item, start_scale, start_distance, old_scale)

        self.setRenderHints(QPainter.RenderHint.Antialiasing |
                            QPainter.RenderHint.SmoothPixmapTransform)
        self.setBackgroundBrush(QBrush(QColor(Theme.CANVAS_BG)))
        self.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.setMinimumSize(480, 360)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAccessibleName("Drawing canvas")
        self._scene.selectionChanged.connect(self.shapeSelectionChanged)
        self._apply_cursor()

    # ----------------------------- configuration --------------------------- #
    @property
    def canvas_rect(self) -> QRectF:
        return QRectF(self._canvas_rect)

    def set_tool(self, tool: Tool) -> None:
        self._tool = tool
        interactive = tool == Tool.SELECT
        for item in self.shape_items():
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, interactive)
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, interactive)
        if not interactive:
            self._scene.clearSelection()
        self._apply_cursor()

    def set_brush(self, color: QColor, width: float) -> None:
        self._brush_color = QColor(color)
        self._brush_width = float(width)

    def set_background(self, image) -> None:
        """Show a QImage as the page; resizes the canvas if its size changed."""
        pix = QPixmap.fromImage(image)
        self._bg_item.setPixmap(pix)
        new_rect = QRectF(0, 0, pix.width(), pix.height())
        if new_rect != self._canvas_rect:
            self._canvas_rect = new_rect
            self._scene.setSceneRect(new_rect.adjusted(-80, -80, 80, 80))
            self.fit_canvas()

    def fit_canvas(self) -> None:
        self.fitInView(self._canvas_rect.adjusted(-16, -16, 16, 16),
                       Qt.AspectRatioMode.KeepAspectRatio)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fit_canvas()

    def _apply_cursor(self) -> None:
        shape = {Tool.BRUSH: Qt.CursorShape.CrossCursor,
                 Tool.STAMP: Qt.CursorShape.CrossCursor,
                 Tool.FILL: Qt.CursorShape.PointingHandCursor}.get(
            self._tool, Qt.CursorShape.ArrowCursor)
        self.viewport().setCursor(shape)

    # ------------------------------ scene items ---------------------------- #
    def shape_items(self) -> List[ShapeItem]:
        return [i for i in self._scene.items() if isinstance(i, ShapeItem)]

    def selected_shapes(self) -> List[ShapeItem]:
        return [i for i in self._scene.selectedItems() if isinstance(i, ShapeItem)]

    def annotation_items(self) -> list:
        """Every vector item (strokes + stamps), excluding background/preview."""
        return [i for i in self._scene.items()
                if i is not self._bg_item and i is not self._preview]

    def add_item(self, item: QGraphicsItem) -> None:
        if item.scene() is not self._scene:
            self._scene.addItem(item)
        if isinstance(item, ShapeItem):
            interactive = self._tool == Tool.SELECT
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, interactive)
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, interactive)

    def remove_item(self, item: QGraphicsItem) -> None:
        if item.scene() is self._scene:
            self._scene.removeItem(item)

    def make_stroke_item(self, path: QPainterPath, color: QColor, width: float) -> QGraphicsPathItem:
        item = QGraphicsPathItem(path)
        item.setPen(_pen(color, width))
        item.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        item.setZValue(5)
        return item

    # -------------------------------- mouse -------------------------------- #
    def _scene_pos(self, event) -> QPointF:
        return self.mapToScene(event.position().toPoint())

    def _clamped(self, pos: QPointF) -> QPointF:
        r = self._canvas_rect
        return QPointF(min(max(pos.x(), r.left()), r.right()),
                       min(max(pos.y(), r.top()), r.bottom()))

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            event.ignore()
            return
        pos = self._scene_pos(event)
        inside = self._canvas_rect.contains(pos)

        if self._tool == Tool.BRUSH:
            if inside:
                self._begin_stroke(pos)
            event.accept()
        elif self._tool == Tool.FILL:
            if inside:
                self.fillRequested.emit(int(pos.x()), int(pos.y()))
            event.accept()
        elif self._tool == Tool.STAMP:
            if inside:
                self.stampRequested.emit(pos)
            event.accept()
        elif self._tool == Tool.SELECT:
            hit = self._handle_hit(event.position().toPoint())
            if hit is not None:
                dist = max(1.0, math.hypot(pos.x() - hit.scenePos().x(),
                                           pos.y() - hit.scenePos().y()))
                self._scaling = (hit, hit.scale(), dist)
                event.accept()
                return
            self._press_positions = {i: QPointF(i.pos()) for i in self.shape_items()}
            super().mousePressEvent(event)
        else:
            event.ignore()

    def mouseMoveEvent(self, event):
        pos = self._scene_pos(event)
        if self._tool == Tool.BRUSH and self._preview is not None:
            self._extend_stroke(self._clamped(pos))
            event.accept()
        elif self._tool == Tool.SELECT and self._scaling is not None:
            item, start_scale, start_dist = self._scaling
            dist = math.hypot(pos.x() - item.scenePos().x(), pos.y() - item.scenePos().y())
            item.setScale(min(max(start_scale * dist / start_dist, self.MIN_SCALE), self.MAX_SCALE))
            event.accept()
        elif self._tool == Tool.SELECT:
            super().mouseMoveEvent(event)
        else:
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            event.ignore()
            return
        if self._tool == Tool.BRUSH and self._preview is not None:
            self._finish_stroke()
            event.accept()
        elif self._tool == Tool.SELECT and self._scaling is not None:
            item, start_scale, _ = self._scaling
            self._scaling = None
            if abs(item.scale() - start_scale) > 1e-6:
                self.itemScaled.emit(item, start_scale, item.scale())
            event.accept()
        elif self._tool == Tool.SELECT:
            super().mouseReleaseEvent(event)
            moves = [(i, old, QPointF(i.pos())) for i, old in self._press_positions.items()
                     if i.pos() != old]
            self._press_positions = {}
            if moves:
                self.itemsMoved.emit(moves)
        else:
            event.accept()

    def wheelEvent(self, event):
        shapes = self.selected_shapes() if self._tool == Tool.SELECT else []
        if not shapes:
            event.ignore()
            return
        factor = 1.1 if event.angleDelta().y() > 0 else 1 / 1.1
        item = shapes[0]
        old = item.scale()
        new = min(max(old * factor, self.MIN_SCALE), self.MAX_SCALE)
        if new != old:
            self.itemScaled.emit(item, old, new)
        event.accept()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.deleteRequested.emit()
            event.accept()
        else:
            super().keyPressEvent(event)

    # ------------------------------ resize handle -------------------------- #
    def _handle_hit(self, view_pos) -> Optional[ShapeItem]:
        for item in self.selected_shapes():
            hp = self.mapFromScene(item.mapToScene(item.handle_point()))
            if math.hypot(hp.x() - view_pos.x(), hp.y() - view_pos.y()) <= self.HANDLE_HIT_PX:
                return item
        return None

    # ------------------------------ smooth strokes ------------------------- #
    def _begin_stroke(self, pos: QPointF) -> None:
        self._stroke_pts = [pos]
        self._stroke_path = QPainterPath(pos)
        self._preview = self.make_stroke_item(QPainterPath(), self._brush_color, self._brush_width)
        self._preview.setZValue(20)
        self._scene.addItem(self._preview)
        self._refresh_preview()

    def _extend_stroke(self, pos: QPointF) -> None:
        last = self._stroke_pts[-1]
        if math.hypot(pos.x() - last.x(), pos.y() - last.y()) < 1.5:
            return
        mid = QPointF((last.x() + pos.x()) / 2, (last.y() + pos.y()) / 2)
        # Quadratic Bezier through midpoints => smooth curve, no jaggies.
        self._stroke_path.quadTo(last, mid)
        self._stroke_pts.append(pos)
        self._refresh_preview()

    def _final_path(self) -> QPainterPath:
        last = self._stroke_pts[-1]
        path = QPainterPath(self._stroke_path)
        path.lineTo(last.x() + (0.01 if len(self._stroke_pts) == 1 else 0), last.y())
        return path

    def _refresh_preview(self) -> None:
        if self._preview is not None:
            self._preview.setPath(self._final_path())

    def _finish_stroke(self) -> None:
        path = self._final_path()
        self._scene.removeItem(self._preview)
        self._preview = None
        self._stroke_pts = []
        self.strokeFinished.emit(path, QColor(self._brush_color), self._brush_width)


# --------------------------------------------------------------------------- #
# CameraDialog
# --------------------------------------------------------------------------- #
class CameraDialog(QDialog):
    """Live webcam preview with a huge shutter button and a big red close button.

    *frame_source*  -> callable returning the latest frame (or None)
    *to_qimage*     -> callable converting that frame to a QImage
    After ``exec()`` returns Accepted, ``captured_frame`` holds the photo.
    """

    def __init__(self, frame_source: Callable[[], Optional[object]],
                 to_qimage: Callable[[object], object],
                 camera_available: bool = True,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Camera")
        self.setModal(True)
        self.captured_frame = None
        self._frame_source = frame_source
        self._to_qimage = to_qimage
        self._last_frame = None
        self._misses = 0
        self._available = camera_available

        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(560, 420)
        self.preview.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.preview.setStyleSheet(f"background:#000; border:8px solid {Theme.INK}; border-radius:14px;")
        self.preview.setAccessibleName("Camera preview")

        self.cancel_btn = IconButton("close", 96, variant="danger", description="Close camera")
        self.shutter_btn = IconButton("camera", 120, variant="confirm", description="Take photo")
        self.cancel_btn.clicked.connect(self.reject)
        self.shutter_btn.clicked.connect(self._take_photo)
        self.shutter_btn.setEnabled(camera_available)

        row = QHBoxLayout()
        row.addWidget(self.cancel_btn)
        row.addStretch(1)
        row.addWidget(self.shutter_btn)
        row.addStretch(1)
        row.addSpacing(self.cancel_btn.width())  # keeps the shutter centred

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(14)
        root.addWidget(self.preview, 1)
        root.addLayout(row)
        self.resize(760, 680)

        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._tick)
        if camera_available:
            self._timer.start()
        else:
            self._show_no_camera()

    def _show_no_camera(self) -> None:
        self._available = False
        self.shutter_btn.setEnabled(False)
        side = 280
        pix = QPixmap(side, side)
        pix.fill(QColor("#000000"))
        painter = QPainter(pix)
        paint_icon(painter, "nocamera", QRectF(40, 40, side - 80, side - 80),
                   QColor("#FFFFFF"), QColor("#90A4AE"))
        painter.end()
        self.preview.setPixmap(pix)

    def _tick(self) -> None:
        frame = self._frame_source()
        if frame is None:
            self._misses += 1
            if self._misses > 90:  # ~3 s without a frame
                self._timer.stop()
                self._show_no_camera()
            return
        self._misses = 0
        self._last_frame = frame
        pix = QPixmap.fromImage(self._to_qimage(frame)).scaled(
            self.preview.size(), Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation)
        self.preview.setPixmap(pix)

    def _take_photo(self) -> None:
        if self._last_frame is None:
            return
        self.captured_frame = self._last_frame.copy()
        self.accept()

    def done(self, result: int) -> None:
        self._timer.stop()
        super().done(result)
