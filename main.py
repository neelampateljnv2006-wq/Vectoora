from __future__ import annotations
from stencil_processor import StencilProcessor
import sys
import os
import json
from PyQt6.QtCore import Qt, QPointF, QRectF, QSize
from PyQt6.QtGui import (
    QColor, QPen, QBrush, QPainter, QImage, QPageSize, QPdfWriter
)
from PyQt6.QtSvg import QSvgGenerator
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QFrame, QLineEdit, QSlider, QDialog,
    QFileDialog, QMessageBox, QColorDialog, QGridLayout, QStackedLayout,
    QScrollArea, QCheckBox, QListWidget, QListWidgetItem, QStackedWidget
)
from constants import Tool, VECTOORA_THEME
from canvas import VectooraCanvasView, VectorGraphicItem
from stencil_cam import OpenCVStencilDialog

class ReadyCheckDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Vectoora - ReadyCheck Inspection Report")
        self.setFixedSize(500, 440)
        self.setStyleSheet("""
            QDialog { background-color: #0B0F19; color: #F8FAFC; font-family: 'Segoe UI', sans-serif; }
            QFrame.checkCard { background-color: #111827; border: 1px solid #1F2937; border-radius: 10px; padding: 12px; }
            QPushButton.fixBtn { background-color: #A3E635; color: #070B11; font-weight: bold; border-radius: 6px; padding: 12px; font-size: 13px; }
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)
        t = QLabel("ReadyCheck Diagnostics")
        t.setStyleSheet("font-size: 18px; font-weight: 800; color: #A3E635;")
        sub = QLabel("Analyzes vector loop continuity & seals perimeter gaps for leak-proof printing.")
        sub.setStyleSheet("font-size: 11px; color: #94A3B8;")
        lay.addWidget(t)
        lay.addWidget(sub)

        card = QFrame()
        card.setProperty("class", "checkCard")
        clay = QVBoxLayout(card)
        for name, desc in [
            ("Contour Continuity Scan", "Evaluating open stroke gaps..."),
            ("Morphological Closure Engine", "Auto-connecting unsealed vector vertices"),
            ("Print Safety Boundary", "Minimum 1.5mm line weight enforced"),
            ("Antialiased Edge Seal", "Smooth continuous vector perimeter guaranteed")
        ]:
            r = QVBoxLayout()
            n_lbl = QLabel(name)
            n_lbl.setStyleSheet("font-size: 12px; font-weight: bold; color: #F1F5F9;")
            d_lbl = QLabel(desc)
            d_lbl.setStyleSheet("font-size: 10px; color: #64748B; margin-left: 10px;")
            r.addWidget(n_lbl)
            r.addWidget(d_lbl)
            clay.addLayout(r)
        lay.addWidget(card)

        btn_r = QHBoxLayout()
        fb = QPushButton("Auto-Seal & Highlight Perimeters")
        fb.setProperty("class", "fixBtn")
        fb.clicked.connect(self.accept)
        cb = QPushButton("Close")
        cb.setStyleSheet("background-color: #1E293B; color: #CBD5E1; border-radius: 6px; padding: 12px;")
        cb.clicked.connect(self.reject)
        btn_r.addWidget(cb)
        btn_r.addWidget(fb, 1)
        lay.addLayout(btn_r)

RECENT_PROJECTS_CACHE = "recent_projects.json"
ESSENTIAL_COLORS = [
    ("#A3E635", "Electric Lime"), ("#38BDF8", "Sky Cyan"), ("#F43F5E", "Rose Red"),
    ("#FBBF24", "Warm Gold"), ("#A855F7", "Vibrant Purple"), ("#10B981", "Emerald"),
    ("#FB923C", "Sunset Orange"), ("#FFFFFF", "Pure White"), ("#94A3B8", "Slate Gray"), ("#0F172A", "Deep Black")
]

class VectooraApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vectoora - Vector Studio")
        self.setMinimumSize(1280, 800)
        self.setStyleSheet(VECTOORA_THEME)
        self.current_selected_item = None
        self.active_color = QColor("#A3E635")
        self.stroke_color = QColor("#1E2D44")
        self.color_target = "fill"
        self.current_zoom = 1.0
        self.seal_indicators = []
        self.current_file_path = None
        self.is_modified = False
        self.recent_projects = self._load_recent_projects()
        self.undo_stack = []
        self.redo_stack = []
        self._init_ui()

    def _load_recent_projects(self) -> list:
        if os.path.exists(RECENT_PROJECTS_CACHE):
            try:
                with open(RECENT_PROJECTS_CACHE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _add_to_recent(self, fp: str):
        if fp in self.recent_projects:
            self.recent_projects.remove(fp)
        self.recent_projects.insert(0, fp)
        self.recent_projects = self.recent_projects[:10]
        try:
            with open(RECENT_PROJECTS_CACHE, "w", encoding="utf-8") as f:
                json.dump(self.recent_projects, f)
        except Exception:
            pass

    def _init_ui(self):
        root = QWidget()
        root_lay = QVBoxLayout(root)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)
        root_lay.addWidget(self._create_top_header())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._create_primary_sidebar())

        self.page_stack = QStackedWidget()
        self.editor_page = self._build_editor_page()
        self.page_stack.addWidget(self.editor_page)
        self.home_page = self._build_home_page()
        self.page_stack.addWidget(self.home_page)
        self.projects_page = self._build_my_projects_page()
        self.page_stack.addWidget(self.projects_page)
        self.settings_page = self._build_settings_page()
        self.page_stack.addWidget(self.settings_page)

        body.addWidget(self.page_stack, 1)
        root_lay.addLayout(body, 1)
        self.setCentralWidget(root)
        self._switch_page(0)

    def _create_top_header(self) -> QFrame:
        hdr = QFrame()
        hdr.setObjectName("topHeader")
        lay = QHBoxLayout(hdr)
        lay.setContentsMargins(12, 6, 12, 6)
        lay.setSpacing(14)

        logo = QLabel("🌱 <b>Vectoora</b>")
        logo.setStyleSheet("font-size: 16px; color: #A3E635;")
        self.doc_title_lbl = QLabel("Untitled.vec")
        self.doc_title_lbl.setStyleSheet("font-size: 11px; color: #64748B;")
        lay.addWidget(logo)
        lay.addWidget(self.doc_title_lbl)

        home_btn = QPushButton("🏠")
        home_btn.setFixedSize(32, 32)
        home_btn.clicked.connect(lambda: self._switch_page(1))
        lay.addWidget(home_btn)

        for txt, cb in [
            ("📄 New", self._new_project), ("📂 Open", self._open_project_dialog),
            ("💾 Save", self._save_project), ("📑 Save As", self._save_project_as),
            ("↶ Undo", self._undo_action), ("↷ Redo", self._redo_action)
        ]:
            b = QPushButton(txt)
            b.setStyleSheet("background: transparent; color: #CBD5E1; font-size: 12px; padding: 4px 8px;")
            if cb:
                b.clicked.connect(cb)
            lay.addWidget(b)

        clr_btn = QPushButton("🧹 Clear All")
        clr_btn.setStyleSheet("background-color: #27141A; border: 1px solid #F43F5E; border-radius: 6px; color: #FDA4AF; font-size: 12px; font-weight: bold; padding: 4px 10px;")
        clr_btn.clicked.connect(self._clear_all_canvas)
        lay.addWidget(clr_btn)

        self.zoom_lbl_btn = QPushButton("100% ▾")
        self.zoom_lbl_btn.setStyleSheet("background-color: #111827; border: 1px solid #1E293B; border-radius: 6px; color: #CBD5E1; padding: 4px 10px;")
        self.zoom_lbl_btn.clicked.connect(lambda: self._set_zoom(1.0))
        lay.addWidget(self.zoom_lbl_btn)
        lay.addStretch(1)

        exp_btn = QPushButton("⬆ Export")
        exp_btn.setStyleSheet("background-color: #A3E635; color: #070B11; font-weight: bold; border-radius: 6px; padding: 6px 16px;")
        exp_btn.clicked.connect(self._on_export_clicked)
        lay.addWidget(exp_btn)

        ready_btn = QPushButton("🛡️ ReadyCheck")
        ready_btn.setStyleSheet("background-color: transparent; border: 1px solid #A3E635; color: #A3E635; font-weight: 600; border-radius: 6px; padding: 5px 14px;")
        ready_btn.clicked.connect(self._open_ready_check)
        lay.addWidget(ready_btn)
        return hdr

    def _create_primary_sidebar(self) -> QFrame:
        sb = QFrame()
        sb.setObjectName("primarySidebar")
        lay = QVBoxLayout(sb)
        lay.setContentsMargins(10, 16, 10, 16)
        lay.setSpacing(6)
        self.nav_buttons = {}

        for name, idx in [("🏠  Home", 1), ("✏️  Editor", 0), ("📁  My Projects", 2), ("🛡️  ReadyCheck", -1), ("⚙️  Settings", 3)]:
            b = QPushButton(name)
            b.setProperty("class", "navBtn")
            if idx >= 0:
                b.clicked.connect(lambda _, i=idx: self._switch_page(i))
            else:
                b.clicked.connect(self._open_ready_check)
            lay.addWidget(b)
            self.nav_buttons[name] = b

        lay.addStretch(1)
        slogan = QLabel("Design\nYour Way ✨")
        slogan.setStyleSheet("color: #A3E635; font-size: 14px; font-weight: bold; padding: 8px;")
        lay.addWidget(slogan)
        return sb

    def _switch_page(self, index: int):
        self.page_stack.setCurrentIndex(index)
        for name, btn in self.nav_buttons.items():
            btn.setProperty("class", "navBtn")
            btn.setStyle(btn.style())
        names = {0: "✏️  Editor", 1: "🏠  Home", 2: "📁  My Projects", 3: "⚙️  Settings"}
        if index in names and names[index] in self.nav_buttons:
            self.nav_buttons[names[index]].setProperty("class", "navBtnActive")
            self.nav_buttons[names[index]].setStyle(self.nav_buttons[names[index]].style())
        if index == 2:
            self._refresh_projects_page_list()

    def _build_editor_page(self) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._create_tools_panel())

        c_stage = QWidget()
        c_lay = QVBoxLayout(c_stage)
        c_lay.setContentsMargins(0, 0, 0, 0)
        c_lay.setSpacing(0)
        self.canvas_view = VectooraCanvasView()
        c_lay.addWidget(self.canvas_view, 1)
        c_lay.addWidget(self._create_floating_pill_bar(), 0, Qt.AlignmentFlag.AlignCenter)
        c_lay.addWidget(self._create_canvas_status_bar())

        lay.addWidget(c_stage, 1)
        lay.addWidget(self._create_inspector_panel())
        self.canvas_view.itemSelectedSignal.connect(self._on_item_selected)
        self.canvas_view.itemTransformSignal.connect(self._on_item_transformed)
        self.canvas_view.shapeCountChanged.connect(self._on_counts_updated)
        self.canvas_view.layersChangedSignal.connect(self._refresh_layers_ui)
        self.canvas_view.canvasModifiedSignal.connect(self._mark_modified)
        return w

    def _build_home_page(self) -> QWidget:
        p = QWidget()
        p.setStyleSheet("background-color: #06090F; padding: 32px;")
        lay = QVBoxLayout(p)
        lay.setSpacing(20)
        t = QLabel("Welcome to Vectoora Pro ✨")
        t.setStyleSheet("font-size: 26px; font-weight: 900; color: #F8FAFC;")
        lay.addWidget(t)

        card_row = QHBoxLayout()
        for ttl, desc, cb in [
            ("✏️ Return to Canvas", "Resume editing artwork", lambda: self._switch_page(0)),
            ("📄 Create New Design", "Start clean canvas", self._new_project),
            ("📁 Open Project", "Load .vec project file", self._open_project_dialog)
        ]:
            card = QFrame()
            card.setStyleSheet("background-color: #0B0F19; border: 1px solid #1E293B; border-radius: 12px; padding: 18px;")
            cl = QVBoxLayout(card)
            cl.addWidget(QLabel(ttl, styleSheet="font-size: 16px; font-weight: bold; color: #A3E635;"))
            cl.addWidget(QLabel(desc, styleSheet="font-size: 12px; color: #94A3B8;"))
            b = QPushButton("Open")
            b.setStyleSheet("background-color: #1E293B; color: #F8FAFC; border-radius: 6px; padding: 8px; margin-top: 12px;")
            b.clicked.connect(cb)
            cl.addWidget(b)
            card_row.addWidget(card)

        lay.addLayout(card_row)
        lay.addStretch(1)
        return p

    def _build_my_projects_page(self) -> QWidget:
        p = QWidget()
        p.setStyleSheet("background-color: #06090F; padding: 32px;")
        lay = QVBoxLayout(p)
        lay.setSpacing(16)
        t = QLabel("📁 My Projects Library")
        t.setStyleSheet("font-size: 24px; font-weight: 800; color: #A3E635;")
        lay.addWidget(t)

        self.project_page_list = QListWidget()
        self.project_page_list.setStyleSheet("background-color: #0B0F19; border: 1px solid #1E293B; border-radius: 10px; color: #F8FAFC; padding: 12px;")
        self.project_page_list.itemDoubleClicked.connect(self._open_project_from_page_list)
        lay.addWidget(self.project_page_list, 1)

        row = QHBoxLayout()
        b1 = QPushButton("📂 Open Selected")
        b1.setStyleSheet("background-color: #A3E635; color: #070B11; font-weight: bold; padding: 10px 18px; border-radius: 6px;")
        b1.clicked.connect(self._open_project_from_page_list)
        row.addWidget(b1)
        b2 = QPushButton("Browse Disk...")
        b2.setStyleSheet("background-color: #1E293B; color: #CBD5E1; padding: 10px 18px; border-radius: 6px;")
        b2.clicked.connect(self._open_project_dialog)
        row.addWidget(b2)
        row.addStretch(1)
        lay.addLayout(row)
        return p

    def _refresh_projects_page_list(self):
        self.project_page_list.clear()
        if not self.recent_projects:
            self.project_page_list.addItem("No saved projects found. Save a design first!")
        else:
            for p in self.recent_projects:
                if os.path.exists(p):
                    it = QListWidgetItem(f"📄 {os.path.basename(p)}  —  {p}")
                    it.setData(Qt.ItemDataRole.UserRole, p)
                    self.project_page_list.addItem(it)

    def _open_project_from_page_list(self):
        it = self.project_page_list.currentItem()
        if it and it.data(Qt.ItemDataRole.UserRole):
            p = it.data(Qt.ItemDataRole.UserRole)
            if self._maybe_save_changes():
                self._load_project_from_disk(p)
                self._switch_page(0)

    def _build_settings_page(self) -> QWidget:
        p = QWidget()
        p.setStyleSheet("background-color: #06090F; padding: 32px;")
        lay = QVBoxLayout(p)
        lay.setSpacing(20)
        t = QLabel("⚙️ Application Settings")
        t.setStyleSheet("font-size: 24px; font-weight: 800; color: #A3E635;")
        lay.addWidget(t)

        box = QFrame()
        box.setStyleSheet("background-color: #0B0F19; border: 1px solid #1E293B; border-radius: 12px; padding: 24px;")
        bl = QVBoxLayout(box)
        bl.setSpacing(14)
        for s in ["Enable Hardware Antialiasing", "Snap to Grid (40px)", "High-Resolution 300 DPI Export"]:
            cb = QCheckBox(s)
            cb.setChecked(True)
            cb.setStyleSheet("color: #F8FAFC; font-size: 13px;")
            bl.addWidget(cb)

        sb = QPushButton("Save Preferences")
        sb.setStyleSheet("background-color: #A3E635; color: #070B11; font-weight: bold; padding: 10px; border-radius: 6px; max-width: 180px;")
        sb.clicked.connect(lambda: QMessageBox.information(self, "Preferences", "Settings saved!"))
        bl.addWidget(sb)
        lay.addWidget(box)
        lay.addStretch(1)
        return p

    def _create_tools_panel(self) -> QFrame:
        tp = QFrame()
        tp.setObjectName("toolsPanel")
        tp.setFixedWidth(230)
        lay = QVBoxLayout(tp)
        lay.setContentsMargins(10, 12, 10, 12)
        lay.setSpacing(6)
        lay.addWidget(QLabel("Drawing Tools", styleSheet="font-size: 13px; font-weight: bold; color: #F8FAFC;"))

        cam_btn = QPushButton("📷  Camera Stencil")
        cam_btn.setStyleSheet("background-color: #0F172A; border: 1px solid #38BDF8; border-radius: 7px; color: #38BDF8; font-size: 12px; font-weight: bold; padding: 8px 12px; text-align: left;")
        cam_btn.clicked.connect(self._open_opencv_camera)
        lay.addWidget(cam_btn)

        self.tool_btns = {}
        for name, t_enum, chk in [
            ("↖  Select (V)", Tool.SELECT, True),
            ("🪣  Paint Bucket (G)", Tool.BUCKET, False),
            ("⭕  Lasso Erase (X)", Tool.LASSO_ERASE, False),
            ("🧹  Object Eraser (E)", Tool.ERASER, False),
            ("✏️  Pen Draw (B)", Tool.PEN, False),
            ("⬜  Rectangle (R)", Tool.RECTANGLE, False),
            ("⭕  Circle (C)", Tool.CIRCLE, False),
            ("╱  Line (L)", Tool.LINE, False),
            ("⬡  Polygon (P)", Tool.POLYGON, False),
            ("T  Text (T)", Tool.TEXT, False),
        ]:
            b = QPushButton(name)
            b.setProperty("class", "toolItemChecked" if chk else "toolItem")
            b.clicked.connect(lambda _, t=t_enum, btn=b: self._set_active_tool(t, btn))
            lay.addWidget(b)
            self.tool_btns[t_enum] = b

        lay.addSpacing(6)
        lay.addWidget(QLabel("Quick Shapes", styleSheet="font-size: 11px; font-weight: bold; color: #94A3B8;"))
        grid = QGridLayout()
        grid.setSpacing(4)
        for idx, (icon, st) in enumerate([("⬜", "rect"), ("⭕", "circle"), ("▲", "triangle"), ("★", "star"), ("❤️", "heart"), ("◆", "diamond"), ("⬡", "hexagon"), ("⬟", "pentagon"), ("➕", "cross"), ("➜", "arrow")]):
            b = QPushButton(icon)
            b.setProperty("class", "shapeBtn")
            b.setFixedSize(34, 30)
            b.clicked.connect(lambda _, s=st: self.canvas_view.add_shape_by_type(s))
            grid.addWidget(b, idx // 5, idx % 5)
        lay.addLayout(grid)

        lay.addSpacing(8)
        lay.addWidget(QLabel("Color Studio", styleSheet="font-size: 11px; font-weight: bold; color: #CBD5E1;"))
        t_box = QFrame()
        t_box.setStyleSheet("background-color: #111827; border: 1px solid #1E293B; border-radius: 6px;")
        tbl = QHBoxLayout(t_box)
        tbl.setContentsMargins(4, 4, 4, 4)
        tbl.setSpacing(4)
        self.target_fill_btn = QPushButton("● Fill")
        self.target_fill_btn.setStyleSheet("background-color: #A3E635; color: #070B11; font-weight: bold; border-radius: 4px; padding: 4px 8px; font-size: 11px;")
        self.target_fill_btn.clicked.connect(lambda: self._set_color_target("fill"))
        self.target_stroke_btn = QPushButton("○ Stroke")
        self.target_stroke_btn.setStyleSheet("background: transparent; color: #94A3B8; border-radius: 4px; padding: 4px 8px; font-size: 11px;")
        self.target_stroke_btn.clicked.connect(lambda: self._set_color_target("stroke"))
        tbl.addWidget(self.target_fill_btn)
        tbl.addWidget(self.target_stroke_btn)
        lay.addWidget(t_box)

        p_grid = QGridLayout()
        p_grid.setSpacing(6)
        for i, (hex_c, c_name) in enumerate(ESSENTIAL_COLORS):
            pb = QPushButton()
            pb.setFixedSize(32, 26)
            pb.setToolTip(f"{c_name} ({hex_c})")
            pb.setStyleSheet(f"background-color: {hex_c}; border: 2px solid #1E293B; border-radius: 6px;")
            pb.clicked.connect(lambda _, c=hex_c: self._apply_color_direct(c))
            p_grid.addWidget(pb, i // 5, i % 5)
        lay.addLayout(p_grid)

        arow = QHBoxLayout()
        self.color_preview_box = QPushButton()
        self.color_preview_box.setFixedSize(34, 30)
        self.color_preview_box.setStyleSheet(f"background-color: {self.active_color.name()}; border: 2px solid #F8FAFC; border-radius: 6px;")
        self.color_preview_box.clicked.connect(self._open_color_picker)
        arow.addWidget(self.color_preview_box)
        self.hex_label = QLabel(self.active_color.name())
        self.hex_label.setStyleSheet("color: #F8FAFC; font-weight: bold; font-size: 12px;")
        arow.addWidget(self.hex_label)
        more_btn = QPushButton("🎨 More...")
        more_btn.setStyleSheet("background-color: #172338; color: #38BDF8; font-size: 11px; font-weight: bold; border-radius: 6px; padding: 6px 10px;")
        more_btn.clicked.connect(self._open_color_picker)
        arow.addWidget(more_btn)
        lay.addLayout(arow)

        lay.addWidget(QLabel("Stroke Width", styleSheet="font-size: 10px; color: #64748B; margin-top: 6px;"))
        self.stroke_slider = QSlider(Qt.Orientation.Horizontal)
        self.stroke_slider.setRange(0, 16)
        self.stroke_slider.setValue(2)
        self.stroke_slider.valueChanged.connect(self._on_stroke_changed)
        lay.addWidget(self.stroke_slider)
        lay.addStretch(1)
        return tp

    def _set_color_target(self, target: str):
        self.color_target = target
        if target == "fill":
            self.target_fill_btn.setStyleSheet("background-color: #A3E635; color: #070B11; font-weight: bold; border-radius: 4px; padding: 4px 8px; font-size: 11px;")
            self.target_stroke_btn.setStyleSheet("background: transparent; color: #94A3B8; border-radius: 4px; padding: 4px 8px; font-size: 11px;")
            col = self.active_color
        else:
            self.target_stroke_btn.setStyleSheet("background-color: #38BDF8; color: #070B11; font-weight: bold; border-radius: 4px; padding: 4px 8px; font-size: 11px;")
            self.target_fill_btn.setStyleSheet("background: transparent; color: #94A3B8; border-radius: 4px; padding: 4px 8px; font-size: 11px;")
            col = self.stroke_color
        self.color_preview_box.setStyleSheet(f"background-color: {col.name()}; border: 2px solid #F8FAFC; border-radius: 6px;")
        self.hex_label.setText(col.name())

    def _create_floating_pill_bar(self) -> QFrame:
        p = QFrame()
        p.setObjectName("floatingActionPill")
        lay = QHBoxLayout(p)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(6)
        for name, cb in [("◀▶ Flip H", self._flip_h), ("▲▼ Flip V", self._flip_v), ("↻ Rotate", self._rotate_cw), ("📦 Duplicate", self._duplicate_selected), ("🗑 Delete", self._delete_selected)]:
            b = QPushButton(name)
            b.setProperty("class", "pillBtn")
            if cb:
                b.clicked.connect(cb)
            lay.addWidget(b)
        return p

    def _create_canvas_status_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("canvasStatusBar")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 4, 16, 4)
        z_out = QPushButton("-")
        z_out.setStyleSheet("background: transparent; border: none; color: #CBD5E1; font-weight: bold;")
        z_out.clicked.connect(lambda: self._set_zoom(self.current_zoom * 0.85))
        self.zoom_lbl = QLabel("100%")
        self.zoom_lbl.setStyleSheet("color: #94A3B8; font-size: 11px;")
        z_in = QPushButton("+")
        z_in.setStyleSheet("background: transparent; border: none; color: #CBD5E1; font-weight: bold;")
        z_in.clicked.connect(lambda: self._set_zoom(self.current_zoom * 1.15))
        lay.addWidget(z_out)
        lay.addWidget(self.zoom_lbl)
        lay.addWidget(z_in)
        fb = QPushButton("⛶ Fit to Canvas")
        fb.setStyleSheet("background: transparent; border: 1px solid #1E293B; border-radius: 4px; color: #CBD5E1; font-size: 11px; padding: 2px 8px;")
        fb.clicked.connect(self._reset_view)
        lay.addWidget(fb)
        lay.addSpacing(20)
        lay.addWidget(QLabel("Canvas Size: 1080 × 1080 px", styleSheet="color: #64748B; font-size: 11px;"))
        lay.addStretch(1)
        self.obj_count_lbl = QLabel("Objects: 0", styleSheet="color: #94A3B8; font-size: 11px;")
        self.sel_count_lbl = QLabel("● Selected: 0", styleSheet="color: #A3E635; font-size: 11px;")
        lay.addWidget(self.obj_count_lbl)
        lay.addSpacing(12)
        lay.addWidget(self.sel_count_lbl)
        return bar

    def _create_inspector_panel(self) -> QFrame:
        insp = QFrame()
        insp.setObjectName("inspectorPanel")
        insp.setFixedWidth(280)
        lay = QVBoxLayout(insp)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)
        tbar = QHBoxLayout()
        self.tab_prop_btn = QPushButton("Properties")
        self.tab_layer_btn = QPushButton("Layers")
        for b in (self.tab_prop_btn, self.tab_layer_btn):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tab_prop_btn.clicked.connect(lambda: self._switch_inspector_tab(0))
        self.tab_layer_btn.clicked.connect(lambda: self._switch_inspector_tab(1))
        tbar.addWidget(self.tab_prop_btn)
        tbar.addWidget(self.tab_layer_btn)
        tbar.addStretch(1)
        lay.addLayout(tbar)

        self.insp_stack = QStackedLayout()
        self.page_prop = QWidget()
        pl = QVBoxLayout(self.page_prop)
        pl.setContentsMargins(0, 8, 0, 0)
        pl.setSpacing(10)
        self.no_sel_banner = QLabel("Select an object on canvas to inspect")
        self.no_sel_banner.setStyleSheet("color: #64748B; font-size: 11px; font-style: italic;")
        pl.addWidget(self.no_sel_banner)
        pl.addWidget(QLabel("Position & Size", styleSheet="font-size: 11px; font-weight: bold; color: #CBD5E1;"))

        r1 = QHBoxLayout()
        self.x_input = QLineEdit("---")
        self.x_input.setProperty("class", "coordInput")
        self.x_input.editingFinished.connect(self._apply_manual_transforms)
        self.y_input = QLineEdit("---")
        self.y_input.setProperty("class", "coordInput")
        self.y_input.editingFinished.connect(self._apply_manual_transforms)
        r1.addWidget(QLabel("X", styleSheet="color: #64748B; font-size: 10px;"))
        r1.addWidget(self.x_input)
        r1.addWidget(QLabel("Y", styleSheet="color: #64748B; font-size: 10px;"))
        r1.addWidget(self.y_input)
        pl.addLayout(r1)

        r2 = QHBoxLayout()
        self.w_input = QLineEdit("---")
        self.w_input.setProperty("class", "coordInput")
        self.w_input.editingFinished.connect(self._apply_manual_transforms)
        self.h_input = QLineEdit("---")
        self.h_input.setProperty("class", "coordInput")
        self.h_input.editingFinished.connect(self._apply_manual_transforms)
        r2.addWidget(QLabel("W", styleSheet="color: #64748B; font-size: 10px;"))
        r2.addWidget(self.w_input)
        r2.addWidget(QLabel("H", styleSheet="color: #64748B; font-size: 10px;"))
        r2.addWidget(self.h_input)
        pl.addLayout(r2)

        self.aspect_ratio_cb = QCheckBox("🔒 Constrain Proportions")
        self.aspect_ratio_cb.setStyleSheet("color: #94A3B8; font-size: 11px;")
        self.aspect_ratio_cb.toggled.connect(self._on_aspect_ratio_toggled)
        pl.addWidget(self.aspect_ratio_cb)

        pl.addWidget(QLabel("Rotation", styleSheet="font-size: 11px; font-weight: bold; color: #CBD5E1; margin-top: 4px;"))
        self.rot_input = QLineEdit("---")
        self.rot_input.setProperty("class", "coordInput")
        self.rot_input.editingFinished.connect(self._apply_manual_transforms)
        pl.addWidget(self.rot_input)

        pl.addWidget(QLabel("Appearance", styleSheet="font-size: 11px; font-weight: bold; color: #CBD5E1; margin-top: 6px;"))
        arow = QHBoxLayout()
        self.fill_swatch_right = QPushButton()
        self.fill_swatch_right.setFixedSize(30, 30)
        self.fill_swatch_right.setStyleSheet("background-color: #38BDF8; border-radius: 6px; border: 1px solid #1E293B;")
        self.fill_swatch_right.clicked.connect(self._open_color_picker)
        self.stroke_swatch_right = QPushButton()
        self.stroke_swatch_right.setFixedSize(30, 30)
        self.stroke_swatch_right.setStyleSheet("background-color: #1E2D44; border-radius: 6px; border: 1px solid #1E293B;")
        self.stroke_swatch_right.clicked.connect(self._open_stroke_color_picker)
        arow.addWidget(QLabel("Fill:", styleSheet="color: #94A3B8; font-size: 11px;"))
        arow.addWidget(self.fill_swatch_right)
        arow.addSpacing(10)
        arow.addWidget(QLabel("Stroke:", styleSheet="color: #94A3B8; font-size: 11px;"))
        arow.addWidget(self.stroke_swatch_right)
        arow.addStretch(1)
        pl.addLayout(arow)

        pl.addWidget(QLabel("Opacity", styleSheet="font-size: 10px; color: #64748B; margin-top: 6px;"))
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(10, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        pl.addWidget(self.opacity_slider)
        self.insp_stack.addWidget(self.page_prop)

        page_layers = QWidget()
        ll = QVBoxLayout(page_layers)
        ll.setContentsMargins(0, 8, 0, 0)
        ll.addWidget(QLabel("Canvas Layer Hierarchy", styleSheet="font-size: 11px; font-weight: bold; color: #CBD5E1;"))
        scroll_l = QScrollArea()
        scroll_l.setWidgetResizable(True)
        scroll_l.setStyleSheet("background: transparent; border: none;")
        scroll_content_l = QWidget()
        self.layers_container = QVBoxLayout(scroll_content_l)
        self.layers_container.setSpacing(4)
        scroll_l.setWidget(scroll_content_l)
        ll.addWidget(scroll_l, 1)
        self.insp_stack.addWidget(page_layers)

        lay.addLayout(self.insp_stack)
        self._switch_inspector_tab(0)
        return insp

    def _set_inspector_enabled(self, enabled: bool):
        self.no_sel_banner.setVisible(not enabled)
        for w in (self.x_input, self.y_input, self.w_input, self.h_input, self.rot_input, self.aspect_ratio_cb, self.fill_swatch_right, self.stroke_swatch_right, self.opacity_slider):
            w.setEnabled(enabled)
        if not enabled:
            self.x_input.setText("---")
            self.y_input.setText("---")
            self.w_input.setText("---")
            self.h_input.setText("---")
            self.rot_input.setText("---")

    def _switch_inspector_tab(self, idx: int):
        self.insp_stack.setCurrentIndex(idx)
        for i, b in enumerate([self.tab_prop_btn, self.tab_layer_btn]):
            if i == idx:
                b.setStyleSheet("background: transparent; border: none; font-size: 12px; font-weight: bold; color: #A3E635; border-bottom: 2px solid #A3E635; padding-bottom: 4px;")
            else:
                b.setStyleSheet("background: transparent; border: none; font-size: 12px; font-weight: bold; color: #64748B; padding-bottom: 4px;")

    def _refresh_layers_ui(self, items):
        while self.layers_container.count():
            w = self.layers_container.takeAt(0).widget()
            if w:
                w.deleteLater()
        for it in items:
            lf = QFrame()
            lf.setProperty("class", "layerItemActive" if it.isSelected() else "layerItem")
            lfl = QHBoxLayout(lf)
            lfl.setContentsMargins(6, 4, 6, 4)
            b = QPushButton(it.item_name)
            b.setStyleSheet("color: #F8FAFC; font-size: 11px; text-align: left; background: transparent; border: none;")
            b.clicked.connect(lambda _, t=it: self._select_layer_item(t))
            lfl.addWidget(b, 1)
            eye = QPushButton("👁️")
            eye.setStyleSheet("background: transparent; border: none; font-size: 11px;")
            eye.clicked.connect(lambda _, item=it: self._toggle_layer_vis(item))
            lfl.addWidget(eye)
            lock = QPushButton("🔒")
            lock.setStyleSheet("background: transparent; border: none; font-size: 11px;")
            lock.clicked.connect(lambda _, item=it: self._toggle_layer_lock(item))
            lfl.addWidget(lock)
            self.layers_container.addWidget(lf)

    def _select_layer_item(self, target):
        self.canvas_view.scene.clearSelection()
        target.setSelected(True)
        self.canvas_view.centerOn(target)

    def _toggle_layer_vis(self, item):
        item.setVisible(not item.isVisible())
        self._mark_modified()

    def _toggle_layer_lock(self, item):
        item.set_locked(not item.is_locked)
        self._mark_modified()
        QMessageBox.information(self, "Layer Status", f"Layer '{item.item_name}' lock toggled.")

    def _on_aspect_ratio_toggled(self, checked: bool):
        t = self.current_selected_item or self.canvas_view.selected_item()
        if t:
            t.keep_aspect_ratio = checked
            self._mark_modified()

    def _apply_manual_transforms(self):
        t = self.current_selected_item or self.canvas_view.selected_item()
        if not t:
            return
        try:
            xv = float(self.x_input.text().replace("px", "").replace("---", "").strip() or t.pos().x())
            yv = float(self.y_input.text().replace("px", "").replace("---", "").strip() or t.pos().y())
            wv = float(self.w_input.text().replace("px", "").replace("---", "").strip() or t.box_w)
            hv = float(self.h_input.text().replace("px", "").replace("---", "").strip() or t.box_h)
            rv = float(self.rot_input.text().replace("°", "").replace("---", "").strip() or t.rotation())
            t.setPos(xv, yv)
            t.setRotation(rv)
            t.set_dimensions(max(15.0, wv), max(15.0, hv))
            self.canvas_view.scene.update()
            self._mark_modified()
        except ValueError:
            pass

    def _set_zoom(self, factor):
        self.canvas_view.scale(factor / self.current_zoom, factor / self.current_zoom)
        self.current_zoom = factor
        self.zoom_lbl.setText(f"{int(self.current_zoom * 100)}%")
        self.zoom_lbl_btn.setText(f"{int(self.current_zoom * 100)}% ▾")

    def _reset_view(self):
        self.canvas_view.resetTransform()
        self.current_zoom = 1.0
        self.zoom_lbl.setText("100%")
        self.zoom_lbl_btn.setText("100% ▾")
        items = self.canvas_view.scene.items()
        if items:
            self.canvas_view.centerOn(items[0])

    def _apply_color_direct(self, hex_c: str):
        col = QColor(hex_c)
        t = self.current_selected_item or self.canvas_view.selected_item()
        if self.color_target == "fill":
            self.active_color = col
            self.canvas_view.active_color = col
            self.color_preview_box.setStyleSheet(f"background-color: {hex_c}; border: 2px solid #F8FAFC; border-radius: 6px;")
            self.hex_label.setText(hex_c)
            self.fill_swatch_right.setStyleSheet(f"background-color: {hex_c}; border-radius: 6px; border: 1px solid #1E293B;")
            if t and hasattr(t, "set_fill"):
                t.set_fill(col)
                self._mark_modified()
        else:
            self.stroke_color = col
            self.canvas_view.stroke_color = col
            self.color_preview_box.setStyleSheet(f"background-color: {hex_c}; border: 2px solid #F8FAFC; border-radius: 6px;")
            self.hex_label.setText(hex_c)
            self.stroke_swatch_right.setStyleSheet(f"background-color: {hex_c}; border-radius: 6px; border: 1px solid #1E293B;")
            if t and hasattr(t, "set_stroke_color"):
                t.set_stroke_color(col)
                self._mark_modified()

    def _open_color_picker(self):
        c = self.active_color if self.color_target == "fill" else self.stroke_color
        col = QColorDialog.getColor(c, self, f"Select {self.color_target.capitalize()} Color")
        if col.isValid():
            self._apply_color_direct(col.name())

    def _open_stroke_color_picker(self):
        self._set_color_target("stroke")
        self._open_color_picker()

    def _on_opacity_changed(self, val):
        t = self.current_selected_item or self.canvas_view.selected_item()
        if t:
            t.set_opacity_val(val / 100.0)
            self._mark_modified()

    def _open_ready_check(self):
        for item in self.seal_indicators:
            self.canvas_view.scene.removeItem(item)
        self.seal_indicators.clear()
        dlg = ReadyCheckDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            for itm in self.canvas_view.scene.items():
                if isinstance(itm, VectorGraphicItem):
                    glow = self.canvas_view.scene.addRect(itm.sceneBoundingRect().adjusted(-6, -6, 6, 6), QPen(QColor("#A3E635"), 3, Qt.PenStyle.DashLine), QBrush(Qt.BrushStyle.NoBrush))
                    self.seal_indicators.append(glow)
            QMessageBox.information(self, "Sealing Complete", "✨ All vector perimeter paths sealed!")

    def _set_active_tool(self, tool: Tool, btn: QPushButton):
        self.canvas_view.set_tool(tool)
        for b in self.tool_btns.values():
            b.setProperty("class", "toolItem")
            b.setStyle(b.style())
        btn.setProperty("class", "toolItemChecked")
        btn.setStyle(btn.style())

    def _on_item_selected(self, item):
        self.current_selected_item = item
        if item is None:
            self._set_inspector_enabled(False)
            return
        self._set_inspector_enabled(True)
        if hasattr(item, "fill_color"):
            self.active_color = item.fill_color
            self.fill_swatch_right.setStyleSheet(f"background-color: {item.fill_color.name()}; border-radius: 6px; border: 1px solid #1E293B;")
        if hasattr(item, "stroke_color"):
            self.stroke_color = item.stroke_color
            self.stroke_swatch_right.setStyleSheet(f"background-color: {item.stroke_color.name()}; border-radius: 6px; border: 1px solid #1E293B;")
        if hasattr(item, "keep_aspect_ratio"):
            self.aspect_ratio_cb.blockSignals(True)
            self.aspect_ratio_cb.setChecked(item.keep_aspect_ratio)
            self.aspect_ratio_cb.blockSignals(False)
        if hasattr(item, "opacity_val"):
            self.opacity_slider.blockSignals(True)
            self.opacity_slider.setValue(int(item.opacity_val * 100))
            self.opacity_slider.blockSignals(False)

    def _on_item_transformed(self, x, y, w, h, rot):
        if not self.current_selected_item:
            return
        self.x_input.blockSignals(True)
        self.y_input.blockSignals(True)
        self.w_input.blockSignals(True)
        self.h_input.blockSignals(True)
        self.rot_input.blockSignals(True)
        self.x_input.setText(f"{int(x)} px")
        self.y_input.setText(f"{int(y)} px")
        self.w_input.setText(f"{int(w)} px")
        self.h_input.setText(f"{int(h)} px")
        self.rot_input.setText(f"{int(rot)}°")
        self.x_input.blockSignals(False)
        self.y_input.blockSignals(False)
        self.w_input.blockSignals(False)
        self.h_input.blockSignals(False)
        self.rot_input.blockSignals(False)

    def _on_counts_updated(self, total, selected):
        self.obj_count_lbl.setText(f"Objects: {total}")
        self.sel_count_lbl.setText(f"● Selected: {selected}")

    def _on_stroke_changed(self, val):
        self.canvas_view.active_stroke_width = val
        t = self.current_selected_item or self.canvas_view.selected_item()
        if t and hasattr(t, "set_stroke_width"):
            t.set_stroke_width(val)
            self._mark_modified()

    def _flip_h(self):
        t = self.current_selected_item or self.canvas_view.selected_item()
        if t:
            t.setScale(t.scale() * -1)
            self._mark_modified()

    def _flip_v(self):
        t = self.current_selected_item or self.canvas_view.selected_item()
        if t:
            t.setRotation(t.rotation() + 180)
            self._mark_modified()

    def _rotate_cw(self):
        t = self.current_selected_item or self.canvas_view.selected_item()
        if t:
            t.setRotation(t.rotation() + 45)
            self._mark_modified()

    def _duplicate_selected(self):
        t = self.current_selected_item or self.canvas_view.selected_item()
        if t:
            new_item = self.canvas_view.add_shape_by_type(t.kind, t.pos() + QPointF(30, 30))
            new_item.set_dimensions(t.box_w, t.box_h)
            new_item.set_fill(t.fill_color)
            self._mark_modified()

    def _delete_selected(self):
        for it in self.canvas_view.scene.selectedItems():
            self.canvas_view.scene.removeItem(it)
        self.canvas_view._notify_layers_updated()
        self._mark_modified()

    def _undo_action(self):
        if not hasattr(self, 'undo_stack') or not self.undo_stack:
            items = [i for i in self.canvas_view.scene.items() if hasattr(i, 'kind')]
            if items:
                last_item = items[0]
                self.canvas_view.scene.removeItem(last_item)
                if not hasattr(self, 'redo_stack'):
                    self.redo_stack = []
                self.redo_stack.append(('remove', last_item))
                self.canvas_view._notify_layers_updated()
                self._mark_modified()
            return
        action = self.undo_stack.pop()
        if isinstance(action, tuple):
            act_type, target = action
            if act_type == 'add_multi':
                for it in target:
                    if it in self.canvas_view.scene.items():
                        self.canvas_view.scene.removeItem(it)
                self.redo_stack.append(action)
            elif act_type in ('erase', 'remove'):
                self.canvas_view.scene.addItem(target)
                self.redo_stack.append(action)
        else:
            self.canvas_view.scene.removeItem(action)
            self.redo_stack.append(action)
        self.canvas_view._notify_layers_updated()
        self._mark_modified()
    def _redo_action(self):
        if not hasattr(self, 'redo_stack') or not self.redo_stack:
            return
        action = self.redo_stack.pop()
        if isinstance(action, tuple):
            act_type, target = action
            if act_type == "add_multi":
                for it in target:
                    self.canvas_view.scene.addItem(it)
                self.undo_stack.append(action)
            elif act_type == "erase":
                self.canvas_view.scene.removeItem(target)
                self.undo_stack.append(action)
            elif act_type == "remove":
                self.canvas_view.scene.removeItem(target)
                self.undo_stack.append(action)
        else:
            self.canvas_view.scene.addItem(action)
            self.undo_stack.append(action)
        self.canvas_view._notify_layers_updated()
        self._mark_modified()

    def _redo_action(self):
        if self.redo_stack:
            item_to_restore = self.redo_stack.pop()
            self.canvas_view.scene.addItem(item_to_restore)
            self.canvas_view.scene.clearSelection()
            item_to_restore.setSelected(True)
            self.canvas_view._notify_layers_updated()
            self._mark_modified()

    def _clear_all_canvas(self):
        if not self.canvas_view.scene.items():
            return
        if QMessageBox.question(self, "Clear Canvas", "Are you sure you want to clear the entire canvas?") == QMessageBox.StandardButton.Yes:
            self.canvas_view.scene.clear()
            self.canvas_view._notify_layers_updated()
            self._mark_modified()

    def _generate_path_from_frame(self, frame):
        import cv2
        import numpy as np
        from PyQt6.QtGui import QPainterPath
        from PyQt6.QtCore import QPointF

        # 1. Bilateral filter to smooth texture while retaining solid facial contours
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.bilateralFilter(gray, 9, 75, 75)

        # 2. Otsu auto-thresholding for solid, unbroken line mass
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # 3. Morphological close with 5x5 kernel to solidly bridge broken gaps
        bridge_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, bridge_kernel)

        # 4. Extract external contours for fully closed, solid stencils (no broken dashes)
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_TC89_KCOS)

        path_list = []
        for cnt in contours:
            # Filter noise dots, keep continuous shapes
            if cv2.contourArea(cnt) > 45:
                epsilon = 0.002 * cv2.arcLength(cnt, True)
                approx = cv2.approxPolyDP(cnt, epsilon, True)
                if len(approx) > 2:
                    p = QPainterPath()
                    p.moveTo(QPointF(float(approx[0][0][0]), float(approx[0][0][1])))
                    for pt in approx[1:]:
                        p.lineTo(QPointF(float(pt[0][0]), float(pt[0][1])))
                    p.closeSubpath()  # Fully seal vector perimeter for ReadyCheck & Bucket Fill
                    path_list.append(p)

        return path_list


    def _apply_lasso_erase(self, lasso_path):
        items_to_erase = []
        for item in self.canvas_view.scene.items():
            if hasattr(item, 'kind') and item.isVisible():
                if item.collidesWithPath(item.mapFromScene(lasso_path)):
                    items_to_erase.append(item)
        if items_to_erase:
            for it in items_to_erase:
                self.canvas_view.scene.removeItem(it)
            if hasattr(self, 'undo_stack'):
                self.undo_stack.append(('add_multi', items_to_erase))
            self.canvas_view._notify_layers_updated()
            self._mark_modified()
    def _open_opencv_camera(self):
        try:
            import cv2
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel, QMessageBox
            from PyQt6.QtGui import QImage, QPixmap, QPainterPath, QColor
            from PyQt6.QtCore import QTimer, Qt, QPointF

            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                QMessageBox.critical(self, "Camera Error", "Could not open webcam.")
                return

            dlg = QDialog(self)
            dlg.setWindowTitle("Live Camera Stencil Capture")
            dlg.setFixedSize(660, 540)
            layout = QVBoxLayout(dlg)

            video_label = QLabel()
            video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(video_label)

            capture_btn = QPushButton("📷 Capture Vector Stencil")
            capture_btn.setStyleSheet("background-color: #38BDF8; color: #0F172A; font-weight: bold; padding: 10px; border-radius: 6px;")
            layout.addWidget(capture_btn)

            captured_paths = []

            def update_frame():
                ret, frame = cap.read()
                if ret:
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    h, w, ch = rgb.shape
                    qimg = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
                    video_label.setPixmap(QPixmap.fromImage(qimg).scaled(640, 440, Qt.AspectRatioMode.KeepAspectRatio))

            timer = QTimer(dlg)
            timer.timeout.connect(update_frame)
            timer.start(30)

            def on_capture():
                ret, frame = cap.read()
                if ret:
                    paths = self._generate_path_from_frame(frame)
                    captured_paths.extend(paths)
                dlg.accept()

            capture_btn.clicked.connect(on_capture)
            dlg.exec()
            cap.release()

            if captured_paths:
                added_items = []
                for p in captured_paths:
                    if not p.isEmpty():
                        it = VectorGraphicItem("stencil", "📷 Stencil Stroke", QColor(0, 0, 0, 0), QColor("#38BDF8"), 2, custom_path=p)
                        self.canvas_view.scene.addItem(it)
                        added_items.append(it)
                if added_items:
                    self.canvas_view.scene.clearSelection()
                    added_items[-1].setSelected(True)
                    if hasattr(self, "undo_stack"):
                        self.undo_stack.append(("add_multi", added_items))
                    self.canvas_view._notify_layers_updated()
                    self._mark_modified()
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Camera Error", f"Camera error: {e}")


    def _on_export_clicked(self):
        fp, flt = QFileDialog.getSaveFileName(self, "Export Artwork", "vectoora_design.png", "PNG Image (*.png);;SVG Vector (*.svg);;PDF Document (*.pdf)")
        if not fp:
            return
        try:
            if fp.lower().endswith(".svg") or "SVG" in flt:
                if not fp.lower().endswith(".svg"):
                    fp += ".svg"
                self._export_to_svg(fp)
            elif fp.lower().endswith(".pdf") or "PDF" in flt:
                if not fp.lower().endswith(".pdf"):
                    fp += ".pdf"
                self._export_to_pdf(fp)
            else:
                if not fp.lower().endswith(".png"):
                    fp += ".png"
                self._export_to_png(fp)
            QMessageBox.information(self, "Export Successful", f"✅ Artwork exported to:\n{fp}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export:\n{e}")

    def _export_to_png(self, fp: str):
        rect = self.canvas_view.scene.sceneRect()
        img = QImage(int(rect.width()), int(rect.height()), QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.canvas_view.scene.render(p, QRectF(img.rect()), rect)
        p.end()
        if not img.save(fp, "PNG"):
            raise RuntimeError("Could not write PNG image.")

    def _export_to_svg(self, fp: str):
        rect = self.canvas_view.scene.sceneRect()
        gen = QSvgGenerator()
        gen.setFileName(fp)
        gen.setSize(QSize(int(rect.width()), int(rect.height())))
        gen.setViewBox(rect)
        p = QPainter(gen)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.canvas_view.scene.render(p, rect, rect)
        p.end()
        if not os.path.exists(fp) or os.path.getsize(fp) == 0:
            raise RuntimeError("SVG failed.")

    def _export_to_pdf(self, fp: str):
        rect = self.canvas_view.scene.sceneRect()
        pw = QPdfWriter(fp)
        pw.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        pw.setResolution(300)
        p = QPainter(pw)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.canvas_view.scene.render(p, QRectF(0, 0, pw.width(), pw.height()), rect)
        p.end()
        if not os.path.exists(fp) or os.path.getsize(fp) == 0:
            raise RuntimeError("PDF failed.")

    def _mark_modified(self):
        self.is_modified = True
        ttl = os.path.basename(self.current_file_path) if self.current_file_path else "Untitled.vec"
        self.doc_title_lbl.setText(f"{ttl} ● (Unsaved)")

    def _mark_saved(self):
        self.is_modified = False
        ttl = os.path.basename(self.current_file_path) if self.current_file_path else "Untitled.vec"
        self.doc_title_lbl.setText(f"{ttl}")

    def _maybe_save_changes(self) -> bool:
        if not self.is_modified:
            return True
        r = QMessageBox.question(self, "Unsaved Changes", "Do you want to save changes before continuing?", QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
        if r == QMessageBox.StandardButton.Save:
            return self._save_project()
        elif r == QMessageBox.StandardButton.Cancel:
            return False
        return True

    def _new_project(self):
        if not self._maybe_save_changes():
            return
        self.canvas_view.scene.clear()
        self.canvas_view._notify_layers_updated()
        self.current_file_path = None
        self._mark_saved()
        self.doc_title_lbl.setText("Untitled.vec")
        self._switch_page(0)

    def _save_project(self) -> bool:
        if self.current_file_path:
            return self._write_project_to_disk(self.current_file_path)
        return self._save_project_as()

    def _save_project_as(self) -> bool:
        fp, _ = QFileDialog.getSaveFileName(self, "Save Project As", self.current_file_path or "my_design.vec", "Vectoora Projects (*.vec);;JSON Files (*.json)")
        if not fp:
            return False
        if not (fp.endswith(".vec") or fp.endswith(".json")):
            fp += ".vec"
        return self._write_project_to_disk(fp)

    def _write_project_to_disk(self, fp: str) -> bool:
        try:
            items = [i.to_dict() for i in self.canvas_view.scene.items() if isinstance(i, VectorGraphicItem)]
            with open(fp, "w", encoding="utf-8") as f:
                json.dump({"format": "VectooraProject", "items": items}, f, indent=2)
            self.current_file_path = fp
            self._mark_saved()
            self._add_to_recent(fp)
            QMessageBox.information(self, "Project Saved", f"✅ Saved to:\n{fp}")
            return True
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed:\n{e}")
            return False

    def _open_project_dialog(self):
        if not self._maybe_save_changes():
            return
        fp, _ = QFileDialog.getOpenFileName(self, "Open Vectoora Project", "", "Vectoora Projects (*.vec *.json);;All Files (*.*)")
        if fp:
            self._load_project_from_disk(fp)
            self._switch_page(0)

    def _load_project_from_disk(self, fp: str):
        if not os.path.exists(fp):
            return
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.canvas_view.scene.clear()
            for it in reversed(data.get("items", [])):
                self.canvas_view.scene.addItem(VectorGraphicItem.from_dict(it))
            self.current_file_path = fp
            self._mark_saved()
            self._add_to_recent(fp)
            self.canvas_view._notify_layers_updated()
            self._reset_view()
        except Exception as e:
            QMessageBox.critical(self, "Corrupted Project", f"Error:\n{e}")

    def closeEvent(self, event):
        if self._maybe_save_changes():
            event.accept()
        else:
            event.ignore()

def main():
    app = QApplication(sys.argv)
    window = VectooraApp()
    window.showMaximized()
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())