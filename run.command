#!/bin/zsh
# NovaID launcher for macOS.
# Double-click this file in Finder, or run ./run.command in a terminal.
# It creates the virtual environment and installs dependencies on first run,
# then launches the app.

cd "$(dirname "$0")" || exit 1

if [ ! -d .venv ]; then
  echo "First run: creating virtual environment..."
  python3 -m venv .venv || { echo "Failed to create venv"; exit 1; }
fi

if ! .venv/bin/python -c "import PySide6" 2>/dev/null; then
  echo "Installing dependencies (one-time)..."
  .venv/bin/pip install --quiet --disable-pip-version-check -r requirements.txt \
    || { echo "Failed to install dependencies"; exit 1; }
fi

echo "Starting NovaID..."
exec .venv/bin/python main.py
