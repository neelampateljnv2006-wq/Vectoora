"""
canvas.py - Vector Engine with Stencil Scaling & Pen Auto-Fill Support
"""
import math
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QPainterPath, QPolygonF, QTransform
)
from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsItem, QGraphicsPathItem
)
from constants import Tool

HANDLE_SZ = 10
ROT_DIST = 26

class Handle:
    NONE = 0
    TL = 1; TM = 2; TR = 3; MR = 4; BR = 5; BM = 6; BL = 7; ML = 8; ROT = 9

class VectorGraphicItem(QGraphicsPathItem):
    def __init__(self, kind: str, name: str, fill_color: QColor, stroke_color: QColor = QColor("#1E2D44"), stroke_w: int = 2, emoji_char: str = "", custom_path: QPainterPath = None):
        super().__init__()
        self.kind = kind
        self.item_name = name
        self.fill_color = fill_color
        self.stroke_color = stroke_color
        self.stroke_w = stroke_w
        self.emoji_char = emoji_char
        self.opacity_val = 1.0
        self.is_locked = False
        self.keep_aspect_ratio = False
        
        self.box_w = 140.0
        self.box_h = 140.0
        self.base_path = custom_path

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        if custom_path:
            self.setPath(custom_path)
            self.setBrush(QBrush(self.fill_color))
            self.setPen(QPen(self.stroke_color, self.stroke_w))
            r = custom_path.boundingRect()
            self.box_w = max(15.0, r.width())
            self.box_h = max(15.0, r.height())
        else:
            self._rebuild_path()

    def _rebuild_path(self):
        w = max(15.0, self.box_w)
        h = max(15.0, self.box_h)
        hw, hh = w / 2.0, h / 2.0

        if self.base_path is not None:
            r = self.base_path.boundingRect()
            if r.width() > 0 and r.height() > 0:
                sx = w / r.width()
                sy = h / r.height()
                t = QTransform()
                t.translate(-hw, -hh)
                t.scale(sx, sy)
                t.translate(-r.left(), -r.top())
                scaled_path = t.map(self.base_path)
                self.setPath(scaled_path)
                self.setBrush(QBrush(self.fill_color))
                self.setPen(QPen(self.stroke_color, self.stroke_w))
                return

        p = QPainterPath()
        if self.kind == "rect":
            p.addRoundedRect(-hw, -hh, w, h, 8, 8)
        elif self.kind == "circle":
            p.addEllipse(-hw, -hh, w, h)
        elif self.kind == "heart":
            p.moveTo(0, hh * 0.4)
            p.cubicTo(-hw * 1.1, -hh * 0.4, -hw * 0.6, -hh * 1.1, 0, -hh * 0.5)
            p.cubicTo(hw * 0.6, -hh * 1.1, hw * 1.1, -hh * 0.4, 0, hh * 0.4)
        elif self.kind == "star":
            pts = []
            for i in range(10):
                r = hw if i % 2 == 0 else hw * 0.42
                ang = math.radians(i * 36 - 90)
                pts.append(QPointF(r * math.cos(ang), (hh / hw) * r * math.sin(ang)))
            p.addPolygon(QPolygonF(pts)); p.closeSubpath()
        else:
            p.addEllipse(-hw, -hh, w, h)

        self.setPath(p)
        self.setBrush(QBrush(self.fill_color))
        self.setPen(QPen(self.stroke_color, self.stroke_w))

    def set_dimensions(self, width: float, height: float):
        self.box_w = max(15.0, width)
        self.box_h = max(15.0, height)
        self._rebuild_path()
        self.update()

    def set_fill(self, color: QColor):
        self.fill_color = color
        self.setBrush(QBrush(color))
        self.update()

    def set_stroke_width(self, width: int):
        self.stroke_w = width
        self.setPen(QPen(self.stroke_color, width))
        self.update()

    def set_stroke_color(self, color: QColor):
        self.stroke_color = color
        self.setPen(QPen(color, self.stroke_w))
        self.update()

    def set_opacity_val(self, val: float):
        self.opacity_val = val
        self.setOpacity(val)
        self.update()

    def set_locked(self, locked: bool):
        self.is_locked = locked
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, not locked)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, not locked)

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "item_name": self.item_name,
            "x": float(self.pos().x()),
            "y": float(self.pos().y()),
            "width": float(self.box_w),
            "height": float(self.box_h),
            "rotation": float(self.rotation()),
            "fill_color": self.fill_color.name(QColor.NameFormat.HexArgb),
            "stroke_color": self.stroke_color.name(),
            "stroke_w": int(self.stroke_w),
            "opacity": float(self.opacity_val),
            "is_locked": bool(self.is_locked),
            "keep_aspect_ratio": bool(self.keep_aspect_ratio),
            "emoji_char": self.emoji_char
        }

    @staticmethod
    def from_dict(data: dict) -> "VectorGraphicItem":
        item = VectorGraphicItem(
            kind=data.get("kind", "rect"),
            name=data.get("item_name", "Layer"),
            fill_color=QColor(data.get("fill_color", "#00000000")),
            stroke_color=QColor(data.get("stroke_color", "#1E2D44")),
            stroke_w=int(data.get("stroke_w", 2)),
            emoji_char=data.get("emoji_char", "")
        )
        item.set_dimensions(float(data.get("width", 120.0)), float(data.get("height", 120.0)))
        item.setPos(float(data.get("x", 0.0)), float(data.get("y", 0.0)))
        item.setRotation(float(data.get("rotation", 0.0)))
        item.set_opacity_val(float(data.get("opacity", 1.0)))
        item.set_locked(bool(data.get("is_locked", False)))
        item.keep_aspect_ratio = bool(data.get("keep_aspect_ratio", False))
        return item

    def get_handles_map(self):
        r = self.boundingRect()
        s = HANDLE_SZ
        h_half = s / 2.0
        return {
            Handle.TL: QRectF(r.left() - h_half, r.top() - h_half, s, s),
            Handle.TM: QRectF(r.center().x() - h_half, r.top() - h_half, s, s),
            Handle.TR: QRectF(r.right() - h_half, r.top() - h_half, s, s),
            Handle.MR: QRectF(r.right() - h_half, r.center().y() - h_half, s, s),
            Handle.BR: QRectF(r.right() - h_half, r.bottom() - h_half, s, s),
            Handle.BM: QRectF(r.center().x() - h_half, r.bottom() - h_half, s, s),
            Handle.BL: QRectF(r.left() - h_half, r.bottom() - h_half, s, s),
            Handle.ML: QRectF(r.left() - h_half, r.center().y() - h_half, s, s),
            Handle.ROT: QRectF(r.center().x() - 6, r.top() - ROT_DIST - 6, 12, 12)
        }

    def hit_test_handle(self, item_pos: QPointF) -> int:
        if not self.isSelected() or self.is_locked:
            return Handle.NONE
        m = self.get_handles_map()
        for h_type, rect in m.items():
            if rect.contains(item_pos):
                return h_type
        return Handle.NONE

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        if self.isSelected() and not self.is_locked:
            painter.setPen(QPen(QColor("#A3E635"), 1.5, Qt.PenStyle.SolidLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            r = self.boundingRect()
            painter.drawRect(r)

            rot_pt = QPointF(r.center().x(), r.top() - ROT_DIST)
            painter.setPen(QPen(QColor("#A3E635"), 1.5, Qt.PenStyle.DashLine))
            painter.drawLine(QPointF(r.center().x(), r.top()), rot_pt)
            painter.setBrush(QBrush(QColor("#070B11")))
            painter.setPen(QPen(QColor("#A3E635"), 2))
            painter.drawEllipse(rot_pt, 6, 6)

            painter.setBrush(QBrush(QColor("#FFFFFF")))
            painter.setPen(QPen(QColor("#A3E635"), 1.5))
            m = self.get_handles_map()
            for h_code in range(1, 9):
                painter.drawRect(m[h_code])

    def itemChange(self, change, value):
        if change in (QGraphicsItem.GraphicsItemChange.ItemPositionChange, 
                      QGraphicsItem.GraphicsItemChange.ItemTransformChange):
            scene = self.scene()
            if scene and hasattr(scene, "views") and scene.views():
                v = scene.views()[0]
                if hasattr(v, "_emit_transform_event"):
                    v._emit_transform_event(self)
        return super().itemChange(change, value)


class VectooraCanvasView(QGraphicsView):
    itemSelectedSignal = pyqtSignal(object)
    itemTransformSignal = pyqtSignal(float, float, float, float, float)
    shapeCountChanged = pyqtSignal(int, int)
    layersChangedSignal = pyqtSignal(list)
    canvasModifiedSignal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        self.current_tool = Tool.SELECT
        self.active_color = QColor("#A3E635")
        self.stroke_color = QColor("#1E2D44")
        self.active_stroke_width = 2
        
        self.pen_points = []
        self.live_pen_item = None

        self.lasso_path = None
        self.lasso_item = None

        self.active_handle = Handle.NONE
        self.active_item = None
        self.start_mouse_scene = QPointF(0, 0)
        self.start_dim = (140.0, 140.0)

        self.setStyleSheet("background-color: #06090F; border: none;")
        self.scene.setSceneRect(-800, -800, 1600, 1600)
        self.setMouseTracking(True)

        self._create_sample_artboard()
        self.scene.selectionChanged.connect(self._on_selection_changed)

    def _create_sample_artboard(self):
        disc = VectorGraphicItem("circle", "Backdrop Circle", QColor("#EAF5DF"), stroke_w=0)
        disc.set_dimensions(260, 260); disc.setPos(0, 0); self.scene.addItem(disc)

        flower = VectorGraphicItem("heart", "Heart Blossom", QColor("#F43F5E"), stroke_color=QColor("#881337"), stroke_w=2)
        flower.set_dimensions(160, 160); flower.setPos(0, -10); self.scene.addItem(flower)

        s1 = VectorGraphicItem("star", "Star Sparkle L", QColor("#C6E872"), stroke_w=0)
        s1.set_dimensions(60, 60); s1.setPos(-170, -10); self.scene.addItem(s1)

        s2 = VectorGraphicItem("diamond", "Diamond Sparkle", QColor("#38BDF8"), stroke_w=0)
        s2.set_dimensions(70, 70); s2.setPos(170, -60); self.scene.addItem(s2)

        flower.setSelected(True)
        self._notify_layers_updated()

    def set_tool(self, tool: Tool):
        self.current_tool = tool
        is_select = (tool == Tool.SELECT)
        for it in self.scene.items():
            if isinstance(it, VectorGraphicItem) and not it.is_locked:
                it.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, is_select)
                it.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, is_select or tool == Tool.BUCKET)
        if not is_select and tool != Tool.BUCKET:
            self.scene.clearSelection()

    def add_shape_by_type(self, shape_type: str, pos: QPointF = QPointF(0, 0)):
        name = f"{shape_type.capitalize()} Object"
        item = VectorGraphicItem(shape_type, name, self.active_color, self.stroke_color, self.active_stroke_width)
        item.setPos(pos)
        self.scene.addItem(item)
        self.scene.clearSelection()
        item.setSelected(True)
        self._notify_layers_updated()
        self.canvasModifiedSignal.emit()
        return item

    def _emit_transform_event(self, item):
        if item == self.selected_item():
            r = item.boundingRect()
            self.itemTransformSignal.emit(
                item.pos().x(), item.pos().y(),
                r.width() * abs(item.scale()), r.height() * abs(item.scale()),
                item.rotation()
            )
            self.canvasModifiedSignal.emit()

    def selected_item(self):
        sel = self.scene.selectedItems()
        return sel[0] if sel and isinstance(sel[0], VectorGraphicItem) else None

    def _on_selection_changed(self):
        selected = self.scene.selectedItems()
        total = len([i for i in self.scene.items() if isinstance(i, VectorGraphicItem)])
        self.shapeCountChanged.emit(total, len(selected))
        it = self.selected_item()
        if it:
            r = it.boundingRect()
            self.itemSelectedSignal.emit(it)
            self.itemTransformSignal.emit(
                it.pos().x(), it.pos().y(),
                r.width() * abs(it.scale()), r.height() * abs(it.scale()),
                it.rotation()
            )
        else:
            self.itemSelectedSignal.emit(None)

    def _notify_layers_updated(self):
        items = [i for i in self.scene.items() if isinstance(i, VectorGraphicItem)]
        self.layersChangedSignal.emit(items)
        self._on_selection_changed()

    def mousePressEvent(self, event):
        scene_pos = self.mapToScene(event.pos())
        sel_item = self.selected_item()

        if self.current_tool == Tool.SELECT and sel_item:
            item_pos = sel_item.mapFromScene(scene_pos)
            h = sel_item.hit_test_handle(item_pos)
            if h != Handle.NONE:
                self.active_handle = h
                self.active_item = sel_item
                self.start_mouse_scene = scene_pos
                self.start_dim = (sel_item.box_w, sel_item.box_h)
                sel_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
                return

        if event.button() == Qt.MouseButton.LeftButton:
            # 🪣 PAINT BUCKET
            if self.current_tool == Tool.BUCKET:
                it = self.itemAt(event.pos())
                if it and isinstance(it, VectorGraphicItem):
                    it.set_fill(self.active_color)
                    self.scene.clearSelection()
                    it.setSelected(True)
                    self.canvasModifiedSignal.emit()
                return

            # ⭕ LASSO ERASE
            if self.current_tool == Tool.LASSO_ERASE:
                self.lasso_path = QPainterPath(scene_pos)
                pen = QPen(QColor("#F43F5E"), 2, Qt.PenStyle.DashLine)
                brush = QBrush(QColor(244, 63, 94, 40))
                self.lasso_item = self.scene.addPath(self.lasso_path, pen, brush)
                return

            # ✏️ PEN / PENCIL START
            if self.current_tool == Tool.PEN:
                self.pen_points = [scene_pos]
                p = QPainterPath(scene_pos)
                self.live_pen_item = self.scene.addPath(
                    p, 
                    QPen(self.stroke_color, self.active_stroke_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                )
                return

            if self.current_tool in (Tool.RECTANGLE, Tool.CIRCLE, Tool.POLYGON, Tool.LINE):
                shape_map = {
                    Tool.RECTANGLE: "rect", Tool.CIRCLE: "circle",
                    Tool.POLYGON: "hexagon", Tool.LINE: "line"
                }
                self.add_shape_by_type(shape_map[self.current_tool], scene_pos)
                return
            elif self.current_tool == Tool.ERASER:
                it = self.itemAt(event.pos())
                if it and isinstance(it, VectorGraphicItem):
                    self.scene.removeItem(it)
                    self._notify_layers_updated()
                    self.canvasModifiedSignal.emit()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        scene_pos = self.mapToScene(event.pos())
        sel_item = self.selected_item()

        if self.current_tool == Tool.SELECT and sel_item and self.active_handle == Handle.NONE:
            item_pos = sel_item.mapFromScene(scene_pos)
            h = sel_item.hit_test_handle(item_pos)
            if h in (Handle.TL, Handle.BR): self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif h in (Handle.TR, Handle.BL): self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            elif h in (Handle.TM, Handle.BM): self.setCursor(Qt.CursorShape.SizeVerCursor)
            elif h in (Handle.ML, Handle.MR): self.setCursor(Qt.CursorShape.SizeHorCursor)
            elif h == Handle.ROT: self.setCursor(Qt.CursorShape.PointingHandCursor)
            else: self.setCursor(Qt.CursorShape.ArrowCursor)

        if self.active_handle != Handle.NONE and self.active_item:
            t = self.active_item
            if self.active_handle == Handle.ROT:
                d = scene_pos - t.pos()
                angle = math.degrees(math.atan2(d.y(), d.x())) + 90.0
                t.setRotation(angle)
            else:
                diff = scene_pos - self.start_mouse_scene
                rad = math.radians(-t.rotation())
                dx = diff.x() * math.cos(rad) - diff.y() * math.sin(rad)
                dy = diff.x() * math.sin(rad) + diff.y() * math.cos(rad)

                w0, h0 = self.start_dim
                nw, nh = w0, h0

                if self.active_handle in (Handle.MR, Handle.TR, Handle.BR): nw = w0 + dx * 2.0
                elif self.active_handle in (Handle.ML, Handle.TL, Handle.BL): nw = w0 - dx * 2.0

                if self.active_handle in (Handle.BM, Handle.BL, Handle.BR): nh = h0 + dy * 2.0
                elif self.active_handle in (Handle.TM, Handle.TL, Handle.TR): nh = h0 - dy * 2.0

                if t.keep_aspect_ratio and w0 > 0:
                    ratio = h0 / w0
                    if abs(nw - w0) > abs(nh - h0): nh = nw * ratio
                    else: nw = nh / ratio

                t.set_dimensions(max(15.0, nw), max(15.0, nh))

            self._emit_transform_event(t)
            return

        if self.current_tool == Tool.LASSO_ERASE and self.lasso_item and self.lasso_path:
            self.lasso_path.lineTo(scene_pos)
            self.lasso_item.setPath(self.lasso_path)
            return

        if self.current_tool == Tool.PEN and self.live_pen_item:
            self.pen_points.append(scene_pos)
            p = self.live_pen_item.path()
            p.lineTo(scene_pos)
            self.live_pen_item.setPath(p)
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.active_handle != Handle.NONE and self.active_item:
            self.active_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
            self.active_handle = Handle.NONE
            self.active_item = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.canvasModifiedSignal.emit()

        if self.current_tool == Tool.LASSO_ERASE and self.lasso_item and self.lasso_path:
            self.lasso_path.closeSubpath()
            lasso_poly = self.lasso_path.toFillPolygon()
            to_remove = []
            for it in self.scene.items():
                if isinstance(it, VectorGraphicItem):
                    if it.collidesWithPath(self.lasso_path) or lasso_poly.containsPoint(it.pos(), Qt.FillRule.OddEvenFill):
                        to_remove.append(it)
            for it in to_remove:
                self.scene.removeItem(it)
            self.scene.removeItem(self.lasso_item)
            self.lasso_item = None
            self.lasso_path = None
            if to_remove:
                self._notify_layers_updated()
                self.canvasModifiedSignal.emit()
            return

        if self.current_tool == Tool.PEN and self.live_pen_item and len(self.pen_points) > 3:
            start_p = self.pen_points[0]
            end_p = self.pen_points[-1]
            dist = math.hypot(end_p.x() - start_p.x(), end_p.y() - start_p.y())

            self.scene.removeItem(self.live_pen_item)
            self.live_pen_item = None

            final_path = QPainterPath(start_p)
            for pt in self.pen_points[1:]:
                final_path.lineTo(pt)

            is_closed = dist < 35.0
            if is_closed:
                final_path.closeSubpath()
                shape_item = VectorGraphicItem("freehand", "Pencil Shape", self.active_color, self.stroke_color, self.active_stroke_width, custom_path=final_path)
            else:
                shape_item = VectorGraphicItem("line", "Pencil Line", QColor(0, 0, 0, 0), self.stroke_color, self.active_stroke_width, custom_path=final_path)

            self.scene.addItem(shape_item)
            self.pen_points = []
            self._notify_layers_updated()
            self.canvasModifiedSignal.emit()
            return

        super().mouseReleaseEvent(event)

    def drawBackground(self, painter, rect):
        painter.fillRect(rect, QColor("#080D15"))
        painter.setPen(QPen(QColor("#131C29"), 1, Qt.PenStyle.DotLine))
        grid_size = 40
        left = int(rect.left()) - (int(rect.left()) % grid_size)
        top = int(rect.top()) - (int(rect.top()) % grid_size)

        x = left
        while x < rect.right():
            painter.drawLine(int(x), int(rect.top()), int(x), int(rect.bottom()))
            x += grid_size
        y = top
        while y < rect.bottom():
            painter.drawLine(int(rect.left()), int(y), int(rect.right()), int(y))
            y += grid_size
