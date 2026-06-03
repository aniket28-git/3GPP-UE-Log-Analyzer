from __future__ import annotations

DARK_QSS = """
/* ── Base ─────────────────────────────────────────────────────── */
QMainWindow, QDialog, QWidget {
    background-color: #1e2130;
    color: #dde1f0;
    font-family: "Segoe UI", "Arial", sans-serif;
    font-size: 10pt;
}

/* ── Menu bar ─────────────────────────────────────────────────── */
QMenuBar {
    background-color: #15182a;
    color: #b0b8d8;
    border-bottom: 1px solid #2a2f4a;
    padding: 2px 0;
}
QMenuBar::item { padding: 4px 14px; border-radius: 4px; }
QMenuBar::item:selected { background-color: #4a80f0; color: #ffffff; }

QMenu {
    background-color: #252840;
    border: 1px solid #3a3f5c;
    border-radius: 6px;
    padding: 4px;
}
QMenu::item { padding: 5px 24px 5px 16px; border-radius: 4px; }
QMenu::item:selected { background-color: #4a80f0; color: #ffffff; }
QMenu::separator { background: #3a3f5c; height: 1px; margin: 4px 8px; }

/* ── Toolbar ──────────────────────────────────────────────────── */
QToolBar {
    background: #15182a;
    border: none;
    border-bottom: 1px solid #2a2f4a;
    spacing: 3px;
    padding: 4px 6px;
}
QToolButton {
    background: transparent;
    color: #8898c8;
    border: none;
    border-radius: 5px;
    padding: 5px 10px;
    font-size: 9pt;
}
QToolButton:hover  { background: #252840; color: #dde1f0; }
QToolButton:pressed { background: #4a80f0; color: white; }

/* ── Splitter ─────────────────────────────────────────────────── */
QSplitter::handle           { background: #2a2f4a; }
QSplitter::handle:horizontal { width: 3px; }
QSplitter::handle:vertical   { height: 3px; }

/* ── Group box ────────────────────────────────────────────────── */
QGroupBox {
    border: 1px solid #2a2f4a;
    border-radius: 8px;
    margin-top: 14px;
    padding: 8px 4px 4px 4px;
    color: #5a6898;
    font-size: 8pt;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
}

/* ── Buttons ──────────────────────────────────────────────────── */
QPushButton {
    background-color: #4a80f0;
    color: white;
    border: none;
    border-radius: 5px;
    padding: 5px 14px;
    font-weight: bold;
    font-size: 9pt;
    min-width: 60px;
}
QPushButton:hover  { background-color: #6097ff; }
QPushButton:pressed { background-color: #3060d0; }
QPushButton[flat="true"] {
    background-color: #252840;
    color: #8898c8;
}
QPushButton[flat="true"]:hover  { background-color: #353b5a; color: #dde1f0; }
QPushButton[flat="true"]:pressed { background-color: #2a2f4a; }

/* ── ComboBox ─────────────────────────────────────────────────── */
QComboBox {
    background-color: #252840;
    border: 1px solid #3a3f5c;
    border-radius: 5px;
    padding: 4px 8px;
    color: #dde1f0;
}
QComboBox:hover      { border-color: #4a80f0; }
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background-color: #252840;
    border: 1px solid #3a3f5c;
    border-radius: 4px;
    color: #dde1f0;
    selection-background-color: #4a80f0;
    selection-color: white;
    padding: 2px;
    outline: none;
}

/* ── Line / DateTime edit ─────────────────────────────────────── */
QLineEdit, QDateTimeEdit {
    background-color: #252840;
    border: 1px solid #3a3f5c;
    border-radius: 5px;
    padding: 4px 8px;
    color: #dde1f0;
}
QLineEdit:focus, QDateTimeEdit:focus { border-color: #4a80f0; }
QDateTimeEdit::up-button, QDateTimeEdit::down-button {
    background: #2a2f4a; border: none; width: 16px;
}

/* ── List widget ──────────────────────────────────────────────── */
QListWidget {
    background-color: #181b2d;
    border: 1px solid #2a2f4a;
    border-radius: 6px;
    color: #b0b8d8;
    outline: none;
}
QListWidget::item         { padding: 5px 8px; border-radius: 3px; }
QListWidget::item:selected { background-color: #4a80f0; color: white; }
QListWidget::item:hover   { background-color: #252840; }

/* ── Tab widget ───────────────────────────────────────────────── */
QTabWidget::pane {
    border: 1px solid #2a2f4a;
    border-radius: 6px;
    top: -1px;
    background: #1e2130;
}
QTabBar::tab {
    background: #181b2d;
    color: #5a6898;
    border: 1px solid #2a2f4a;
    border-bottom: none;
    padding: 7px 20px;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
    min-width: 110px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background: #1e2130;
    color: #4a80f0;
    border-bottom: 2px solid #4a80f0;
    font-weight: bold;
}
QTabBar::tab:hover:!selected { color: #dde1f0; background: #202435; }

/* ── Tree widget ──────────────────────────────────────────────── */
QTreeWidget {
    background-color: #181b2d;
    alternate-background-color: #1e2135;
    border: 1px solid #2a2f4a;
    border-radius: 6px;
    color: #b0b8d8;
    outline: none;
}
QTreeWidget::item                 { padding: 3px 2px; }
QTreeWidget::item:selected        { background-color: #4a80f0; color: white; }
QTreeWidget::item:hover:!selected { background-color: #252840; }

QHeaderView::section {
    background-color: #1e2135;
    color: #5a6898;
    border: none;
    border-bottom: 1px solid #2a2f4a;
    border-right: 1px solid #2a2f4a;
    padding: 5px 8px;
    font-weight: bold;
    font-size: 8pt;
    text-transform: uppercase;
    letter-spacing: 1px;
}

/* ── Scroll bars ──────────────────────────────────────────────── */
QScrollBar:vertical {
    background: #181b2d; width: 8px; margin: 0; border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #3a3f5c; border-radius: 4px; min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: #4a80f0; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QScrollBar:horizontal {
    background: #181b2d; height: 8px; margin: 0; border-radius: 4px;
}
QScrollBar::handle:horizontal {
    background: #3a3f5c; border-radius: 4px; min-width: 30px;
}
QScrollBar::handle:horizontal:hover { background: #4a80f0; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ── Progress bar ─────────────────────────────────────────────── */
QProgressBar {
    background-color: #252840;
    border: none;
    border-radius: 4px;
    text-align: center;
    color: transparent;
    max-height: 8px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4a80f0, stop:1 #7c63ff);
    border-radius: 4px;
}

/* ── Status bar ───────────────────────────────────────────────── */
QStatusBar {
    background: #15182a;
    border-top: 1px solid #2a2f4a;
    font-size: 9pt;
}
QStatusBar QLabel { color: #8898c8; }

/* ── Graphics view ────────────────────────────────────────────── */
QGraphicsView {
    background: #181b2d;
    border: 1px solid #2a2f4a;
    border-radius: 6px;
}

/* ── Misc ─────────────────────────────────────────────────────── */
QScrollArea          { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }
QLabel               { color: #b0b8d8; background: transparent; }

QToolTip {
    background: #252840;
    color: #dde1f0;
    border: 1px solid #4a80f0;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 9pt;
}
"""

