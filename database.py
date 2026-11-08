"""
database.py
-----------
SQLite storage layer for the NovaID demo. No GUI, no auth logic here —
just tables, connections and small helpers. Everything lives in one
local file; the application makes no network requests.

Tables
======
users
    id                INTEGER PRIMARY KEY
    username          TEXT UNIQUE
    pwd_hash          BLOB     -- derived key (never the plain password)
    salt              BLOB     -- per-user random salt
    algo              TEXT     -- key-derivation algorithm label
    failed_count      INTEGER  -- consecutive failed attempts
    is_locked         INTEGER  -- 0 / 1
    last_failed_at    TEXT     -- ISO timestamp of last failed attempt
    created_at        TEXT

attempts
    id                INTEGER PRIMARY KEY
    username          TEXT     -- the username that was tried
    success           INTEGER  -- 0 / 1
    reason            TEXT     -- short machine/readable reason
    created_at        TEXT     -- ISO timestamp
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Optional

# Default database file sits next to this module.
DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "novaid.db")


def now_iso() -> str:
    """Current local time as an ISO-8601 string (second precision)."""
    return datetime.now().isoformat(timespec="seconds")


def connect(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Open a connection with row access by column name."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    # Wait instead of failing immediately if another connection (e.g. the
    # tester thread, which opens its own connection to the same file) holds
    # a brief write lock.
    conn.execute("PRAGMA busy_timeout = 5000;")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Create tables if they do not yet exist."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            username       TEXT UNIQUE NOT NULL,
            pwd_hash       BLOB NOT NULL,
            salt           BLOB NOT NULL,
            algo           TEXT NOT NULL,
            failed_count   INTEGER NOT NULL DEFAULT 0,
            is_locked      INTEGER NOT NULL DEFAULT 0,
            last_failed_at TEXT,
            created_at     TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS attempts (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            username   TEXT NOT NULL,
            success    INTEGER NOT NULL,
            reason     TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )
    conn.commit()


# --- user helpers ----------------------------------------------------------

def get_user(conn: sqlite3.Connection, username: str) -> Optional[sqlite3.Row]:
    cur = conn.execute("SELECT * FROM users WHERE username = ?", (username,))
    return cur.fetchone()


def list_users(conn: sqlite3.Connection):
    cur = conn.execute("SELECT * FROM users ORDER BY username COLLATE NOCASE")
    return cur.fetchall()


def insert_user(
    conn: sqlite3.Connection,
    username: str,
    pwd_hash: bytes,
    salt: bytes,
    algo: str,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO users (username, pwd_hash, salt, algo, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (username, pwd_hash, salt, algo, now_iso()),
    )
    conn.commit()
    return cur.lastrowid


def update_user_security(
    conn: sqlite3.Connection,
    username: str,
    failed_count: int,
    is_locked: bool,
    last_failed_at: Optional[str],
) -> None:
    conn.execute(
        """
        UPDATE users
        SET failed_count = ?, is_locked = ?, last_failed_at = ?
        WHERE username = ?
        """,
        (failed_count, 1 if is_locked else 0, last_failed_at, username),
    )
    conn.commit()


def unlock_user(conn: sqlite3.Connection, username: str) -> None:
    """Clear the lock and reset the failed counter for one user."""
    conn.execute(
        """
        UPDATE users
        SET failed_count = 0, is_locked = 0, last_failed_at = NULL
        WHERE username = ?
        """,
        (username,),
    )
    conn.commit()


def reset_all_security(conn: sqlite3.Connection) -> None:
    """Unlock every account and clear the attempt log (new round)."""
    conn.execute(
        "UPDATE users SET failed_count = 0, is_locked = 0, last_failed_at = NULL"
    )
    conn.execute("DELETE FROM attempts")
    conn.commit()


# --- attempt log helpers ---------------------------------------------------

def log_attempt(
    conn: sqlite3.Connection,
    username: str,
    success: bool,
    reason: str,
) -> None:
    conn.execute(
        """
        INSERT INTO attempts (username, success, reason, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (username, 1 if success else 0, reason, now_iso()),
    )
    conn.commit()


def get_failed_attempts(conn: sqlite3.Connection, username: Optional[str] = None):
    """Return failed attempts, newest first; optionally for one user."""
    if username is None:
        cur = conn.execute(
            "SELECT * FROM attempts WHERE success = 0 ORDER BY id DESC"
        )
    else:
        cur = conn.execute(
            "SELECT * FROM attempts WHERE success = 0 AND username = ? ORDER BY id DESC",
            (username,),
        )
    return cur.fetchall()
