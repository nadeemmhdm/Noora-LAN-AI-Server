# Local Network (LAN) & Multi-Device Setup Guide

**Author:** Nadeem  
**Topic:** Connecting Mobile Devices, Tablets, and Secondary PCs to Noora AI

---

## 1. Prerequisites

Before connecting external devices:
1. Ensure your host Windows laptop and the external devices (iPhone, Android, Mac, iPad) are connected to the **exact same Wi-Fi router or network**.
2. Start the server on the laptop dashboard (**Status: ONLINE**).
3. Confirm the server LAN IP address displayed on the dashboard (e.g. `192.168.1.100` or `10.0.0.5`).

---

## 2. Windows Firewall Configuration

For devices on your Wi-Fi to reach port `8080`, an inbound rule must permit incoming TCP packets on port 8080.

### Method A: Automated (via Dashboard)
1. Navigate to the **Settings** tab in the desktop application.
2. Locate the **Windows Firewall Inbound Rule** card.
3. Click **Add Firewall Rule**.

### Method B: Manual (via Administrator PowerShell)
```powershell
netsh advfirewall firewall add rule name="Noora LAN AI Server" dir=in action=allow protocol=TCP localport=8080 profile=private
```

---

## 3. Client Platform Configuration Guides

### A. Chatbox App (Recommended for iOS, Android, macOS & Windows)
1. Download **Chatbox** from [chatboxai.app](https://chatboxai.app) or your mobile App Store.
2. Open Settings ⚙️ → **Model Provider** → Select **OpenAI API**.
3. Configure the following fields:
   - **API Host:** `http://<HOST_LAPTOP_IP>:8080/v1` *(e.g. `http://192.168.1.100:8080/v1`)*
   - **API Key:** `sk-local-noora-default-lan-key` *(or any key generated in API Keys tab)*
   - **Model:** `local-ai`
4. Save settings and start chatting.

---

### B. Python Client (OpenAI SDK)

```python
from openai import OpenAI

# Initialize client pointing to host laptop
client = OpenAI(
    base_url="http://192.168.1.100:8080/v1",  # Replace with host LAN IP
    api_key="sk-local-noora-default-lan-key"
)

response = client.chat.completions.create(
    model="local-ai",
    messages=[
        {"role": "user", "content": "Hello Noora, summarize local AI advantages."}
    ]
)

print(response.choices[0].message.content)
```

---

### C. OpenWebUI / LibreChat / NextChat
- **API URL:** `http://192.168.1.100:8080/v1`
- **API Key:** `sk-local-noora-default-lan-key`
- **Model Name:** `local-ai`

---

## 4. Subnet Security & Access Control

Noora AI implements RFC 1918 private subnet validation:
- Requests originating from private subnets (`192.168.x.x`, `10.x.x.x`, `172.16-31.x.x`, and `127.0.0.1`) are permitted.
- Any request originating from outside the local private network is rejected with HTTP 403 Forbidden.
- Device activity is tracked in the **Connected Devices** tab, where individual IP addresses can be blocked or unblocked instantly.
