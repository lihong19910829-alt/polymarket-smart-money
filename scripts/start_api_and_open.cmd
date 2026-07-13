@echo off
cd /d "%~dp0.."
if "%PORT%"=="" set PORT=8000
start "" "http://127.0.0.1:%PORT%"
call "%CD%\scripts\start_api.cmd"

