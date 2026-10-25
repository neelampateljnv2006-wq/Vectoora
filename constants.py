"""
constants.py - Updated Tools with Lasso Erase
"""
from enum import Enum, auto

class Tool(Enum):
    SELECT = auto()
    BUCKET = auto()
    LASSO_ERASE = auto()
    ERASER = auto()
    PEN = auto()
    RECTANGLE = auto()
    CIRCLE = auto()
    LINE = auto()
    POLYGON = auto()
    TEXT = auto()

VECTOORA_THEME = """
QMainWindow { background-color: #06090F; }
QFrame#topHeader { background-color: #0B0F19; border-bottom: 1px solid #162032; }
QFrame#primarySidebar { background-color: #070B12; border-right: 1px solid #131C2E; }
QFrame#toolsPanel { background-color: #0B0F19; border-right: 1px solid #162032; }
QFrame#inspectorPanel { background-color: #0B0F19; border-left: 1px solid #162032; }
QFrame#canvasStatusBar { background-color: #070B12; border-top: 1px solid #131C2E; }
QFrame#floatingActionPill { background-color: #0E1626; border: 1px solid #1E2D47; border-radius: 20px; }
QPushButton.pillBtn { background: transparent; border: none; color: #CBD5E1; font-size: 11px; padding: 4px 8px; font-weight: 500; }
QPushButton.pillBtn:hover { color: #A3E635; }
QPushButton.navBtn { background: transparent; border: none; color: #94A3B8; font-size: 12px; font-weight: 600; text-align: left; padding: 8px 12px; border-radius: 8px; }
QPushButton.navBtn:hover { background-color: #111827; color: #F8FAFC; }
QPushButton.navBtnActive { background-color: #A3E635; border: none; color: #070B11; font-size: 12px; font-weight: 700; text-align: left; padding: 8px 12px; border-radius: 8px; }
QPushButton.toolItem { background: transparent; border: none; color: #CBD5E1; font-size: 12px; text-align: left; padding: 6px 10px; border-radius: 6px; }
QPushButton.toolItem:hover { background-color: #111827; color: #F8FAFC; }
QPushButton.toolItemChecked { background-color: #162312; border: 1px solid #A3E635; color: #A3E635; font-size: 12px; font-weight: bold; text-align: left; padding: 6px 10px; border-radius: 6px; }
QPushButton.shapeBtn { background-color: #111827; border: 1px solid #1E2D44; border-radius: 6px; color: #CBD5E1; font-size: 14px; }
QPushButton.shapeBtn:hover { border-color: #A3E635; background-color: #162032; }
QLineEdit.coordInput { background-color: #111827; border: 1px solid #1E2D44; border-radius: 6px; color: #F8FAFC; padding: 4px 8px; font-size: 11px; }
QLineEdit.coordInput:focus { border-color: #A3E635; }
QSlider::groove:horizontal { height: 4px; background: #1E2D44; border-radius: 2px; }
QSlider::sub-page:horizontal { background: #A3E635; border-radius: 2px; }
QSlider::handle:horizontal { width: 12px; margin-top: -4px; margin-bottom: -4px; border-radius: 6px; background: #A3E635; }
"""
