"""
main.py
-------
Entry point for the NovaID authentication-security game.

Starts the Qt application, opens (and if needed creates) the local SQLite
database, seeds three demo users on first run, and shows the main window.

Run:  python main.py
"""

from __future__ import annotations

import sys

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

import database as db
from auth import AuthService
from gui.main_window import MainWindow


def apply_light_theme(app: QApplication) -> None:
    """Force a fixed light theme on every platform.

    Without this, Windows (especially in dark mode / windowed mode) hands Qt
    a dark system palette, so text defaults to white and becomes invisible on
    the app's white cards. We pin the Fusion style and a light palette so the
    look is identical everywhere. The dark "Tester" tab sets its own colours
    via its stylesheet, which overrides the palette, so it stays dark.
    """
    app.setStyle("Fusion")

    ink = QColor("#1f2430")
    muted = QColor("#6b7280")
    pal = QPalette()
    pal.setColor(QPalette.Window, QColor("#f4f6fb"))
    pal.setColor(QPalette.WindowText, ink)
    pal.setColor(QPalette.Base, QColor("#ffffff"))
    pal.setColor(QPalette.AlternateBase, QColor("#f7f8fc"))
    pal.setColor(QPalette.Text, ink)
    pal.setColor(QPalette.Button, QColor("#eef1f7"))
    pal.setColor(QPalette.ButtonText, ink)
    pal.setColor(QPalette.ToolTipBase, QColor("#ffffff"))
    pal.setColor(QPalette.ToolTipText, ink)
    pal.setColor(QPalette.PlaceholderText, muted)
    pal.setColor(QPalette.Highlight, QColor("#4f6ef7"))
    pal.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    for role in (QPalette.Text, QPalette.WindowText, QPalette.ButtonText):
        pal.setColor(QPalette.Disabled, role, muted)
    app.setPalette(pal)

# Three demo users required by the task: one weak, one medium, one strong.
DEMO_USERS = [
    ("alice", "123456"),                 # weak — on the common list
    ("bob", "Sunshine7"),                # medium
    ("carol", "Tr0ub4dour&3xplore!"),    # strong
]


def seed_demo_users(auth: AuthService) -> None:
    """Create demo users if they do not already exist."""
    for username, password in DEMO_USERS:
        if db.get_user(auth.conn, username) is None:
            auth.register(username, password)


def main() -> int:
    conn = db.connect()
    db.init_db(conn)

    auth = AuthService(conn)
    seed_demo_users(auth)

    app = QApplication(sys.argv)
    apply_light_theme(app)
    window = MainWindow(auth)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
