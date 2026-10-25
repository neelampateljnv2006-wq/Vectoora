from __future__ import annotations
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
        self._init_ui()

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