"""
test_runner.py
--------------
The "tester" side of the game. It runs an automated series of login
attempts against one chosen account, trying passwords from a built-in
teaching list of common weak passwords, one by one, with a small delay
so the process is visible on screen.

It uses *exactly the same* AuthService.login() method as the defender
tab, so the lockout policy applies identically: a weak password that is
on the list gets guessed, a strong password does not, and the account
locks after N consecutive misses — which stops the series early.

The work happens in a QThread (TestWorker) so the GUI never freezes.
Each attempt emits a signal the GUI appends to the live terminal log.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from PySide6.QtCore import QThread, Signal

import database as db
from auth import AuthService, Outcome

# ~50 of the most common weak passwords, for teaching purposes only.
COMMON_PASSWORD_LIST = [
    "123456", "password", "123456789", "12345678", "12345", "qwerty",
    "1234567", "111111", "1234567890", "123123", "abc123", "1234",
    "password1", "iloveyou", "qwerty123", "000000", "admin", "welcome",
    "monkey", "dragon", "letmein", "login", "princess", "qwertyuiop",
    "solo", "passw0rd", "starwars", "sunshine", "master", "hello",
    "freedom", "whatever", "trustno1", "football", "jordan", "superman",
    "harley", "1q2w3e4r", "michael", "shadow", "ashley", "baseball",
    "696969", "batman", "pepper", "zaq12wsx", "flower", "hottie",
    "loveme", "654321",
]


@dataclass
class AttemptEvent:
    """One line for the live log."""

    index: int          # 1-based attempt number
    password: str       # the password that was tried
    outcome: Outcome    # result from AuthService
    message: str        # system reaction text
    guessed: bool       # True if this attempt signed in
    stopped: bool       # True if the account locked on this attempt


class TestWorker(QThread):
    """Runs the password series against one account in a background thread."""

    # Emitted once per attempt with an AttemptEvent payload.
    attempted = Signal(object)
    # Emitted once when the whole series ends. Payload: result dict.
    finished_series = Signal(object)

    def __init__(
        self,
        db_path: str,
        username: str,
        threshold: int,
        passwords=None,
        delay: float = 0.35,
        parent=None,
    ):
        super().__init__(parent)
        # Store only plain data here. The SQLite connection and AuthService
        # are created inside run(), on the worker thread, because SQLite
        # objects may only be used from the thread that created them.
        self.db_path = db_path
        self.username = username
        self.threshold = threshold
        self.passwords = list(passwords) if passwords else list(COMMON_PASSWORD_LIST)
        self.delay = delay
        self._cancelled = False

    def cancel(self) -> None:
        """Ask the series to stop after the current attempt."""
        self._cancelled = True

    def run(self) -> None:  # noqa: D401 - QThread entry point
        guessed_password = None
        locked = False
        attempts_made = 0
        conn = None

        try:
            # Own connection + service, bound to this thread.
            conn = db.connect(self.db_path)
            auth = AuthService(conn, self.threshold, db_path=self.db_path)

            for i, pw in enumerate(self.passwords, start=1):
                if self._cancelled:
                    break

                result = auth.login(self.username, pw)
                attempts_made = i

                event = AttemptEvent(
                    index=i,
                    password=pw,
                    outcome=result.outcome,
                    message=result.message,
                    guessed=result.success,
                    stopped=result.outcome in (Outcome.LOCKED, Outcome.LOCKED_NOW),
                )
                self.attempted.emit(event)

                if result.success:
                    guessed_password = pw
                    break

                if result.outcome in (Outcome.LOCKED, Outcome.LOCKED_NOW):
                    locked = True
                    break

                # Small visible pause between attempts.
                time.sleep(self.delay)
        finally:
            if conn is not None:
                conn.close()
            # Always emit a result, even on cancellation or error, so the
            # GUI never gets stuck waiting with its buttons disabled.
            self.finished_series.emit(
                {
                    "username": self.username,
                    "guessed_password": guessed_password,
                    "guessed": guessed_password is not None,
                    "locked": locked,
                    "cancelled": self._cancelled,
                    "attempts_made": attempts_made,
                }
            )
