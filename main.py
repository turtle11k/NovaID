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

from PySide6.QtWidgets import QApplication

import database as db
from auth import AuthService
from gui.main_window import MainWindow

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
    window = MainWindow(auth)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
