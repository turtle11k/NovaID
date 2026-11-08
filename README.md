# NovaID — Authentication Security Game

An offline teaching application built with **Python + PySide6** on the theme
of *authentication security*. It runs as a single window with two tabs that
play against each other:

- **🛡 Defender** — a fictional account service, *NovaID*, where you register
  users, sign in, and watch the protections (password-strength guidance,
  failed-attempt logging, and account lockout) work.
- **⚡ Tester** — a dark terminal screen that runs an automated series of
  logins against one account using a built-in list of common weak passwords,
  to show which passwords fall and how lockout stops the attack.

A scoreboard tracks how many accounts the Tester cracked versus how many the
Defender kept safe. Everything is **100% offline** — no network requests; all
data lives in a local SQLite file (`novaid.db`).

> This is an educational demonstration of defensive concepts (strong
> passwords, salted hashing, rate-limiting/lockout, audit logging). It only
> ever operates on its own local demo database.

---

## Requirements

- Python **3.9+** (tested on 3.14)
- PySide6 (installed via `requirements.txt`)
- Works on **macOS (Apple Silicon / M-series)** and **Windows**

## Install & run

### macOS (Apple Silicon and Intel)

```bash
cd NovaID
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Windows

```bat
cd NovaID
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

On first launch the app creates `novaid.db` and seeds three demo users:

| Username | Password              | Strength |
|----------|-----------------------|----------|
| `alice`  | `123456`              | weak (on the common list) |
| `bob`    | `Sunshine7`           | medium   |
| `carol`  | `Tr0ub4dour&3xplore!` | strong   |

Delete `novaid.db` if you ever want a completely fresh start.

---

## How to play

1. On **Defender**, register a few accounts and watch the strength bar as you
   type. Try signing in with a wrong password several times to trigger the
   warnings and the lockout, then unlock from the administrator panel.
2. On **Tester**, pick an account and press **run series**. Watch the log
   fill in line by line:
   - `alice` (weak) is cracked almost immediately.
   - `carol` (strong) is never guessed; instead the account **locks** after
     N wrong attempts and the series stops.
3. The scoreboard updates after each series. Press **New round** to clear all
   locks, the attempt log, and the score.

---

## Project structure

```
NovaID/
├── main.py                # entry point; seeds demo users, starts the app
├── database.py            # SQLite storage layer (tables, queries) — no GUI
├── auth.py                # all auth logic: hashing, login, lockout — no GUI
├── password_strength.py   # password strength evaluation — no GUI
├── test_runner.py         # QThread worker for the automated attempt series
├── gui/
│   ├── styles.py          # light "card" theme + dark terminal theme
│   ├── icons.py           # loads the PNG icon set from assets/
│   ├── scoreboard.py      # shared game state + scoreboard widget
│   ├── defender_tab.py    # registration, login, warnings, admin panel
│   ├── tester_tab.py      # terminal screen + live log
│   └── main_window.py     # tabs + scoreboard + "New round"
├── assets/                # PNG icons (fingerprint, terminal, padlock, node)
├── tools/
│   └── make_icons.py      # regenerates assets/*.png with QPainter (no deps)
├── requirements.txt
└── README.md
```

All security/logic lives in the non-GUI modules (`auth.py`, `database.py`,
`password_strength.py`, `test_runner.py`); the `gui/` package only draws them.

---

## How each requirement is met

### Tab 1 — Defender (NovaID account service)

1. **Registration (username + password)** — `DefenderTab._on_register` →
   `AuthService.register` (`auth.py`).
2. **Live strength indicator** — `password_strength.evaluate` scores length,
   digits, uppercase, special characters, and checks a list of too-common
   passwords, returning *weak / medium / strong*. The bar, verdict label and
   checklist update on every keystroke (`DefenderTab._on_password_typed`).
3. **Salted hashes only** — `auth._derive_key` uses `hashlib.scrypt` with a
   per-user random salt (`os.urandom`). Only the derived key + salt are
   stored (`database.insert_user`). The plain password is never written
   anywhere.
4. **Login by hash check** — `AuthService.verify_password` re-derives the key
   and compares it with **`hmac.compare_digest`** (constant-time).
5. **Failed-attempt logging** — every attempt is written to the `attempts`
   table with a timestamp (`database.log_attempt`), shown in the admin log.
6. **Lockout after N wrong attempts** — N is configurable **3–5, default 3**
   (the spin box in the login card; `AuthService.set_threshold`). After N
   consecutive misses the account is locked and is refused **even with the
   correct password** (`AuthService.login`, `Outcome.LOCKED`).
7. **Suspicious-activity warnings** — coloured banners and pop-ups for
   "N attempts left", "account locked", and "login to a locked account"
   (`DefenderTab._react_to_login`).
8. **Administrator panel** — a table of users with status (active/locked),
   failed count, last-failure time, the full failed-attempt log, and an
   **Unlock** button (`DefenderTab._build_admin_card`, `refresh_admin`).

Design: light, minimalist "card" style — pale background, generous spacing,
rounded fields/buttons, soft borders, system font, no real brand names
(`gui/styles.DEFENDER_STYLE`).

### Tab 2 — Tester (password resilience)

1. **Pick an account** from the local database (`TesterTab.account_combo`).
2. **Automated series** — `TestWorker` tries ~50 common weak passwords in
   turn through the **same `AuthService.login`** used by Tab 1, with a small
   delay so each step is visible.
3. **Real-time log** — attempt number, password tried, result, time and the
   system's reaction (`TesterTab._on_attempt`).
4. **Clear outcome** — a weak password is guessed from the list, a strong one
   is not, and the lockout stops the series after N misses
   (`TesterTab._on_finished`).

Design: dark terminal theme — black background, green monospace font, the log
scrolls line by line (`gui/styles.TESTER_STYLE`).

### Game part

- **Scoreboard** — Tester points (accounts cracked) vs Defender points
  (accounts that held) in `gui/scoreboard.py`.
- **Per-round summary** — one plain-language line after each series naming
  the measure that worked (strong password / lockout) or why the password
  fell (`GameState.record_result`).
- **New round** — resets locks, the attempt log and the score
  (`MainWindow._on_new_round` → `AuthService.new_round`).

### Technical

- The series runs in a **`QThread`** (`test_runner.TestWorker`) so the UI
  never freezes. Because SQLite connections are thread-bound, the worker
  opens **its own** connection to the same database file; the result is always
  emitted (even on cancel/error) so the UI never gets stuck.
- Structure matches the brief: `database.py`, `auth.py`,
  `password_strength.py`, `test_runner.py`, `gui/`, `main.py`,
  `requirements.txt`, `README.md`.

---

## A note on the "strong password" outcome

With the lockout threshold at 3–5 and ~50 passwords in the list, a strong
account always **locks** before the list is exhausted — so the usual result
for a strong password is *"locked — series stopped (defence held)"* rather
than *"exhausted the list"*. That is the realistic lesson: **rate-limiting /
lockout is what actually stops an online guessing attack**, no matter how long
the wordlist is. The "resisted the whole list" message exists for the case
where lockout is disabled or the list is shorter than the threshold.
