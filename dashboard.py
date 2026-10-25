"""
dashboard.py - Screen 1: Home / Dashboard matching exact UI specifications
Features:
- Left persistent navigation drawer
- Hero Banner ("Welcome back, Creator! Turn your ideas into stunning designs.")
- Module launch cards (WearLab, ShapeLab, MarkIt, HueBox, CutCraft)
- Recent projects grid
- Quick actions panel (New Project, Open Project, Import Image, View Tutorials)
"""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QScrollArea, QGridLayout
)

DASHBOARD_STYLESHEET = """
QWidget#dashboardRoot {
    background-color: #0B0F19;
    color: #F8FAFC;
    font-family: 'Segoe UI', sans-serif;
}
QFrame#heroCard {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #111827, stop:1 #1E293B);
    border: 1px solid #1E293B;
    border-radius: 16px;
    padding: 18px;
}
QFrame#studioCard {
    background-color: #111827;
    border: 1px solid #1F2937;
    border-radius: 14px;
}
QFrame#studioCard:hover {
    border: 1px solid #A3E635;
    background-color: #151E2E;
}
QFrame#projectCard {
    background-color: #111827;
    border: 1px solid #1F2937;
    border-radius: 12px;
}
QFrame#projectCard:hover {
    border: 1px solid #A3E635;
}
QPushButton#actionBtn {
    background-color: #111827;
    border: 1px solid #1F2937;
    border-radius: 10px;
    color: #E2E8F0;
    text-align: left;
    padding: 10px 14px;
    font-size: 13px;
    font-weight: 500;
}
QPushButton#actionBtn:hover {
    background-color: #1E293B;
    border-color: #A3E635;
    color: #A3E635;
}
QPushButton#navItem {
    background-color: transparent;
    border: none;
    border-radius: 8px;
    color: #94A3B8;
    text-align: left;
    padding: 10px 14px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton#navItem:hover {
    background-color: #1E293B;
    color: #F8FAFC;
}
QPushButton#navItemActive {
    background-color: #A3E635;
    border: none;
    border-radius: 8px;
    color: #020617;
    text-align: left;
    padding: 10px 14px;
    font-size: 13px;
    font-weight: bold;
}
"""

class StudioModuleCard(QFrame):
    clicked = pyqtSignal(str)

    def __init__(self, key: str, icon_symbol: str, title: str, subtitle: str, color_accent: str = "#A3E635"):
        super().__init__()
        self.key = key
        self.setObjectName("studioCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(140, 110)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(6)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_lbl = QLabel(icon_symbol)
        icon_lbl.setStyleSheet(f"font-size: 26px; color: {color_accent};")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #F8FAFC;")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sub_lbl = QLabel(subtitle)
        sub_lbl.setStyleSheet("font-size: 10px; color: #94A3B8;")
        sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lay.addWidget(icon_lbl)
        lay.addWidget(title_lbl)
        lay.addWidget(sub_lbl)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.key)
        super().mousePressEvent(event)


class RecentProjectItem(QFrame):
    def __init__(self, title: str, timestamp: str, icon_art: str):
        super().__init__()
        self.setObjectName("projectCard")
        self.setFixedSize(130, 120)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(4)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        preview = QLabel(icon_art)
        preview.setStyleSheet("font-size: 32px;")
        preview.setAlignment(Qt.AlignmentFlag.AlignCenter)

        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #F8FAFC;")
        t_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        d_lbl = QLabel(timestamp)
        d_lbl.setStyleSheet("font-size: 9px; color: #64748B;")
        d_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lay.addWidget(preview)
        lay.addWidget(t_lbl)
        lay.addWidget(d_lbl)


