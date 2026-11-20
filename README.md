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

---

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React 19, Vite, TypeScript, Tailwind CSS, Boxicons, Framer Motion |
| **Desktop Shell** | Windows Edge WebView2 (pywebview) + Tauri 2 Ready (`src-tauri/`) |
| **Backend Gateway** | Python 3.10+, FastAPI, Uvicorn, SQLite (WAL mode) |
| **AI Engine** | `llama.cpp` (`llama-server.exe` build 12499 x64 CPU AVX2) |
| **Model Format** | GGUF (Quantized 4-bit Q4_K_M for ultra-low RAM footprint) |

---

## 🚀 Quick Start

### 1. Launch the Desktop Application
Double-click:
```bat
run_desktop.bat
```
This opens the modern, glassmorphic desktop GUI.

### 2. Or Run in Headless Server Mode
```bat
run_headless.bat
```
Listening on `http://<YOUR_LAN_IP>:8080`.

---

## 📱 Connecting From Devices on Your Wi-Fi

1. Open **Noora AI Server** and click **Start Server**.
2. Note your **LAN API Base URL** from the dashboard (e.g., `http://192.168.1.100:8080/v1`).
3. Generate an API Key under the **API Keys** tab (e.g., `sk-local-xxxxxxxxxxxxxxxx`).
4. In any application, client, or mobile app (e.g., Chatbox, OpenWebUI, Home Assistant, or Python), configure:
   - **Base URL:** `http://192.168.1.100:8080/v1`
   - **API Key:** `sk-local-xxxxxxxxxxxxxxxx`
   - **Model:** `local-ai` or your active GGUF model name.

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
