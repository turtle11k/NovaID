"""
gui/scoreboard.py
-----------------
A tiny shared game-state object plus a compact scoreboard widget.

The score has two sides:
  * Tester points  — how many accounts were cracked (a password guessed).
  * Defender points — how many accounts withstood a full series
    (locked out or never guessed).

Both tabs reference the same GameState instance; the scoreboard widget
listens to its `changed` signal and refreshes.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from gui.icons import get_pixmap


class GameState(QObject):
    """Holds the running score and emits `changed` when it updates."""

    changed = Signal()

    def __init__(self):
        super().__init__()
        self.tester_points = 0
        self.defender_points = 0
        self.last_summary = "No rounds played yet."

    def record_result(self, guessed: bool, locked: bool, username: str,
                      guessed_password=None):
        """Update the score from the outcome of one tester series."""
        if guessed:
            self.tester_points += 1
            self.last_summary = (
                f"Tester cracked '{username}' with '{guessed_password}'. "
                "The password was on the common-password list."
            )
        else:
            self.defender_points += 1
            if locked:
                self.last_summary = (
                    f"Defender held: '{username}' locked after too many "
                    "wrong attempts — the series was stopped."
                )
            else:
                self.last_summary = (
                    f"Defender held: '{username}' resisted the whole list — "
                    "the password was not among the common ones."
                )
        self.changed.emit()

    def reset(self):
        self.tester_points = 0
        self.defender_points = 0
        self.last_summary = "New round — scores and lockouts cleared."
        self.changed.emit()


class ScoreBoard(QFrame):
    """Compact two-sided score display with a one-line round summary."""

    def __init__(self, state: GameState, parent=None):
        super().__init__(parent)
        self.state = state
        self.setObjectName("Card")

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(8)

        row = QHBoxLayout()
        row.setSpacing(24)

        # Defender side: icon + score
        d_wrap = QHBoxLayout()
        d_wrap.setSpacing(8)
        self.defender_icon = QLabel()
        self.defender_icon.setPixmap(get_pixmap("defender", 20))
        self.defender_lbl = QLabel()
        self.defender_lbl.setStyleSheet("font-size:15px; font-weight:600;")
        d_wrap.addWidget(self.defender_icon)
        d_wrap.addWidget(self.defender_lbl)

        # Tester side: icon + score
        t_wrap = QHBoxLayout()
        t_wrap.setSpacing(8)
        self.tester_icon = QLabel()
        self.tester_icon.setPixmap(get_pixmap("tester", 20))
        self.tester_lbl = QLabel()
        self.tester_lbl.setStyleSheet("font-size:15px; font-weight:600;")
        t_wrap.addWidget(self.tester_icon)
        t_wrap.addWidget(self.tester_lbl)

        row.addLayout(d_wrap)
        row.addStretch(1)
        row.addLayout(t_wrap)
        root.addLayout(row)

        self.summary_lbl = QLabel()
        self.summary_lbl.setWordWrap(True)
        self.summary_lbl.setStyleSheet("color:#6b7280; font-size:12px;")
        root.addWidget(self.summary_lbl)

        state.changed.connect(self.refresh)
        self.refresh()

    def refresh(self):
        self.defender_lbl.setText(f"Defender: {self.state.defender_points}")
        self.tester_lbl.setText(f"Tester: {self.state.tester_points}")
        self.summary_lbl.setText(self.state.last_summary)
