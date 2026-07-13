@echo off
cd /d "%~dp0.."
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" scripts\generate_live_snapshot.py
) else (
  python scripts\generate_live_snapshot.py
)
start "" "%CD%\live-dashboard-snapshot.html"