# Semantic color palette
COL_PRIMARY  = "#4a80f0"
COL_SUCCESS  = "#2ed573"
COL_WARNING  = "#ffa502"
COL_ERROR    = "#ff4757"
COL_CRITICAL = "#a55eea"
COL_TEAL     = "#1eb8d0"
COL_MUTED    = "#5a6898"
COL_BG_CARD  = "#252840"
COL_BG_DEEP  = "#181b2d"
COL_BORDER   = "#2a2f4a"

# KPI name → accent color
KPI_ACCENT: dict[str, str] = {
    "Attach Success Rate":    COL_SUCCESS,
    "Avg Attach Setup Time":  COL_WARNING,
    "Handover Success Rate":  COL_PRIMARY,
    "RLF Count":              COL_ERROR,
    "Reestablishment Count":  COL_WARNING,
    "Avg RSRP":               COL_TEAL,
    "Avg RSRQ":               COL_TEAL,
    "Avg SINR":               COL_TEAL,
    "Avg PDN/PDU Setup Time": COL_WARNING,
    "Min RSRP":               COL_ERROR,
    "Max RSRP":               COL_SUCCESS,
}

# Timeline lane colors for dark theme
LANE_BG_EVEN = "#1c1f33"
LANE_BG_ODD  = "#181b2d"
LANE_GRID    = "#252840"
LANE_LABEL   = "#5a6898"


def apply(app) -> None:
    """Apply the dark theme to a QApplication instance."""
    app.setStyle("Fusion")
    app.setStyleSheet(DARK_QSS)