class DashboardView(QWidget):
    openWorkspace = pyqtSignal(str)
    importImageRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dashboardRoot")
        self.setStyleSheet(DASHBOARD_STYLESHEET)
        self._build_ui()

    def _build_ui(self):
        root_lay = QHBoxLayout(self)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)

        # ----------------- 1. LEFT SIDEBAR NAVIGATION -----------------
        sidebar = QFrame()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet("background-color: #080C14; border-right: 1px solid #1E293B;")
        side_lay = QVBoxLayout(sidebar)
        side_lay.setContentsMargins(14, 18, 14, 18)
        side_lay.setSpacing(6)

        # Brand Header
        brand_lbl = QLabel("🌱 Stencil Studio")
        brand_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #A3E635; margin-bottom: 12px;")
        side_lay.addWidget(brand_lbl)

        # Navigation Links
        nav_home = QPushButton("🏠  Home")
        nav_home.setObjectName("navItemActive")
        side_lay.addWidget(nav_home)

        nav_items = [
            ("👕  WearLab", "wearlab"),
            ("✏️  ShapeLab", "shapelab"),
            ("🏷️  MarkIt", "markit"),
            ("🎨  HueBox", "huebox"),
            ("✂️  CutCraft", "cutcraft"),
            ("🔍  EdgeCheck", "edgecheck"),
            ("🌈  ColorMix", "colormix"),
            ("👁️  Showcase", "showcase"),
            ("📁  My Space", "myspace"),
            ("📤  ShareOut", "shareout"),
            ("⚙️  Settings", "settings")
        ]

        for text, key in nav_items:
            b = QPushButton(text)
            b.setObjectName("navItem")
            b.clicked.connect(lambda _, k=key: self.openWorkspace.emit(k))
            side_lay.addWidget(b)

        side_lay.addStretch(1)
        root_lay.addWidget(sidebar)

        # ----------------- 2. MAIN DASHBOARD CONTENT AREA -----------------
        main_content = QWidget()
        main_lay = QVBoxLayout(main_content)
        main_lay.setContentsMargins(32, 24, 32, 24)
        main_lay.setSpacing(22)

        # Top Bar
        top_bar = QHBoxLayout()
        search_box = QLabel("🔍  Search projects, templates...")
        search_box.setStyleSheet("background-color: #111827; border: 1px solid #1F2937; border-radius: 8px; padding: 8px 16px; color: #64748B; font-size: 12px;")
        top_bar.addWidget(search_box, 1)

        user_badge = QLabel("👤 Creator")
        user_badge.setStyleSheet("color: #E2E8F0; font-size: 12px; font-weight: bold; padding-left: 14px;")
        top_bar.addWidget(user_badge)
        main_lay.addLayout(top_bar)

        # Hero Welcome Banner
        hero = QFrame()
        hero.setObjectName("heroCard")
        hero_lay = QHBoxLayout(hero)
        
        hero_left = QVBoxLayout()
        h_title = QLabel("Welcome back, Creator!")
        h_title.setStyleSheet("font-size: 22px; font-weight: 800; color: #FFFFFF;")
        h_sub = QLabel("Turn your ideas into stunning designs.")
        h_sub.setStyleSheet("font-size: 13px; color: #94A3B8; margin-top: 2px;")
        hero_left.addWidget(h_title)
        hero_left.addWidget(h_sub)
        hero_lay.addLayout(hero_left)

        slogan = QLabel("Design\nCreate\nInspire ✨")
        slogan.setStyleSheet("font-size: 15px; font-weight: 700; color: #A3E635; text-align: right;")
        slogan.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        hero_lay.addWidget(slogan)
        main_lay.addWidget(hero)

        # Studio Launch Modules
        mod_label = QLabel("Studio Workspaces")
        mod_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #E2E8F0;")
        main_lay.addWidget(mod_label)

        mod_grid = QHBoxLayout()
        mod_grid.setSpacing(12)
        modules = [
            ("wearlab", "👕", "WearLab", "Edit garments", "#38BDF8"),
            ("shapelab", "✏️", "ShapeLab", "Create & draw", "#FB7185"),
            ("markit", "🏷️", "MarkIt", "Add logos", "#FBBF24"),
            ("huebox", "🎨", "HueBox", "Play with colors", "#C084FC"),
            ("cutcraft", "✂️", "CutCraft", "Make stencils", "#A3E635"),
        ]
        for key, icon, name, desc, col in modules:
            card = StudioModuleCard(key, icon, name, desc, col)
            card.clicked.connect(self.openWorkspace.emit)
            mod_grid.addWidget(card)
        main_lay.addLayout(mod_grid)

        # Bottom Section (Recent Projects & Quick Actions)
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(20)

        # Recent Projects
        rec_box = QVBoxLayout()
        rec_title = QLabel("Recent Projects")
        rec_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #E2E8F0;")
        rec_box.addWidget(rec_title)

        rec_grid = QHBoxLayout()
        rec_grid.setSpacing(10)
        rec_grid.addWidget(RecentProjectItem("Tshirt_Design", "2 days ago", "👕"))
        rec_grid.addWidget(RecentProjectItem("Logo_Design", "4 days ago", "🌸"))
        rec_grid.addWidget(RecentProjectItem("Hoodie_Design", "6 days ago", "🧥"))
        rec_grid.addWidget(RecentProjectItem("Floral_Stencil", "1 week ago", "🌺"))
        rec_box.addLayout(rec_grid)
        bottom_row.addLayout(rec_box, 3)

        # Quick Actions
        act_box = QVBoxLayout()
        act_title = QLabel("Quick Actions")
        act_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #E2E8F0;")
        act_box.addWidget(act_title)

        act_new = QPushButton("✨  New Project")
        act_new.setObjectName("actionBtn")
        act_new.clicked.connect(lambda: self.openWorkspace.emit("wearlab"))

        act_import = QPushButton("📁  Import Image")
        act_import.setObjectName("actionBtn")
        act_import.clicked.connect(self.importImageRequested.emit)

        act_open = QPushButton("📂  Open Project")
        act_open.setObjectName("actionBtn")
        act_open.clicked.connect(lambda: self.openWorkspace.emit("myspace"))

        act_box.addWidget(act_new)
        act_box.addWidget(act_import)
        act_box.addWidget(act_open)
        act_box.addStretch(1)
        bottom_row.addLayout(act_box, 1)

        main_lay.addLayout(bottom_row)
        main_lay.addStretch(1)

        root_lay.addWidget(main_content, 1)