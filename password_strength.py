"""
password_strength.py
---------------------
Password strength evaluation for the NovaID defender tab.

Pure logic, no GUI. The evaluator scores a password against several
criteria (length, digits, uppercase letters, special characters) and
checks it against a built-in list of passwords that are too common to
ever be considered safe. It returns a simple verdict used by the UI:

    "weak" / "medium" / "strong"

along with a numeric score and human-readable feedback so the interface
can show a coloured bar and a checklist.
"""

from __future__ import annotations

import string
from dataclasses import dataclass, field
from typing import List

# A short embedded list of passwords that are far too common to allow.
# This is intentionally small and overlaps with the teaching list used by
# the tester tab. Any password appearing here is forced to "weak".
COMMON_PASSWORDS = {
    "123456", "123456789", "12345678", "12345", "1234567", "password",
    "qwerty", "abc123", "111111", "123123", "admin", "letmein",
    "welcome", "monkey", "dragon", "iloveyou", "sunshine", "princess",
    "football", "000000", "qwerty123", "1q2w3e4r", "password1",
    "qwertyuiop", "superman", "trustno1", "login", "passw0rd",
}

# Verdict labels (kept as constants so the GUI and tests agree on spelling).
WEAK = "weak"
MEDIUM = "medium"
STRONG = "strong"


@dataclass
class StrengthResult:
    """Outcome of evaluating a single password."""

    verdict: str                       # WEAK / MEDIUM / STRONG
    score: int                         # 0..5, how many checks passed
    is_common: bool                    # True if found in COMMON_PASSWORDS
    checks: dict = field(default_factory=dict)   # named check -> bool
    feedback: List[str] = field(default_factory=list)  # advice lines

    @property
    def ratio(self) -> float:
        """Score as a 0.0..1.0 fraction, handy for progress bars."""
        return self.score / 5.0


def _has_special(password: str) -> bool:
    special = set(string.punctuation)
    return any(ch in special for ch in password)


def evaluate(password: str) -> StrengthResult:
    """Evaluate *password* and return a StrengthResult.

    Scoring criteria (one point each):
      1. length >= 8
      2. length >= 12 (an extra point for longer passwords)
      3. contains at least one digit
      4. contains at least one uppercase letter
      5. contains at least one special character

    A password found in COMMON_PASSWORDS is always reported as WEAK,
    regardless of how many criteria it meets.
    """
    checks = {
        "length8": len(password) >= 8,
        "length12": len(password) >= 12,
        "digit": any(ch.isdigit() for ch in password),
        "upper": any(ch.isupper() for ch in password),
        "special": _has_special(password),
    }
    score = sum(1 for passed in checks.values() if passed)
    is_common = password.lower() in COMMON_PASSWORDS

    feedback: List[str] = []
    if not checks["length8"]:
        feedback.append("Use at least 8 characters.")
    if not checks["digit"]:
        feedback.append("Add at least one digit (0-9).")
    if not checks["upper"]:
        feedback.append("Add at least one uppercase letter.")
    if not checks["special"]:
        feedback.append("Add a special character (e.g. ! ? # $).")
    if checks["length8"] and not checks["length12"]:
        feedback.append("12+ characters would be even stronger.")

    if is_common:
        verdict = WEAK
        feedback.insert(0, "This password is on the list of common passwords.")
    elif score <= 2:
        verdict = WEAK
    elif score <= 3:
        verdict = MEDIUM
    else:
        verdict = STRONG

    if verdict == STRONG and not feedback:
        feedback.append("Great — this password meets all the criteria.")

    return StrengthResult(
        verdict=verdict,
        score=score,
        is_common=is_common,
        checks=checks,
        feedback=feedback,
    )


if __name__ == "__main__":
    # Tiny manual check when run directly.
    for pw in ["123456", "Sunshine1", "Tr0ub4dour&3xplore!"]:
        r = evaluate(pw)
        print(f"{pw!r:28} -> {r.verdict:7} (score {r.score}/5)")
