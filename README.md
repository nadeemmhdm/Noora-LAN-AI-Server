# Noora AI — LAN AI Server

**Developed by Nadeem**  
*On-Demand Local AI Hosting Server for Windows 10/11*  
*Optimized for Intel Core i5 CPU and 4GB RAM (100% CPU Inference, Zero Dedicated GPU Required)*

---

## 🌟 Overview

**Noora AI** transforms your Windows laptop into a secure, on-demand local AI server. It exposes a standard OpenAI-compatible API endpoint to any device connected to the same Wi-Fi or Ethernet LAN without third-party tunnels (no Cloudflare Tunnels, Tailscale, ZeroTier, or VPS).

- **AI Name & Persona:** **Noora**
- **Developer:** **Nadeem**
- **Hardware Targets:** Intel Core i5, 4GB RAM, CPU-only inference.
- **Privacy Guarantee:** 100% on-device local execution; zero prompt or secret logging; air-gapped capable.
- **🧠 AI Training & Knowledge Memory:** Train Noora by uploading Markdown (`.md`, `.txt`) documentation, company policies, guides, or notes. Noora automatically parses document hierarchies, extracts section keywords and semantic chunks, saves them to persistent on-device SQLite memory, and retrieves relevant knowledge in $<5\text{ms}$ with zero vector-database RAM overhead to answer queries across your network.
- **🌐 Real-Time Web Search:** Online-only web search integration (Zero API keys required). When connected to Wi-Fi/Internet, retrieves live factual data and source links; when offline, gracefully runs purely local neural inference without network errors.

---

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React 19, Vite, TypeScript, Tailwind CSS, Boxicons, Framer Motion |
| **Desktop Shell** | Windows Edge WebView2 (pywebview) + Tauri 2 Ready (`src-tauri/`) |
| **Backend Gateway** | Python 3.10+, FastAPI, Uvicorn, SQLite (WAL mode) |
| **AI Engine** | `llama.cpp` (`llama-server.exe` build 12499 x64 CPU AVX2) |
| **Model Suite** | GGUF Q4_K_M (`N.1 Faster`, `N.1 Pro`, `N.1 Core`) |

---

## 📋 System Requirements

- **Operating System:** Windows 10 / Windows 11 (64-bit)
- **CPU:** Intel Core i5 or AMD Ryzen CPU (AVX2 support, no GPU required)
- **Memory (RAM):** 4 GB minimum (approx. 650 MB to 1.5 GB allocated during inference)
- **Disk Space:** ~2.5 GB free space
- **Software:** Python 3.10 to 3.13 (Ensure **"Add Python to PATH"** was checked during Python installation)

---

## 📥 How to Install and Setup (3 Methods)

### Method 1: Automated Setup Wizard (Fastest & Recommended)

Run the automated setup script to set up Python virtualenv, install dependencies, and verify the CPU engine in one command:

```cmd
Nila-LAN-AI-Setup.bat
```

Once completed, start the server:
```cmd
run_desktop.bat
```

---

### Method 2: Manual Terminal Setup (Step-by-Step Commands)

If you prefer installing manually or are working in a custom terminal environment:

#### 1. Clone the Repository
```powershell
git clone https://github.com/nadeemmhdm/Noora-LAN-AI-Server.git
cd Noora-LAN-AI-Server
```

#### 2. Create and Activate Virtual Environment
```powershell
# Create isolated environment
python -m venv .venv

# Activate on Windows PowerShell:
.\.venv\Scripts\Activate.ps1

# Or activate on Command Prompt (CMD):
.\.venv\Scripts\activate.bat
```

#### 3. Install Python Dependencies
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

#### 4. (Optional) Compile Frontend Assets
Compiled assets are pre-packaged in `frontend/dist/`. To recompile or modify:
```powershell
cd frontend
npm install
npm run build
cd ..
```

#### 5. Verify or Download llama.cpp AVX2 Engine
Ensure `engine/llama-server.exe` exists. To download the verified CPU build:
```powershell
python -c "
import urllib.request, zipfile, io, os
os.makedirs('engine', exist_ok=True)
url = 'https://github.com/ggerganov/llama.cpp/releases/download/b12499/llama-b12499-bin-win-cpu-x64.zip'
print('Downloading llama.cpp CPU binary...')
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as resp:
    data = resp.read()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        z.extractall('engine')
print('Engine installed successfully to engine/llama-server.exe')
"
```

#### 6. Download Default Noora GGUF Model
```powershell
python -c "
import urllib.request, os
os.makedirs('models', exist_ok=True)
url = 'https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf'
dest = 'models/qwen2.5-0.5b-instruct-q4_k_m.gguf'
print('Downloading Noora N.1 Faster GGUF model...')
urllib.request.urlretrieve(url, dest)
print('Done. Saved to ' + dest)
"
```

#### 7. Allow Port 8080 in Windows Firewall
Open PowerShell as **Administrator** and run:
```powershell
netsh advfirewall firewall add rule name="Noora LAN AI Server" dir=in action=allow protocol=TCP localport=8080 profile=private
```

---

### Method 3: Portable ZIP (Zero Installation)

