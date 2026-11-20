@echo off
title Noora AI Server (Headless LAN Mode)
cd /d "%~dp0"

echo ========================================================
echo   Launching Noora AI Server in Headless LAN Mode
echo   Engineered by Nadeem
echo ========================================================

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" backend\main.py --headless
) else (
    python backend\main.py --headless
)

pause
