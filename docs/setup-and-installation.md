# Noora AI — Installation & Setup Guide

**Author:** Nadeem  
**Application:** Noora AI LAN Server (v1.0.0)  
**Target Architecture:** Windows 10/11 x64, Intel Core i5 CPU, 4GB+ RAM  

---

## 📋 System Requirements

Before installing, ensure your machine meets the minimum hardware and software prerequisites:

- **Operating System:** Windows 10 (64-bit) or Windows 11 (64-bit)
- **Processor (CPU):** Intel Core i5 (6th gen or newer) or AMD Ryzen 3/5 with AVX2 instruction support
- **Memory (RAM):** 4 GB minimum (1.5 GB free for model execution)
- **Storage:** 2.5 GB free disk space (for backend, engine, and GGUF model files)
- **Network:** Connected to a local Wi-Fi or Ethernet LAN router
- **Software Dependencies:** Python 3.10, 3.11, 3.12, or 3.13 installed with **"Add Python to PATH"** enabled. (Node.js 18+ is only needed if you want to modify and recompile the frontend).

---

## 🚀 Installation Methods

You can set up Noora AI using three different methods:

### Method 1: Automated 1-Click Wizard (Recommended for Most Users)

The automated batch installer checks Python, initializes an isolated virtual environment, installs Python packages, downloads the AVX2 CPU engine if missing, and configures the default model.

1. Open PowerShell or Command Prompt in the project folder.
2. Run:
```cmd
Nila-LAN-AI-Setup.bat
```
3. Once completed, launch the desktop application:
```cmd
run_desktop.bat
```

---

### Method 2: Manual Terminal Setup (Step-by-Step)

If you prefer full control over each component or are running in a custom developer environment, follow these exact terminal commands:

#### Step 1: Clone the Repository
```powershell
git clone https://github.com/nadeemmhdm/Noora-LAN-AI-Server.git
cd Noora-LAN-AI-Server
```

#### Step 2: Create a Python Virtual Environment
```powershell
# Create an isolated virtual environment in .venv
python -m venv .venv

# Activate the virtual environment
# In Windows PowerShell:
.\.venv\Scripts\Activate.ps1

# Or in Windows Command Prompt (CMD):
.\.venv\Scripts\activate.bat
```

#### Step 3: Upgrade Pip & Install Backend Requirements
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

> **Note:** The core dependencies in `requirements.txt` are:
> - `fastapi>=0.115.0` (OpenAI-compatible REST API gateway)
> - `uvicorn>=0.30.0` (High-performance ASGI server)
> - `psutil>=5.9.0` (Hardware auto-detection: CPU cores, RAM telemetry)
> - `httpx>=0.27.0` (Async streaming reverse proxy to llama-server)
> - `pydantic>=2.8.0` (Data validation and schemas)
> - `pywebview>=5.0.0` (Native Windows Edge WebView2 desktop container)

#### Step 4: (Optional) Build the Frontend Distribution
The repository comes pre-packaged with compiled frontend assets in `frontend/dist/`. If you want to modify the React frontend:
```powershell
cd frontend
npm install
npm run build
cd ..
```

#### Step 5: Verify llama.cpp CPU Engine
Ensure `engine/llama-server.exe` exists. If you need to manually download the official AVX2 CPU engine:
```powershell
python -c "
import urllib.request, zipfile, io, os
os.makedirs('engine', exist_ok=True)
url = 'https://github.com/ggerganov/llama.cpp/releases/download/b12499/llama-b12499-bin-win-cpu-x64.zip'
print('Downloading official llama.cpp CPU binary...')
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as resp:
    data = resp.read()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        z.extractall('engine')
print('Engine installed successfully to engine/llama-server.exe!')
"
```

#### Step 6: Download or Place GGUF Models
Place your GGUF models inside the `models/` directory. To download the ultra-fast default **Noora N.1 Faster** model (~491 MB):
```powershell
python -c "
import urllib.request, os
os.makedirs('models', exist_ok=True)
url = 'https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf'
dest = 'models/qwen2.5-0.5b-instruct-q4_k_m.gguf'
print('Downloading Noora N.1 Faster GGUF model...')
urllib.request.urlretrieve(url, dest)
print('Model downloaded to ' + dest)
"
```

#### Step 7: Configure Windows Firewall Rule
Allow incoming connections on port `8080` from devices on your local Wi-Fi. Run PowerShell as **Administrator**:
```powershell
netsh advfirewall firewall add rule name="Noora LAN AI Server" dir=in action=allow protocol=TCP localport=8080 profile=private
```

---

### Method 3: Portable ZIP Distribution (Zero Installation)

