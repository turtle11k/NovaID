"""
gui/defender_tab.py
-------------------
The "Defender" tab: the NovaID account service.

Contains:
  * Registration form with a live password-strength indicator
    (bar + checklist + weak/medium/strong verdict).
  * Login form that uses AuthService.login().
  * Coloured banners and pop-up warnings for suspicious activity
    ("2 attempts left", "account locked", "login to a locked account").
  * An administrator panel: a table of all users with status, failed
    count and last-failure time, the full log of failed attempts, and
    an Unlock button.

Light, minimalist look driven by gui/styles.DEFENDER_STYLE.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox,
    QProgressBar, QPushButton, QSpinBox, QSplitter, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

import database as db
import password_strength as ps
from auth import AuthService, Outcome
from gui.icons import get_icon
from gui.styles import DEFENDER_STYLE, STRENGTH_COLORS


class DefenderTab(QWidget):
    """Account-service UI with registration, login and admin panel."""

    # Emitted when the user list changes, so other tabs can refresh.
    users_changed = Signal()

    def __init__(self, auth: AuthService, parent=None):
        super().__init__(parent)
        self.auth = auth
        self.setObjectName("DefenderTab")
        self.setStyleSheet(DEFENDER_STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(18)

        # Header
        header = QVBoxLayout()
        header.setSpacing(2)
        title = QLabel("NovaID")
        title.setObjectName("Title")
        subtitle = QLabel("A demo account service — register, sign in, and watch "
                          "the protections work.")
        subtitle.setObjectName("Subtitle")
        header.addWidget(title)
        header.addWidget(subtitle)
        root.addLayout(header)

        # Banner (hidden until there is something to say)
        self.banner = QLabel("")
        self.banner.setWordWrap(True)
        self.banner.setVisible(False)
        self.banner.setStyleSheet(self._banner_css("#30a46c"))
        root.addWidget(self.banner)

        # Register + login cards side by side, wrapped for the splitter.
        forms = QWidget()
        top = QHBoxLayout(forms)
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(18)
        top.addWidget(self._build_register_card(), 1)
        top.addWidget(self._build_login_card(), 1)

        # Vertical splitter: forms on top, admin panel below. The admin panel
        # gets most of the height so its tables show many rows at once, and
        # the divider can be dragged to rebalance.
        splitter = QSplitter(Qt.Vertical)
        splitter.setObjectName("MainSplit")
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(forms)
        splitter.addWidget(self._build_admin_card())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([250, 540])
        root.addWidget(splitter, 1)

        self.refresh_admin()

    # --- card builders -----------------------------------------------------

    def _build_register_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(10)

        lay.addWidget(self._section("Create an account"))

        self.reg_user = QLineEdit()
        self.reg_user.setPlaceholderText("Username")
        self.reg_pass = QLineEdit()
        self.reg_pass.setPlaceholderText("Password")
        self.reg_pass.setEchoMode(QLineEdit.Password)
        self.reg_pass.textChanged.connect(self._on_password_typed)

        lay.addWidget(self.reg_user)
        lay.addWidget(self.reg_pass)

        # Strength bar + verdict
        bar_row = QHBoxLayout()
        self.strength_bar = QProgressBar()
        self.strength_bar.setRange(0, 100)
        self.strength_bar.setValue(0)
        self.strength_bar.setTextVisible(False)
        self.strength_bar.setFixedHeight(10)
        self.verdict_lbl = QLabel("—")
        self.verdict_lbl.setFixedWidth(70)
        self.verdict_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        bar_row.addWidget(self.strength_bar, 1)
        bar_row.addWidget(self.verdict_lbl)
        lay.addLayout(bar_row)

        self.checklist_lbl = QLabel("Type a password to see its strength.")
        self.checklist_lbl.setWordWrap(True)
        self.checklist_lbl.setStyleSheet("color:#6b7280; font-size:12px;")
        lay.addWidget(self.checklist_lbl)

        show = QPushButton("Show / hide password")
        show.setObjectName("Ghost")
        show.setCheckable(True)
        show.toggled.connect(
            lambda on: self.reg_pass.setEchoMode(
                QLineEdit.Normal if on else QLineEdit.Password
            )
        )
        lay.addWidget(show)

        btn = QPushButton("Register")
        btn.clicked.connect(self._on_register)
        lay.addWidget(btn)

        return card

    def _build_login_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(10)

        lay.addWidget(self._section("Sign in"))

        self.log_user = QLineEdit()
        self.log_user.setPlaceholderText("Username")
        self.log_pass = QLineEdit()
        self.log_pass.setPlaceholderText("Password")
        self.log_pass.setEchoMode(QLineEdit.Password)
        self.log_pass.returnPressed.connect(self._on_login)

        lay.addWidget(self.log_user)
        lay.addWidget(self.log_pass)

        # Lockout threshold control
        thr_row = QHBoxLayout()
        thr_row.addWidget(QLabel("Lock after"))
        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(3, 5)
        self.threshold_spin.setValue(self.auth.lockout_threshold)
        self.threshold_spin.valueChanged.connect(self._on_threshold_changed)
        thr_row.addWidget(self.threshold_spin)
        thr_row.addWidget(QLabel("wrong attempts"))
        thr_row.addStretch(1)
        lay.addLayout(thr_row)

        btn = QPushButton("Sign in")
        btn.clicked.connect(self._on_login)
        lay.addWidget(btn)

        lay.addStretch(1)
        return card

    def _build_admin_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(10)

        head = QHBoxLayout()
        head.addWidget(self._section("Administrator panel"))
        head.addStretch(1)
        self.row_count_lbl = QLabel("")
        self.row_count_lbl.setStyleSheet("color:#6b7280; font-size:12px;")
        head.addWidget(self.row_count_lbl)
        unlock_btn = QPushButton("Unlock selected")
        unlock_btn.setObjectName("Ghost")
        unlock_btn.clicked.connect(self._on_unlock_selected)
        head.addWidget(unlock_btn)
        lay.addLayout(head)

        # The two tables sit side by side in a horizontal splitter, so each
        # gets the full height of the panel instead of being stacked and
        # squeezed to a couple of rows. The divider is draggable.
        tables = QSplitter(Qt.Horizontal)
        tables.setChildrenCollapsible(False)

        # --- Users ---
        users_box = QWidget()
        ubl = QVBoxLayout(users_box)
        ubl.setContentsMargins(0, 0, 0, 0)
        ubl.setSpacing(6)
        ubl.addWidget(self._mini_label("Users"))
        self.users_table = QTableWidget(0, 4)
        self.users_table.setHorizontalHeaderLabels(
            ["User", "Status", "Failed", "Last failed attempt"]
        )
        self._tune_table(self.users_table, stretch_cols=(0, 3), fit_cols=(1, 2))
        self.users_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.users_table.setSelectionMode(QTableWidget.SingleSelection)
        ubl.addWidget(self.users_table)
        tables.addWidget(users_box)

        # --- Failed-attempt log ---
        log_box = QWidget()
        lbl = QVBoxLayout(log_box)
        lbl.setContentsMargins(0, 0, 0, 0)
        lbl.setSpacing(6)
        lbl.addWidget(self._mini_label("Failed-attempt log (newest first)"))
        self.log_table = QTableWidget(0, 3)
        self.log_table.setHorizontalHeaderLabels(["Time", "User", "Reason"])
        self._tune_table(self.log_table, stretch_cols=(2,), fit_cols=(0, 1))
        lbl.addWidget(self.log_table)
        tables.addWidget(log_box)

        tables.setSizes([540, 420])
        lay.addWidget(tables, 1)

        return card

    # --- small helpers -----------------------------------------------------

    def _section(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("SectionTitle")
        return lbl

    def _mini_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("color:#6b7280; font-size:12px; font-weight:600;")
        return lbl

    def _tune_table(self, table: QTableWidget, stretch_cols=(), fit_cols=()) -> None:
        """Shared table styling: compact rows, readable columns, more rows
        visible at once so the panel does not force constant scrolling."""
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setWordWrap(False)
        table.setAlternatingRowColors(True)
        table.setMinimumHeight(240)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(30)
        header = table.horizontalHeader()
        header.setHighlightSections(False)
        for c in stretch_cols:
            header.setSectionResizeMode(c, QHeaderView.Stretch)
        for c in fit_cols:
            header.setSectionResizeMode(c, QHeaderView.ResizeToContents)

    def _banner_css(self, color: str) -> str:
        return (
            f"background: {color}1a; color: {color};"
            f"border: 1px solid {color}55; border-radius: 10px;"
            "padding: 10px 14px; font-weight: 600;"
        )

    def show_banner(self, text: str, color: str) -> None:
        self.banner.setText(text)
        self.banner.setStyleSheet(self._banner_css(color))
        self.banner.setVisible(True)

    # --- events ------------------------------------------------------------

    def _on_password_typed(self, text: str) -> None:
        if not text:
            self.strength_bar.setValue(0)
            self.verdict_lbl.setText("—")
            self.checklist_lbl.setText("Type a password to see its strength.")
            return

        result = ps.evaluate(text)
        color = STRENGTH_COLORS[result.verdict]
        self.strength_bar.setValue(int(result.ratio * 100))
        self.strength_bar.setStyleSheet(
            "QProgressBar{background:#eceef4;border-radius:5px;}"
            f"QProgressBar::chunk{{background:{color};border-radius:5px;}}"
        )
        self.verdict_lbl.setText(result.verdict.capitalize())
        self.verdict_lbl.setStyleSheet(f"color:{color}; font-weight:600;")
        self.checklist_lbl.setText("  •  ".join(result.feedback))

    def _on_register(self) -> None:
        username = self.reg_user.text().strip()
        password = self.reg_pass.text()
        try:
            self.auth.register(username, password)
        except ValueError as exc:
            QMessageBox.warning(self, "Cannot register", str(exc))
            return

        verdict = ps.evaluate(password).verdict
        self.reg_user.clear()
        self.reg_pass.clear()
        self._on_password_typed("")
        self.show_banner(
            f"Account '{username}' created (password rated: {verdict}).",
            STRENGTH_COLORS.get(verdict, "#30a46c"),
        )
        self.refresh_admin()
        self.users_changed.emit()

    def _on_login(self) -> None:
        username = self.log_user.text().strip()
        password = self.log_pass.text()
        if not username:
            return
        result = self.auth.login(username, password)
        self._react_to_login(result)
        self.refresh_admin()

    def _react_to_login(self, result) -> None:
        """Show the right banner / pop-up for a login outcome."""
        if result.outcome is Outcome.SUCCESS:
            self.show_banner(f"Welcome back, {result.username}.", "#30a46c")

        elif result.outcome is Outcome.NO_SUCH_USER:
            self.show_banner(result.message, "#e5484d")

        elif result.outcome is Outcome.WRONG_PASSWORD:
            color = "#e6a700" if result.attempts_remaining > 1 else "#e5484d"
            self.show_banner(result.message, color)
            if result.attempts_remaining == 1:
                QMessageBox.warning(
                    self, "Suspicious activity",
                    f"Only 1 attempt left for '{result.username}' "
                    "before the account is locked.",
                )

        elif result.outcome is Outcome.LOCKED_NOW:
            self.show_banner(result.message, "#e5484d")
            QMessageBox.critical(
                self, "Account locked",
                f"'{result.username}' has been locked after too many "
                "wrong attempts. An administrator must unlock it.",
            )

        elif result.outcome is Outcome.LOCKED:
            self.show_banner(
                f"Attempt to sign in to the locked account "
                f"'{result.username}' was refused.",
                "#e5484d",
            )
            QMessageBox.critical(
                self, "Locked account",
                f"'{result.username}' is locked. Even the correct password "
                "will not work until an administrator unlocks it.",
            )

    def _on_threshold_changed(self, value: int) -> None:
        self.auth.set_threshold(value)

    def _on_unlock_selected(self) -> None:
        row = self.users_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Unlock", "Select a user row first.")
            return
        username = self.users_table.item(row, 0).text()
        self.auth.unlock(username)
        self.show_banner(f"Account '{username}' unlocked.", "#30a46c")
        self.refresh_admin()
        self.users_changed.emit()

    # --- refresh -----------------------------------------------------------

    def refresh_admin(self) -> None:
        conn = self.auth.conn

        users = db.list_users(conn)
        self.users_table.setRowCount(len(users))
        for r, u in enumerate(users):
            locked = bool(u["is_locked"])
            cells = [
                u["username"],
                "Locked" if locked else "Active",
                str(u["failed_count"]),
                u["last_failed_at"] or "—",
            ]
            for c, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if c == 1:
                    item.setIcon(get_icon("locked") if locked else get_icon("active"))
                    if locked:
                        item.setForeground(Qt.red)
                self.users_table.setItem(r, c, item)

        failures = db.get_failed_attempts(conn)
        self.log_table.setRowCount(len(failures))
        for r, a in enumerate(failures):
            cells = [a["created_at"], a["username"], a["reason"]]
            for c, text in enumerate(cells):
                self.log_table.setItem(r, c, QTableWidgetItem(text))

        locked_n = sum(1 for u in users if u["is_locked"])
        self.row_count_lbl.setText(
            f"{len(users)} user(s) · {locked_n} locked · "
            f"{len(failures)} failed attempt(s)"
        )
