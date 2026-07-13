@echo off
setlocal
cd /d "%~dp0.."
if "%PORT%"=="" set PORT=8000
set UV_CACHE_DIR=%CD%\.uv-cache
if not exist ".venv\Scripts\uvicorn.exe" (
  uv sync --extra dev
)
".venv\Scripts\uvicorn.exe" app.main:app --host 127.0.0.1 --port %PORT%