For machines without Python pre-installed:
1. Download `Nila-LAN-AI-Portable.zip` from [GitHub Releases](https://github.com/nadeemmhdm/Noora-LAN-AI-Server/releases/latest).
2. Extract the ZIP file to any folder (e.g. `C:\Noora-AI`).
3. Double-click `run_desktop.bat`.

---

## 🖥️ Running the Server

### 1. Launch with Native Desktop GUI
```powershell
.\.venv\Scripts\python.exe backend\main.py
```
Or simply double-click `run_desktop.bat`. This launches the native Windows Edge WebView2 window with real-time CPU & RAM gauges, API key management, and the interactive chat playground.

### 2. Launch in Headless Server Mode (Console Only)
To run in the background or on a dedicated home server without opening a GUI window:
```powershell
.\.venv\Scripts\python.exe backend\main.py --headless
```
Or double-click `run_headless.bat`.

### 3. Custom Host & Port Parameters
```powershell
# Custom port and interface
.\.venv\Scripts\python.exe backend\main.py --host 0.0.0.0 --port 9000 --headless
```

---

## 🔍 Verification & Testing Commands

Once started, test that the server and inference engine are healthy and reachable:

### 1. Check in Web Browser
Open:
```text
http://localhost:8080/v1
```
Or from another device on the same Wi-Fi (e.g., your smartphone):
```text
http://<YOUR_LAPTOP_IP>:8080/v1
```
You will see the **Noora AI LAN Server Status Console**, active working API key, and an in-browser prompt tester.

---

### 2. Test via cURL (Linux / macOS / Git Bash / CMD)
```bash
curl -X POST "http://localhost:8080/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-local-noora-default-lan-key" \
  -d '{
    "model": "N.1 Faster",
    "messages": [
      {"role": "user", "content": "Introduce yourself in one sentence."}
    ],
    "max_tokens": 50
  }'
```

---

### 3. Test via Python (OpenAI SDK)
```python
from openai import OpenAI

# Connect to Noora AI running on your laptop
client = OpenAI(
    base_url="http://localhost:8080/v1",  # Or use LAN IP: http://192.168.x.x:8080/v1
    api_key="sk-local-noora-default-lan-key"
)

response = client.chat.completions.create(
    model="N.1 Faster",
    messages=[
        {"role": "user", "content": "Who developed you and what can you do?"}
    ]
)

print(response.choices[0].message.content)
```

---

### 4. Test via Windows PowerShell
```powershell
$headers = @{
    "Content-Type"  = "application/json"
    "Authorization" = "Bearer sk-local-noora-default-lan-key"
}
$body = @{
    model    = "N.1 Faster"
    messages = @(
        @{ role = "user"; content = "Hello Noora!" }
    )
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8080/v1/chat/completions" -Method POST -Headers $headers -Body $body
$response.choices[0].message.content
```

---

## 🌐 Real-Time Web Search Integration (Online Mode Only)

Noora AI includes built-in live web search capability requiring **zero external API keys** or paid search service subscriptions:

- **When Online (Host has internet connectivity):** Noora automatically detects questions requesting recent events, current versions, or news, performs live web queries via organic web scrapers and encyclopedic APIs, and enriches its response with clickable citation sources.
- **When Offline (No internet or air-gapped Wi-Fi):** Noora detects that internet is unreachable within milliseconds via lightweight socket checks and transparently falls back to 100% offline local neural inference. No timeouts, no crashes, and zero network errors.
- **Manual Control:** You can explicitly force or disable web search per request by passing `"web_search": true` or `"web_search": false` in the `/v1/chat/completions` JSON body, or toggle it in the Web Playground.

---

## 🛠️ Troubleshooting Setup Issues

| Problem | Cause | Solution |
| :--- | :--- | :--- |
| **`python` command not recognized** | Python was installed without checking "Add to PATH" | Re-run Python installer, choose "Modify", and check "Add Python to environment variables". |
| **Port 8080 already in use** | Another service (e.g. Apache, Tomcat, or old server instance) is bound to port 8080 | Pass `--port 8090` to `main.py` or stop the conflicting application. |
| **Wi-Fi devices cannot connect** | Windows Defender Firewall is blocking inbound connections | Run the PowerShell firewall command as Administrator or use the "Add Rule" button in the Settings tab. |
| **Model failed to load (Out of Memory)** | Free system RAM is lower than 450 MB | Close background browser tabs or switch to the lightweight `N.1 Faster` model (491 MB). |
| **HTTP 401 Unauthorized** | Invalid or missing API Key | Pass the active working API key shown on `http://<LAN_IP>:8080/v1` in `Authorization: Bearer <KEY>`. |
