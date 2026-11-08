@echo off
REM NovaID launcher for Windows.
REM Double-click this file, or run run.bat in a terminal.
REM It creates the virtual environment and installs dependencies on first
REM run, then launches the app.

cd /d "%~dp0"

if not exist ".venv\" (
  echo First run: creating virtual environment...
  py -m venv .venv 2>nul || python -m venv .venv || goto :error
)

".venv\Scripts\python.exe" -c "import PySide6" 2>nul
if errorlevel 1 (
  echo Installing dependencies ^(one-time^)...
  ".venv\Scripts\pip.exe" install --quiet --disable-pip-version-check -r requirements.txt || goto :error
)

echo Starting NovaID...
".venv\Scripts\python.exe" main.py
goto :eof

:error
echo.
echo Failed to set up or launch NovaID.
pause
