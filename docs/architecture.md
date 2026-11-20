# Noora AI Architecture & System Design

**Author:** Nadeem  
**Application:** Noora AI LAN Server (v1.0.0)  
**Target Architecture:** Windows 10/11 x64, Intel Core i5 CPU, 4GB+ RAM

---

## 1. High-Level Architecture Overview

Noora AI is architected as an on-demand, local-first artificial intelligence gateway. It converts a standard Windows laptop into an OpenAI-compatible inference server accessible across your local area network (LAN / Wi-Fi) without relying on external cloud infrastructure, reverse tunnels, or third-party relays.

```
+-------------------------------------------------------------------------------+
|                       Client Layer (LAN / Localhost)                         |
|   - Mobile (iOS/Android Chatbox)  - Python Scripts  - Desktop Applications    |
|   - Secondary Laptops / PCs       - cURL / CLI      - Noora Web UI Dashboard  |
+-------------------------------------------------------------------------------+
                                        |
                 HTTP REST / SSE (Port 8080 / Private Subnet)
                                        v
+-------------------------------------------------------------------------------+
|                       FastAPI Gateway (backend/gateway.py)                    |
|  - Subnet Validator: Restricts access strictly to RFC 1918 private subnets   |
|  - Authentication: Bearer Token verification against SHA-256 hashed keys     |
|  - Rate Limiter: Per-key request metering & throttling (RPM)                  |
|  - Telemetry & Audit: SQLite request logging (no prompt logging)              |
|  - OpenAI Compatibility Layer: /v1/chat/completions, /v1/models, /health      |
+-------------------------------------------------------------------------------+
                                        |
                          Loopback (127.0.0.1:8081)
                                        v
+-------------------------------------------------------------------------------+
|                 AI Inference Engine (backend/inference.py)                    |
|  - Managed Child Process: llama-server.exe (llama.cpp AVX2 CPU build)         |
|  - Pre-flight Memory Safety: Evaluates available system RAM before load       |
|  - Auto CPU Thread Tuning: Allocates physical cores to eliminate lockups      |
|  - On-Demand Lifecycle: Released immediately on stop or window close          |
+-------------------------------------------------------------------------------+
                                        |
+-------------------------------------------------------------------------------+
|                     Storage & Data Layer (SQLite + GGUF)                      |
|  - noora_ai.db: Models, hashed API keys, observed devices, audit metrics      |
|  - models/*.gguf: Quantized GGUF models (Qwen 2.5 0.5B, 1.5B, Llama 3.2 1B)   |
+-------------------------------------------------------------------------------+
```

---

## 2. Component Breakdown

### A. FastAPI Gateway (`backend/gateway.py`)
- Acts as the single point of entry exposed to the LAN.
- Enforces strict subnet isolation: verifies that client IP belongs to `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, or `127.0.0.1`.
- Forwards validated inference requests to internal `llama-server.exe` running on loopback (`127.0.0.1:8081`).
- Streams responses back to clients in real-time using Server-Sent Events (`text/event-stream`).

### B. Inference Engine Manager (`backend/inference.py`)
- Manages the `llama-server.exe` child process.
- Implements process safety:
  - Validates RAM availability via `psutil.virtual_memory()` before starting.
  - Spawns process with `CREATE_NO_WINDOW` on Windows to prevent console flashing.
  - Probes health endpoint (`/health`) on loopback before declaring the server ONLINE.
  - On shutdown, terminates the process tree cleanly (`taskkill /F /T /PID`) to prevent orphan processes.

### C. Persistent Storage (`backend/database.py`)
- SQLite database configured in WAL (Write-Ahead Logging) mode for concurrent access.
- Cryptographically secure API keys generated with `secrets.token_hex(16)`.
- Never stores raw secret keys; stores only SHA-256 hashes (`key_hash`).
- Logs API latency, HTTP response status codes, and token counts without recording private user prompts.

### D. Frontend Interface (`frontend/`)
- Built with React 19, Vite, TypeScript, and Tailwind CSS.
- Boxicons icon library for crisp vector rendering.
- Embedded directly into FastAPI as static files (`frontend/dist/`) and presented through Microsoft Edge WebView2 (`pywebview`).

---

## 3. Security Architecture

1. **Air-Gapped & Offline by Default:** Zero outbound telemetry or cloud requests during inference.
2. **Subnet Filtering:** External public IPs are rejected with HTTP 403 Forbidden.
3. **Loopback Isolation:** The raw inference engine binds strictly to `127.0.0.1:8081`, ensuring no unauthenticated LAN clients can bypass the gateway.
4. **Firewall Rule Management:** Manages Windows Firewall port 8080 rules strictly for Private network profiles without disabling system defenses.
