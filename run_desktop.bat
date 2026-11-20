@echo off
title Noora AI - LAN AI Server (Developed by Nadeem)
cd /d "%~dp0"

echo ========================================================
echo   Launching Noora AI - LAN AI Server
echo   Engineered by Nadeem
echo   Optimized for Intel Core i5 and 4GB RAM
echo ========================================================

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" backend\main.py
) else (
    python backend\main.py
)

pause
