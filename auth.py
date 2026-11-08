"""
auth.py
-------
All authentication logic for NovaID, with no GUI dependencies.

Security properties demonstrated here:
  * Passwords are never stored in plain text. We store only a salted
    key derived with hashlib.scrypt (a slow, memory-hard KDF), together
    with the per-user random salt.
  * Verification uses hmac.compare_digest for a constant-time comparison,
    so timing does not leak how many bytes matched.
  * Each failed login is written to an audit log with a timestamp.
  * After N consecutive failed attempts (configurable, 3..5, default 3)
    the account is locked. A locked account is refused *even if the
    correct password is supplied*, until an administrator unlocks it.

The module exposes a small AuthService class that wraps a database
connection, plus an AuthResult describing the outcome of each attempt so
the GUI can show the right banner or warning.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import database as db

# Key-derivation parameters for scrypt. These are reasonable for a desktop
# demo: strong enough to be meaningful, fast enough to stay responsive.
ALGO_LABEL = "scrypt"
SCRYPT_N = 2 ** 14      # CPU/memory cost
SCRYPT_R = 8            # block size
SCRYPT_P = 1            # parallelisation
DK_LEN = 32            # derived key length in bytes
SALT_LEN = 16          # salt length in bytes

# Lockout threshold bounds (requirement: configurable 3..5, default 3).
MIN_THRESHOLD = 3
MAX_THRESHOLD = 5
DEFAULT_THRESHOLD = 3


class Outcome(str, Enum):
    """Machine-readable result of a login attempt."""

    SUCCESS = "success"
    WRONG_PASSWORD = "wrong_password"
    NO_SUCH_USER = "no_such_user"
    LOCKED = "locked"              # attempt made against an already-locked account
    LOCKED_NOW = "locked_now"      # this attempt caused the lock to engage


@dataclass
class AuthResult:
    """Describes a single login attempt and the system's reaction."""

    outcome: Outcome
    username: str
    failed_count: int = 0
    attempts_remaining: int = 0
    message: str = ""

    @property
    def success(self) -> bool:
        return self.outcome is Outcome.SUCCESS


def _derive_key(password: str, salt: bytes) -> bytes:
    """Derive a key from *password* and *salt* using scrypt."""
    return hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=DK_LEN,
    )


class AuthService:
    """Authentication operations on top of a SQLite connection."""

    def __init__(self, conn, lockout_threshold: int = DEFAULT_THRESHOLD,
                 db_path: str = db.DEFAULT_DB_PATH):
        self.conn = conn
        # Remembered so a background thread can open its *own* connection to
        # the same database file (SQLite connections are not shareable
        # across threads).
        self.db_path = db_path
        self.set_threshold(lockout_threshold)

    def set_threshold(self, value: int) -> None:
        """Clamp and store the lockout threshold (3..5)."""
        self.lockout_threshold = max(MIN_THRESHOLD, min(MAX_THRESHOLD, int(value)))

    # --- registration ------------------------------------------------------

    def register(self, username: str, password: str) -> None:
        """Create a new user. Raises ValueError if the name is taken/empty."""
        username = username.strip()
        if not username:
            raise ValueError("Username must not be empty.")
        if not password:
            raise ValueError("Password must not be empty.")
        if db.get_user(self.conn, username) is not None:
            raise ValueError(f"User '{username}' already exists.")

        salt = os.urandom(SALT_LEN)
        pwd_hash = _derive_key(password, salt)
        db.insert_user(self.conn, username, pwd_hash, salt, ALGO_LABEL)

    # --- login -------------------------------------------------------------

    def verify_password(self, user_row, password: str) -> bool:
        """Constant-time check of *password* against a stored user row."""
        candidate = _derive_key(password, bytes(user_row["salt"]))
        return hmac.compare_digest(candidate, bytes(user_row["pwd_hash"]))

    def login(self, username: str, password: str) -> AuthResult:
        """Attempt a login and apply the lockout policy.

        This is the single entry point used by *both* tabs: the defender's
        login form and the tester's automated series call this exact method,
        so the demonstrated behaviour is identical.
        """
        user = db.get_user(self.conn, username)

        # Unknown user: log and report, nothing to lock.
        if user is None:
            db.log_attempt(self.conn, username, False, Outcome.NO_SUCH_USER.value)
            return AuthResult(
                outcome=Outcome.NO_SUCH_USER,
                username=username,
                message=f"No account named '{username}'.",
            )

        # Already locked: refuse before even checking the password.
        if user["is_locked"]:
            db.log_attempt(self.conn, username, False, Outcome.LOCKED.value)
            return AuthResult(
                outcome=Outcome.LOCKED,
                username=username,
                failed_count=user["failed_count"],
                attempts_remaining=0,
                message="Account is locked. An administrator must unlock it.",
            )

        # Correct password on an unlocked account: success, reset counter.
        if self.verify_password(user, password):
            db.update_user_security(self.conn, username, 0, False, None)
            db.log_attempt(self.conn, username, True, Outcome.SUCCESS.value)
            return AuthResult(
                outcome=Outcome.SUCCESS,
                username=username,
                failed_count=0,
                attempts_remaining=self.lockout_threshold,
                message="Signed in.",
            )

        # Wrong password: increment the counter and maybe lock.
        failed_count = user["failed_count"] + 1
        timestamp = db.now_iso()
        locked_now = failed_count >= self.lockout_threshold

        db.update_user_security(
            self.conn, username, failed_count, locked_now, timestamp
        )
        reason = Outcome.LOCKED_NOW.value if locked_now else Outcome.WRONG_PASSWORD.value
        db.log_attempt(self.conn, username, False, reason)

        remaining = max(0, self.lockout_threshold - failed_count)
        if locked_now:
            return AuthResult(
                outcome=Outcome.LOCKED_NOW,
                username=username,
                failed_count=failed_count,
                attempts_remaining=0,
                message=(
                    f"Too many wrong attempts — account '{username}' is now locked."
                ),
            )
        return AuthResult(
            outcome=Outcome.WRONG_PASSWORD,
            username=username,
            failed_count=failed_count,
            attempts_remaining=remaining,
            message=f"Wrong password. {remaining} attempt(s) left before lockout.",
        )

    # --- admin helpers -----------------------------------------------------

    def unlock(self, username: str) -> None:
        db.unlock_user(self.conn, username)

    def new_round(self) -> None:
        """Reset locks, counters and the attempt log for a fresh round."""
        db.reset_all_security(self.conn)
