@echo off
setlocal enabledelayedexpansion
title Noora AI LAN Server - Setup & Installation Wizard
cd /d "%~dp0"

echo ======================================================================
echo   NOORA AI LAN SERVER - SETUP WIZARD
echo   Developed by Nadeem
echo   Target: Windows 10/11 (Intel Core i5, 4GB RAM)
echo ======================================================================
echo.

:: 1. Check Python
echo [*] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Python 3.10+ is required but was not found in PATH.
    echo     Please install Python 3.10 or newer from python.org and ensure
    echo     "Add Python to PATH" is checked during installation.
    pause
    exit /b 1
)
python --version
echo [+] Python detected.
echo.

:: 2. Setup Virtual Environment
if not exist ".venv\Scripts\python.exe" (
    echo [*] Creating isolated Python virtual environment (.venv)...
    python -m venv .venv
    echo [+] Virtual environment initialized.
) else (
    echo [+] Virtual environment already exists.
)
echo.

:: 3. Install Backend Dependencies
echo [*] Installing required runtime packages...
".venv\Scripts\python.exe" -m pip install -q --upgrade pip
".venv\Scripts\python.exe" -m pip install -q fastapi uvicorn psutil httpx pydantic pywebview
echo [+] Backend dependencies installed.
echo.

:: 4. Verify AI Engine and Model
if not exist "engine\llama-server.exe" (
    echo [*] llama-server.exe missing. Downloading official CPU inference engine...
    ".venv\Scripts\python.exe" -c "
import urllib.request, zipfile, io, os
url = 'https://github.com/ggerganov/llama.cpp/releases/download/b12499/llama-b12499-bin-win-cpu-x64.zip'
print('Downloading official llama.cpp CPU engine...')
os.makedirs('engine', exist_ok=True)
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as resp:
    data = resp.read()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        z.extractall('engine')
print('Engine installed successfully!')
"
) else (
    echo [+] llama-server.exe CPU engine verified.
)

if not exist "models\qwen2.5-0.5b-instruct-q4_k_m.gguf" (
    echo [*] Default model not found. Starting initial model download...
    ".venv\Scripts\python.exe" -c "
import urllib.request, os
os.makedirs('models', exist_ok=True)
url = 'https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf'
dest = 'models/qwen2.5-0.5b-instruct-q4_k_m.gguf'
print('Downloading Qwen2.5-0.5B GGUF model...')
urllib.request.urlretrieve(url, dest)
print('Model downloaded successfully!')
"
) else (
    echo [+] Default GGUF AI model ready (qwen2.5-0.5b-instruct-q4_k_m.gguf).
)
echo.

:: 5. Windows Firewall Setup (Optional)
echo [*] Setting up Windows Firewall rule for LAN access (Port 8080)...
netsh advfirewall firewall show rule name="Noora LAN AI Server" >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] Creating inbound firewall rule for TCP port 8080 (private network)...
    netsh advfirewall firewall add rule name="Noora LAN AI Server" dir=in action=allow protocol=TCP localport=8080 profile=private >nul 2>&1
    if %errorlevel% equ 0 (
        echo [+] Firewall rule created successfully.
    ) else (
        echo [i] Note: Run setup as Administrator to automatically add the firewall rule,
        echo     or manage it anytime from the desktop Settings tab.
    )
) else (
    echo [+] Inbound firewall rule already configured.
)
echo.

echo ======================================================================
echo   INSTALLATION COMPLETE!
echo.
echo   You can now launch the application by running:
echo   - run_desktop.bat   (Opens the modern desktop GUI)
echo   - run_headless.bat  (Runs the background server)
echo ======================================================================
echo.
pause
