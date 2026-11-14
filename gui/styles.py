"""
gui/styles.py
-------------
Qt style sheets for the two tabs. Kept in one place so the look stays
consistent and easy to tweak.

  * DEFENDER_STYLE — a light, minimalist card style: pale background,
    generous spacing, rounded fields and buttons, soft shadows, system
    font. No logos or real company names.
  * TESTER_STYLE — a dark "terminal" style: near-black background, green
    monospace text, for the automated attempt log.

Strength-bar colours and a few shared palette values are exposed as
constants so widgets can reuse them from Python.
"""

# Shared palette
INK = "#1f2430"
MUTED = "#6b7280"
ACCENT = "#4f6ef7"
CARD_BG = "#ffffff"
APP_BG = "#f4f6fb"

# Strength verdict colours (weak / medium / strong)
STRENGTH_COLORS = {
    "weak": "#e5484d",
    "medium": "#e6a700",
    "strong": "#30a46c",
}

# Terminal palette
TERM_BG = "#0b0f0a"
TERM_GREEN = "#39ff8b"
TERM_DIM = "#1e7a46"


DEFENDER_STYLE = f"""
QWidget#DefenderTab {{
    background: {APP_BG};
    color: {INK};
    font-family: -apple-system, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
    font-size: 14px;
}}

QFrame#Card {{
    background: {CARD_BG};
    border: 1px solid #e6e8ef;
    border-radius: 16px;
}}

QLabel#Title {{
    font-size: 22px;
    font-weight: 600;
    color: {INK};
}}

QLabel#Subtitle {{
    color: {MUTED};
    font-size: 13px;
}}

QLabel#SectionTitle {{
    font-size: 16px;
    font-weight: 600;
    color: {INK};
}}

QLineEdit {{
    background: #fbfcfe;
    color: {INK};
    border: 1px solid #d8dce6;
    border-radius: 10px;
    padding: 10px 12px;
    selection-background-color: {ACCENT};
    selection-color: #ffffff;
}}
QLineEdit:focus {{
    border: 1px solid {ACCENT};
    background: #ffffff;
}}

QPushButton {{
    background: {ACCENT};
    color: white;
    border: none;
    border-radius: 10px;
    padding: 10px 18px;
    font-weight: 600;
}}
QPushButton:hover {{ background: #3f5de0; }}
QPushButton:pressed {{ background: #3550c8; }}
QPushButton:disabled {{ background: #c3cbe6; color: #eef0f7; }}

QPushButton#Ghost {{
    background: transparent;
    color: {ACCENT};
    border: 1px solid #c9d1ef;
}}
QPushButton#Ghost:hover {{ background: #eef1fe; }}

QTableWidget {{
    background: {CARD_BG};
    color: {INK};
    border: 1px solid #e6e8ef;
    border-radius: 12px;
    gridline-color: #eef0f6;
    alternate-background-color: #f7f8fc;
    selection-background-color: #e8ecfd;
    selection-color: {INK};
}}
QTableWidget::item {{ padding: 4px 6px; }}
QHeaderView::section {{
    background: #f7f8fc;
    color: {MUTED};
    border: none;
    border-bottom: 1px solid #e6e8ef;
    padding: 8px;
    font-weight: 600;
}}

QSpinBox {{
    background: #fbfcfe;
    color: {INK};
    border: 1px solid #d8dce6;
    border-radius: 8px;
    padding: 4px 8px;
}}
"""


# Tab bar: explicit light styling so the *selected* tab is white instead of
# the macOS system-blue accent (which the indigo icon used to blend into).
TAB_STYLE = f"""
QTabWidget::pane {{
    border: 1px solid #e6e8ef;
    border-radius: 12px;
    background: transparent;
    top: -1px;
}}
QTabBar::tab {{
    background: #e9edf6;
    color: {MUTED};
    padding: 8px 20px;
    margin-right: 6px;
    border: 1px solid #e3e7f0;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    border-bottom: none;
}}
QTabBar::tab:selected {{
    background: #ffffff;
    color: {INK};
    font-weight: 600;
}}
QTabBar::tab:hover:!selected {{
    background: #eff2f9;
}}
"""


TESTER_STYLE = f"""
QWidget#TesterTab {{
    background: {TERM_BG};
    color: {TERM_GREEN};
    font-family: 'SF Mono', 'Menlo', 'Consolas', 'DejaVu Sans Mono', monospace;
    font-size: 13px;
}}

QLabel#TermTitle {{
    color: {TERM_GREEN};
    font-size: 18px;
    font-weight: 700;
}}
QLabel#TermHint {{ color: {TERM_DIM}; }}

QComboBox {{
    background: #06160d;
    color: {TERM_GREEN};
    border: 1px solid {TERM_DIM};
    border-radius: 6px;
    padding: 6px 10px;
}}
QComboBox QAbstractItemView {{
    background: #06160d;
    color: {TERM_GREEN};
    selection-background-color: {TERM_DIM};
}}

QPlainTextEdit {{
    background: #050a06;
    color: {TERM_GREEN};
    border: 1px solid {TERM_DIM};
    border-radius: 8px;
    padding: 10px;
    font-family: 'SF Mono', 'Menlo', 'Consolas', 'DejaVu Sans Mono', monospace;
}}

QPushButton {{
    background: #0f2a1a;
    color: {TERM_GREEN};
    border: 1px solid {TERM_GREEN};
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}}
QPushButton:hover {{ background: #153b24; }}
QPushButton:disabled {{ color: {TERM_DIM}; border-color: {TERM_DIM}; }}
"""
