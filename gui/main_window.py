"""
gui/main_window.py
------------------
The main window: a scoreboard on top, the two tabs below
(Defender / Tester), and a "New round" button that clears all locks,
the attempt log and the score.
"""

from __future__ import annotations

from PySide6.QtCore import QSize
from PySide6.QtWidgets import (
    QHBoxLayout, QMainWindow, QMessageBox, QPushButton, QTabWidget,
    QVBoxLayout, QWidget,
)

from auth import AuthService
from gui.defender_tab import DefenderTab
from gui.icons import get_icon
from gui.scoreboard import GameState, ScoreBoard
from gui.styles import TAB_STYLE
from gui.tester_tab import TesterTab


class MainWindow(QMainWindow):
    def __init__(self, auth: AuthService):
        super().__init__()
        self.auth = auth
        self.state = GameState()

        self.setWindowTitle("NovaID — Authentication Security Game")
        self.resize(1040, 860)
        self.setMinimumSize(900, 640)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # Top strip: scoreboard + new round button
        top = QHBoxLayout()
        self.scoreboard = ScoreBoard(self.state)
        top.addWidget(self.scoreboard, 1)
        new_round = QPushButton("New round")
        new_round.clicked.connect(self._on_new_round)
        new_round.setFixedHeight(44)
        top.addWidget(new_round)
        root.addLayout(top)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(TAB_STYLE)
        self.tabs.setIconSize(QSize(18, 18))
        self.defender = DefenderTab(auth)
        self.tester = TesterTab(auth, self.state)
        self.tabs.addTab(self.defender, get_icon("defender"), "Defender")
        self.tabs.addTab(self.tester, get_icon("tester"), "Tester")
        root.addWidget(self.tabs, 1)

        # Keep tester's account list in sync with the defender.
        self.defender.users_changed.connect(self.tester.refresh_accounts)
        self.tabs.currentChanged.connect(self._on_tab_changed)

    def _on_tab_changed(self, index: int) -> None:
        # Refresh whichever tab we switch to so it reflects the latest state.
        if self.tabs.widget(index) is self.tester:
            self.tester.refresh_accounts()
        elif self.tabs.widget(index) is self.defender:
            self.defender.refresh_admin()

    def _on_new_round(self) -> None:
        self.auth.new_round()
        self.state.reset()
        self.defender.refresh_admin()
        self.tester.refresh_accounts()
        self.tester._println("")
        self.tester._println("### NEW ROUND — all locks, logs and scores cleared ###")
        QMessageBox.information(
            self, "New round",
            "All accounts unlocked, the attempt log cleared and the score reset.",
        )
