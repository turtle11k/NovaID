"""
gui/tester_tab.py
-----------------
The "Tester" tab: a dark terminal screen that runs an automated series
of login attempts against one chosen account using the built-in list of
common weak passwords.

Shows a live, line-by-line log: attempt number, the password tried, the
result, the time, and the system's reaction (warning / lockout). When
the series ends it prints a plain-language summary and updates the
shared scoreboard.

The attempts run in a TestWorker (QThread) so the window stays
responsive and you can watch each line appear.
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton,
    QVBoxLayout, QWidget,
)

import database as db
from auth import AuthService, Outcome
from gui.scoreboard import GameState
from gui.styles import TESTER_STYLE
from test_runner import COMMON_PASSWORD_LIST, TestWorker


class TesterTab(QWidget):
    """Terminal-style automated password testing screen."""

    def __init__(self, auth: AuthService, state: GameState, parent=None):
        super().__init__(parent)
        self.auth = auth
        self.state = state
        self.worker = None

        self.setObjectName("TesterTab")
        self.setStyleSheet(TESTER_STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(14)

        title = QLabel("tester // password resilience probe")
        title.setObjectName("TermTitle")
        root.addWidget(title)

        hint = QLabel(
            f"Tries {len(COMMON_PASSWORD_LIST)} common weak passwords against the "
            "selected account, using the same login function as the service."
        )
        hint.setObjectName("TermHint")
        hint.setWordWrap(True)
        root.addWidget(hint)

        # Controls
        controls = QHBoxLayout()
        controls.setSpacing(10)
        self.account_combo = QComboBox()
        controls.addWidget(QLabel("target:"))
        controls.addWidget(self.account_combo, 1)

        self.start_btn = QPushButton("▶ run series")
        self.start_btn.clicked.connect(self._on_start)
        self.stop_btn = QPushButton("■ stop")
        self.stop_btn.clicked.connect(self._on_stop)
        self.stop_btn.setEnabled(False)
        self.clear_btn = QPushButton("clear log")
        self.clear_btn.clicked.connect(lambda: self.log.clear())

        controls.addWidget(self.start_btn)
        controls.addWidget(self.stop_btn)
        controls.addWidget(self.clear_btn)
        root.addLayout(controls)

        # Live log
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        root.addWidget(self.log, 1)

        self.refresh_accounts()
        self._println("system ready. select a target and run the series.")

    # --- account list ------------------------------------------------------

    def refresh_accounts(self) -> None:
        current = self.account_combo.currentText()
        self.account_combo.clear()
        for u in db.list_users(self.auth.conn):
            self.account_combo.addItem(u["username"])
        # keep selection if still present
        idx = self.account_combo.findText(current)
        if idx >= 0:
            self.account_combo.setCurrentIndex(idx)

    # --- logging -----------------------------------------------------------

    def _println(self, text: str) -> None:
        self.log.appendPlainText(text)
        self.log.verticalScrollBar().setValue(
            self.log.verticalScrollBar().maximum()
        )

    # --- run / stop --------------------------------------------------------

    def _on_start(self) -> None:
        username = self.account_combo.currentText()
        if not username:
            self._println("! no account selected.")
            return
        if self.worker is not None and self.worker.isRunning():
            return

        self._println("")
        self._println(f"=== starting series against '{username}' "
                     f"(threshold: lock after {self.auth.lockout_threshold}) ===")

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.account_combo.setEnabled(False)

        self.worker = TestWorker(
            db_path=self.auth.db_path,
            username=username,
            threshold=self.auth.lockout_threshold,
        )
        self.worker.attempted.connect(self._on_attempt)
        self.worker.finished_series.connect(self._on_finished)
        self.worker.start()

    def _on_stop(self) -> None:
        if self.worker is not None:
            self.worker.cancel()
            self._println("... stop requested.")

    def _on_attempt(self, event) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        mark = "+" if event.guessed else ("x" if event.stopped else "-")
        line = (f"[{ts}] #{event.index:02d}  try={event.password:<14} "
                f"[{mark}] {event.outcome.value:<14} {event.message}")
        self._println(line)

    def _on_finished(self, result: dict) -> None:
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.account_combo.setEnabled(True)

        username = result["username"]
        self._println("")
        if result["cancelled"]:
            self._println("=== series cancelled by user ===")
        elif result["guessed"]:
            self._println(
                f"=== RESULT: cracked '{username}' with "
                f"'{result['guessed_password']}' after "
                f"{result['attempts_made']} attempt(s). Weak password. ==="
            )
        elif result["locked"]:
            self._println(
                f"=== RESULT: '{username}' locked after "
                f"{result['attempts_made']} wrong attempts — series stopped. "
                "Defence held. ==="
            )
        else:
            self._println(
                f"=== RESULT: exhausted the list, '{username}' not cracked. "
                "Strong password. ==="
            )

        # Update the shared score (only for a completed, non-cancelled run).
        if not result["cancelled"]:
            self.state.record_result(
                guessed=result["guessed"],
                locked=result["locked"],
                username=username,
                guessed_password=result["guessed_password"],
            )