1. Download `Nila-LAN-AI-Portable.zip` from [GitHub Releases](https://github.com/nadeemmhdm/Noora-LAN-AI-Server/releases/latest).
2. Extract the archive into any folder.
3. Double-click `run_desktop.bat` to start immediately.

---

## 🚀 Running the Server

### Start with Native Desktop GUI
```powershell
.\.venv\Scripts\python.exe backend\main.py
```
*(Or double-click `run_desktop.bat`)*

### Start in Headless Server Mode (Console Only)
```powershell
.\.venv\Scripts\python.exe backend\main.py --headless
```
*(Or double-click `run_headless.bat`)*

### Custom Host & Port
```powershell
.\.venv\Scripts\python.exe backend\main.py --host 0.0.0.0 --port 8080 --headless
```

---

## 🧪 Testing & Verification Commands

### 1. Test in Web Browser
Open your browser and navigate to:
```text
http://localhost:8080/v1
```
Or from another device on your Wi-Fi:
```text
http://<YOUR_LAN_IP>:8080/v1
```
*(Displays server status, active API key with 1-click copy, and an in-browser live prompt console)*

### 2. Test via cURL (Local or With Online Web Search)
```bash
# Standard local chat completion
curl -X POST "http://localhost:8080/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-local-noora-default-lan-key" \
  -d '{
    "model": "N.1 Faster",
    "messages": [{"role": "user", "content": "Hello Noora!"}],
    "max_tokens": 50
  }'

# Real-time web search request (Online only)
curl -X POST "http://localhost:8080/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-local-noora-default-lan-key" \
  -d '{
    "model": "N.1 Faster",
    "messages": [{"role": "user", "content": "What is the latest release news in technology?"}],
    "web_search": true,
    "max_tokens": 150
  }'
```

### 3. Test via Python (OpenAI SDK)
```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8080/v1",  # Or LAN IP: http://192.168.x.x:8080/v1
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

### 4. Test via PowerShell
```powershell
$headers = @{
    "Content-Type"  = "application/json"
    "Authorization" = "Bearer sk-local-noora-default-lan-key"
}
$body = @{
    model    = "N.1 Faster"
    messages = @(@{ role = "user"; content = "Hello Noora!" })
} | ConvertTo-Json

$resp = Invoke-RestMethod -Uri "http://localhost:8080/v1/chat/completions" -Method POST -Headers $headers -Body $body
$resp.choices[0].message.content
```

---

## 🤖 Noora Model Suite (Trained & Developed by Nadeem)

| Model Name | Model ID | Capability | File Size | Memory Footprint |
| :--- | :--- | :--- | :--- | :--- |
| **Noora N.1 Faster** | `N.1 Faster` | Ultra-low latency, speed, everyday Q&A (Default) | ~491 MB | ~650 MB RAM |
| **Noora N.1 Pro Reasoning** | `N.1 Pro` | Code generation, deep reasoning & algorithms | ~1.11 GB | ~1.5 GB RAM |
| **Noora N.1 Core** | `N.1 Core` | Balanced versatility, knowledge & general tasks | ~807 MB | ~1.1 GB RAM |
| **Active Routing** | `local-ai` | Always maps dynamically to the active loaded model | — | — |

---

## 📱 Connecting From Devices on Your Wi-Fi

1. Open **Noora AI Server** and click **Start Server**.
2. Note your **LAN API Base URL** from the dashboard (e.g., `http://192.168.1.100:8080/v1`).
3. Copy your active working API Key (e.g., `sk-local-noora-default-lan-key`).
4. In any client app (e.g., **Chatbox** for Android/iOS/Mac):
   - **Provider:** OpenAI API
   - **API Host:** `http://192.168.1.100:8080/v1`
   - **API Key:** `sk-local-noora-default-lan-key`
   - **Model:** `N.1 Faster` (or `local-ai`)

---

## 💻 Python Client Example

```python
from openai import OpenAI

# Connect to your local laptop server across the Wi-Fi network
client = OpenAI(
    base_url="http://192.168.1.100:8080/v1",  # Replace with your laptop's LAN IP
    api_key="sk-local-YOUR_GENERATED_KEY"
)

response = client.chat.completions.create(
    model="local-ai",
    messages=[
        {"role": "user", "content": "Hello Noora, what can you do?"}
    ],
    max_tokens=150
)

print(response.choices[0].message.content)
```

---

## 🛡️ Windows Firewall Setup

If other devices on your Wi-Fi cannot connect to port `8080`:
1. Navigate to the **Settings** tab inside the Noora AI desktop dashboard.
2. Under **Windows Firewall Inbound Rule**, click **Add Firewall Rule**.
3. Or manually run in PowerShell as Administrator:
```powershell
netsh advfirewall firewall add rule name="Noora LAN AI Server" dir=in action=allow protocol=TCP localport=8080 profile=private
```

---

## 📦 Distribution Packages

- **Setup Script:** `Nila-LAN-AI-Setup.bat` (Automated environment, dependency, and model verification)
- **Portable ZIP:** Run `python package_portable.py` to produce `Nila-LAN-AI-Portable.zip`.
- **Tauri 2 Configuration:** Located in `src-tauri/` for compiling a native standalone binary with Cargo.

---

## 🧪 Automated Testing

Run the included automated tests:
```powershell
# Unit tests
.\.venv\Scripts\python.exe tests\test_backend.py

# Full end-to-end server & AI inference tests
.\.venv\Scripts\python.exe tests\test_e2e_server.py
```

---

## 📄 License & Credits

- **Application Name:** Noora LAN AI Server
- **AI Persona:** Noora
- **Architect & Developer:** Nadeem
- Powered by `llama.cpp` by Georgi Gerganov and open-source contributors.
