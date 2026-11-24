import os
import sys
import time
import json
import asyncio
import httpx
from typing import Optional, List, Dict, Any, Union
from pathlib import Path
from pydantic import BaseModel, Field
from fastapi import FastAPI, Request, HTTPException, Depends, Header, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import (
    APP_NAME, AI_NAME, DEVELOPER, VERSION,
    DEFAULT_GATEWAY_PORT, DEFAULT_INFERENCE_PORT, LOOPBACK_HOST,
    MODELS_DIR, TRUSTED_MODELS_CATALOG, NOORA_MODELS, STATIC_DIR,
    CPU_PHYSICAL_CORES, CPU_LOGICAL_CORES, CPU_MODEL_NAME, DEFAULT_CONTEXT_SIZE
)
from backend.database import (
    init_db, get_db_connection, verify_api_key, generate_api_key,
    get_active_working_key, resolve_model_filename, log_api_request, log_system_event,
    is_ip_blocked, set_ip_blocked_status, get_server_setting,
    update_server_setting, prune_old_logs,
    get_all_knowledge_documents, get_knowledge_document,
    get_chunks_by_document, delete_knowledge_document
)
from backend.inference import engine
from backend.network_utils import (
    get_network_interfaces, get_primary_lan_ip, is_private_lan_ip, resolve_hostname
)
from backend.firewall import check_firewall_rule, add_firewall_rule, remove_firewall_rule
from backend.web_search import (
    check_internet_connectivity, perform_web_search, should_trigger_web_search,
    format_search_context, format_collapsible_sources_markdown, analyze_search_intent,
    is_datetime_query, get_datetime_search_data
)
from backend.knowledge import (
    analyze_and_train_markdown, search_knowledge_memory, format_knowledge_context,
    format_collapsible_memory_markdown
)

# Initialize Database on startup
init_db()

app = FastAPI(
    title=APP_NAME,
    version=VERSION,
    description=f"{APP_NAME} - Developed by {DEVELOPER}"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_rate_limits: Dict[int, List[float]] = {}
_active_downloads: Dict[str, Dict[str, Any]] = {}

# ----------------- Security & Middleware -----------------

def check_rate_limit(key_id: int, rpm_limit: int) -> bool:
    now = time.time()
    if key_id not in _rate_limits:
        _rate_limits[key_id] = []
    _rate_limits[key_id] = [t for t in _rate_limits[key_id] if now - t < 60]
    if len(_rate_limits[key_id]) >= rpm_limit:
        return False
    _rate_limits[key_id].append(now)
    return True

async def authenticate_request(request: Request, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    client_ip = request.client.host if request.client else "127.0.0.1"

    if is_ip_blocked(client_ip):
        log_api_request(client_ip, request.url.path, request.method, 403, 0.0, error_message="IP is blocked")
        raise HTTPException(status_code=403, detail="Access denied: Your IP address is blocked.")

    lan_only = get_server_setting("lan_access_only", "true").lower() == "true"
    if lan_only and not is_private_lan_ip(client_ip):
        log_api_request(client_ip, request.url.path, request.method, 403, 0.0, error_message="Non-LAN IP access blocked")
        raise HTTPException(status_code=403, detail="Access restricted to local LAN subnet.")

    # Localhost auto-auth convenience
    is_localhost = client_ip in ["127.0.0.1", "::1", "localhost"]
    if is_localhost and (not authorization or authorization in ["Bearer auto", "Bearer local-dev", "Bearer test-key"]):
        active_key = get_active_working_key()
        if active_key:
            return active_key

    if not authorization or not authorization.startswith("Bearer "):
        log_api_request(client_ip, request.url.path, request.method, 401, 0.0, error_message="Missing or malformed Authorization header")
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Missing Authorization header. Provide a valid 'Bearer sk-local-...' API key."
        )

    raw_key = authorization.replace("Bearer ", "").strip()
    key_record = verify_api_key(raw_key)
    if not key_record:
        log_api_request(client_ip, request.url.path, request.method, 401, 0.0, error_message="Invalid or revoked API key")
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Invalid, expired, or revoked API key. Copy the active key from the Noora AI dashboard."
        )

    rpm_limit = key_record.get("rate_limit_rpm", 240)
    if not check_rate_limit(key_record["id"], rpm_limit):
        log_api_request(client_ip, request.url.path, request.method, 429, 0.0, api_key_name=key_record["name"], error_message="Rate limit exceeded")
        raise HTTPException(status_code=429, detail="Too Many Requests: Rate limit exceeded for this API key.")

    return key_record

# ----------------- Models & Schemas -----------------

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: Optional[str] = "N.1 Faster"
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 0.95
    max_tokens: Optional[int] = 2048
    stream: Optional[bool] = False
    web_search: Optional[bool] = None

class CompletionRequest(BaseModel):
    model: Optional[str] = "N.1 Faster"
    prompt: str
    max_tokens: Optional[int] = 1024
    temperature: Optional[float] = 0.7
    stream: Optional[bool] = False
    web_search: Optional[bool] = None

class SearchQueryRequest(BaseModel):
    query: str
    max_results: Optional[int] = 4

class KeyCreateRequest(BaseModel):
    name: str
    rate_limit_rpm: Optional[int] = 240

class ModelDownloadRequest(BaseModel):
    catalog_id: str

class SettingsUpdateRequest(BaseModel):
    server_port: Optional[str] = None
    cpu_threads: Optional[str] = None
    context_size: Optional[str] = None
    max_tokens: Optional[str] = None
    lan_access_only: Optional[str] = None
    rate_limit_default_rpm: Optional[str] = None
    dark_mode: Optional[str] = None
    enable_web_search: Optional[str] = None

class KnowledgeUploadTextRequest(BaseModel):
    filename: str
    content: str

class KnowledgeQueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 3
    min_score: Optional[float] = 0.5
    web_search_mode: Optional[str] = None
    web_search_max_results: Optional[str] = None

# ----------------- System & Health Endpoints -----------------

@app.get("/health")
async def health_check():
    lan_ip = get_primary_lan_ip()
    port = int(get_server_setting("server_port", str(DEFAULT_GATEWAY_PORT)))
    engine_stats = engine.get_stats()
    return {
        "status": "healthy" if engine_stats["status"] == "ONLINE" else "idle",
        "app_name": APP_NAME,
        "ai_name": AI_NAME,
        "developer": DEVELOPER,
        "version": VERSION,
        "server_status": engine_stats["status"],
        "active_model": engine_stats["active_model"],
        "active_model_id": engine_stats["active_model_id"],
        "lan_ip": lan_ip,
        "api_port": port,
        "base_url": f"http://{lan_ip}:{port}/v1",
        "models": ["N.1 Faster", "N.1 Pro", "N.1 Core"],
        "hardware": {
            "cpu_model": CPU_MODEL_NAME,
            "physical_cores": CPU_PHYSICAL_CORES,
            "logical_cores": CPU_LOGICAL_CORES,
            "threads_used": engine_stats.get("threads_used", 4),
            "batch_threads_used": engine_stats.get("batch_threads_used", 8),
            "context_size": engine_stats.get("context_size", DEFAULT_CONTEXT_SIZE)
        }
    }

@app.get("/api/server/status")
async def get_server_status():
    lan_ip = get_primary_lan_ip()
    port = int(get_server_setting("server_port", str(DEFAULT_GATEWAY_PORT)))
    engine_stats = engine.get_stats()

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as total FROM api_requests")
    total_requests = cur.fetchone()["total"]
    cur.execute("SELECT COUNT(*) as successful FROM api_requests WHERE status_code >= 200 AND status_code < 400")
    successful_requests = cur.fetchone()["successful"]
    cur.execute("SELECT COUNT(*) as failed FROM api_requests WHERE status_code >= 400")
    failed_requests = cur.fetchone()["failed"]

    cutoff_15m = time.time() - 900
    cur.execute("SELECT COUNT(*) as active_clients FROM devices WHERE last_seen > ?", (cutoff_15m,))
    active_clients = cur.fetchone()["active_clients"]
    conn.close()

    active_key = get_active_working_key()
    is_online, net_latency = check_internet_connectivity()
    web_search_enabled = get_server_setting("enable_web_search", "true").lower() == "true"
    web_search_mode = get_server_setting("web_search_mode", "auto")

    return {
        **engine_stats,
        "app_name": APP_NAME,
        "ai_name": AI_NAME,
        "developer": DEVELOPER,
        "lan_ip": lan_ip,
        "port": port,
        "api_base_url": f"http://{lan_ip}:{port}/v1",
        "active_working_key": active_key["raw_key"] if active_key else None,
        "active_key_prefix": active_key["key_prefix"] if active_key else None,
        "is_online": is_online,
        "internet_latency_ms": net_latency,
        "web_search_enabled": web_search_enabled,
        "web_search_mode": web_search_mode,
        "total_requests": total_requests,
        "successful_requests": successful_requests,
        "failed_requests": failed_requests,
        "active_clients": active_clients
    }

@app.get("/api/hardware")
async def get_hardware_info():
    stats = engine.get_stats()
    return {
        "cpu_model": CPU_MODEL_NAME,
        "physical_cores": CPU_PHYSICAL_CORES,
        "logical_cores": CPU_LOGICAL_CORES,
        "threads_used": stats.get("threads_used", 4),
        "batch_threads_used": stats.get("batch_threads_used", 8),
        "system_ram_gb": round(stats["system_ram_total_mb"] / 1024, 2),
        "available_ram_gb": round(stats["system_ram_free_mb"] / 1024, 2)
    }

@app.get("/api/network/connectivity")
async def get_network_connectivity():
    online, latency = check_internet_connectivity()
    return {
        "online": online,
        "latency_ms": latency,
        "web_search_enabled": get_server_setting("enable_web_search", "true").lower() == "true",
        "web_search_mode": get_server_setting("web_search_mode", "auto")
    }

@app.post("/api/web_search")
async def run_explicit_web_search(req: SearchQueryRequest):
    return perform_web_search(req.query, max_results=req.max_results or 4)

# ----------------- V1 Landing & Status Page -----------------

def render_v1_landing_html(lan_ip: str, port: int, active_key: str, active_model: str, server_status: str, cpu_model: str, is_internet_online: bool = True) -> str:
    base_url = f"http://{lan_ip}:{port}/v1"
    is_online = (server_status == "ONLINE")
    status_badge_class = "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" if is_online else "bg-amber-500/20 text-amber-400 border-amber-500/30"
    status_dot_class = "bg-emerald-400 animate-pulse" if is_online else "bg-amber-400"
    status_text = "Server Online & Ready" if is_online else f"Server {server_status}"

    net_badge_class = "bg-emerald-500/10 text-emerald-400 border-emerald-500/30" if is_internet_online else "bg-slate-800 text-slate-400 border-slate-700"
    net_icon = "bx-globe" if is_internet_online else "bx-wifi-off"
    net_text = "Online (Web Search Ready)" if is_internet_online else "Offline (Local Only)"
    websearch_checked = "checked" if is_internet_online else ""

    return f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Noora AI — LAN Server (Developed & Trained by Nadeem)</title>
  <link href="https://unpkg.com/boxicons@2.1.4/css/boxicons.min.css" rel="stylesheet">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {{
      darkMode: 'class',
      theme: {{
        extend: {{
          fontFamily: {{
            sans: ['Inter', 'system-ui', 'sans-serif'],
            mono: ['JetBrains Mono', 'monospace']
          }}
        }}
      }}
    }}
  </script>
  <style>
    body {{
      background-color: #070B14;
      color: #F3F4F6;
      font-family: 'Inter', sans-serif;
    }}
    .glass-panel {{
      background: rgba(15, 23, 42, 0.75);
      backdrop-filter: blur(14px);
      -webkit-backdrop-filter: blur(14px);
      border: 1px solid rgba(255, 255, 255, 0.08);
    }}
    .glass-card {{
      background: rgba(23, 31, 51, 0.65);
      backdrop-filter: blur(8px);
      -webkit-backdrop-filter: blur(8px);
      border: 1px solid rgba(255, 255, 255, 0.06);
    }}
  </style>
</head>
<body class="min-h-screen flex flex-col p-4 sm:p-6 md:p-10 selection:bg-indigo-500 selection:text-white">
  <div class="max-w-5xl w-full mx-auto space-y-6">

    <!-- Top Header -->
    <header class="glass-panel p-5 sm:p-6 rounded-2xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
      <div class="flex items-center space-x-3.5">
        <div class="w-12 h-12 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-500/30 text-white text-2xl font-bold">
          <i class="bx bx-bot"></i>
        </div>
        <div>
          <div class="flex items-center space-x-2">
            <h1 class="text-xl sm:text-2xl font-black text-white tracking-tight">Noora AI</h1>
            <span class="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">LAN Server</span>
          </div>
          <p class="text-xs text-slate-400 mt-0.5">
            Engineered, Developed & Trained by <span class="text-indigo-400 font-bold">Nadeem</span>
          </p>
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-2 w-full sm:w-auto justify-between sm:justify-end">
        <div class="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl border font-medium text-xs {net_badge_class}">
          <i class="bx {net_icon}"></i>
          <span>{net_text}</span>
        </div>
        <div class="flex items-center space-x-2 px-3 py-1.5 rounded-xl border font-medium text-xs {status_badge_class}">
          <span class="w-2 h-2 rounded-full {status_dot_class}"></span>
          <span>{status_text}</span>
        </div>
        <a href="/" class="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition-all flex items-center space-x-1.5 shadow-sm">
          <i class="bx bx-tachometer text-base"></i>
          <span>Full Dashboard</span>
        </a>
      </div>
    </header>

    <!-- LAN Access Credentials Card -->
    <div class="glass-panel p-6 rounded-2xl space-y-4">
      <div class="flex items-center justify-between">
        <h2 class="text-base font-bold text-white flex items-center gap-2">
          <i class="bx bx-wifi text-indigo-400 text-lg"></i>
          LAN Connection Endpoint & Active API Key
        </h2>
        <span class="text-[11px] font-semibold text-emerald-400 bg-emerald-500/10 px-2.5 py-0.5 rounded-full border border-emerald-500/20">
          Ready to Connect
        </span>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
        <!-- Base URL -->
        <div class="glass-card p-4 rounded-xl border border-indigo-500/30 space-y-2">
          <span class="text-slate-400 font-medium block">OpenAI-Compatible Base URL</span>
          <div class="flex items-center space-x-2">
            <input type="text" readOnly id="input-base-url" value="{base_url}" class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 font-mono text-slate-200 select-all focus:outline-none text-xs">
            <button onclick="copyField('input-base-url', 'btn-copy-url')" id="btn-copy-url" class="px-3 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold whitespace-nowrap transition-all flex items-center space-x-1">
              <i class="bx bx-copy"></i>
              <span>Copy</span>
            </button>
          </div>
          <p class="text-[11px] text-slate-500">Accessible from any phone, tablet, or PC connected to this Wi-Fi network.</p>
        </div>

        <!-- Active API Key -->
        <div class="glass-card p-4 rounded-xl border border-amber-500/30 space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-slate-400 font-medium block">Active Working API Key</span>
            <span class="text-[10px] text-amber-400 font-semibold px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/20">Auto-Authenticated</span>
          </div>
          <div class="flex items-center space-x-2">
            <input type="text" readOnly id="input-api-key" value="{active_key}" class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 font-mono text-amber-300 select-all focus:outline-none text-xs">
            <button onclick="copyField('input-api-key', 'btn-copy-key')" id="btn-copy-key" class="px-3 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold whitespace-nowrap transition-all flex items-center space-x-1">
              <i class="bx bx-copy"></i>
              <span>Copy Key</span>
            </button>
          </div>
          <p class="text-[11px] text-slate-500">Provide in <code>Authorization: Bearer &lt;API_KEY&gt;</code> header.</p>
        </div>
      </div>
    </div>

    <!-- Capability-Based Models Suite -->
    <div class="space-y-3">
      <div class="flex items-center justify-between">
        <h3 class="text-sm font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
          <i class="bx bx-chip text-indigo-400"></i>
          Noora Model Suite (Developed & Trained by Nadeem)
        </h3>
        <span class="text-xs text-indigo-400 font-mono font-medium">Active: {active_model}</span>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <!-- Model 1: N.1 Faster -->
        <div class="glass-card p-4 rounded-xl border border-indigo-500/40 bg-indigo-950/20 space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-xs font-mono font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/30">N.1 Faster</span>
            <span class="text-[10px] text-indigo-300 font-semibold">Speed / Fast</span>
          </div>
          <h4 class="text-sm font-bold text-white">Noora N.1 Faster</h4>
          <p class="text-[11px] text-slate-400 leading-relaxed">
            Ultra-low latency CPU inference (~1.2s response). Perfect for everyday chat, quick Q&A, and mobile apps.
          </p>
          <div class="pt-1 text-[10px] text-slate-500 font-mono">Model ID: <code>N.1 Faster</code></div>
        </div>

        <!-- Model 2: N.1 Pro -->
        <div class="glass-card p-4 rounded-xl border border-slate-800 space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-xs font-mono font-bold text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/30">N.1 Pro</span>
            <span class="text-[10px] text-indigo-300 font-semibold">Logic & Code</span>
          </div>
          <h4 class="text-sm font-bold text-white">Noora N.1 Pro Reasoning</h4>
          <p class="text-[11px] text-slate-400 leading-relaxed">
            Enhanced logic, coding assistance, and multi-step reasoning while staying lightweight on 4GB RAM.
          </p>
          <div class="pt-1 text-[10px] text-slate-500 font-mono">Model ID: <code>N.1 Pro</code></div>
        </div>

        <!-- Model 3: N.1 Core -->
        <div class="glass-card p-4 rounded-xl border border-slate-800 space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-xs font-mono font-bold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/30">N.1 Core</span>
            <span class="text-[10px] text-amber-300 font-semibold">Balanced</span>
          </div>
          <h4 class="text-sm font-bold text-white">Noora N.1 Core</h4>
          <p class="text-[11px] text-slate-400 leading-relaxed">
            Balanced versatility and general knowledge. Consistent accuracy across diverse questions.
          </p>
          <div class="pt-1 text-[10px] text-slate-500 font-mono">Model ID: <code>N.1 Core</code></div>
        </div>
      </div>
    </div>

    <!-- Live Test Chat Console Directly on this page -->
    <div class="glass-panel p-6 rounded-2xl space-y-4">
      <div class="flex items-center justify-between">
        <h3 class="text-base font-bold text-white flex items-center gap-2">
          <i class="bx bx-message-rounded-dots text-indigo-400 text-lg"></i>
          Test Prompt Directly in Browser
        </h3>
        <div class="flex items-center space-x-2 text-xs">
          <label class="flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-700 text-indigo-300 font-medium cursor-pointer hover:border-indigo-500/50 transition-all" title="AI automatically determines whether live web search is needed">
            <input type="checkbox" id="chat-web-search-toggle" {websearch_checked} class="accent-indigo-500 cursor-pointer">
            <span>🌐 AI Mode (Auto Search)</span>
          </label>
          <span class="text-slate-400 hidden sm:inline">Model:</span>
          <select id="chat-model-select" class="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1 text-slate-200 text-xs font-semibold focus:outline-none">
            <option value="N.1 Faster">Noora N.1 Faster (Fast)</option>
            <option value="N.1 Pro">Noora N.1 Pro (Reasoning)</option>
            <option value="N.1 Core">Noora N.1 Core (Balanced)</option>
            <option value="local-ai">local-ai (Active)</option>
          </select>
        </div>
      </div>

      <div class="space-y-3">
        <div class="relative">
          <textarea id="chat-prompt-input" rows="2" placeholder="Ask Noora a question (e.g. 'Who are you and who trained you?')" class="w-full bg-slate-900/90 border border-slate-700 rounded-xl p-3.5 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 resize-none font-sans"></textarea>
        </div>

        <div class="flex items-center justify-between">
          <span class="text-xs text-slate-500 flex items-center gap-1">
            <i class="bx bx-bolt-circle text-indigo-400"></i>
            100% CPU inference on Intel i5
          </span>
          <button onclick="sendTestChat()" id="btn-send-chat" class="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition-all flex items-center space-x-1.5 shadow-md active:scale-95">
            <i class="bx bx-send"></i>
            <span>Send Prompt</span>
          </button>
        </div>
      </div>

      <!-- Response Area -->
      <div id="chat-response-container" class="hidden p-4 rounded-xl bg-slate-900 border border-slate-800 text-sm font-sans space-y-2">
        <div class="flex items-center justify-between text-xs text-indigo-400 font-semibold border-b border-slate-800/80 pb-2">
          <div class="flex items-center space-x-1.5">
            <i class="bx bx-bot"></i>
            <span>Noora Response (<span id="resp-model-label">N.1 Faster</span>):</span>
          </div>
          <span id="resp-latency" class="font-mono text-slate-400 text-[11px]"></span>
        </div>
        <div id="chat-response-text" class="text-slate-200 whitespace-pre-wrap leading-relaxed pt-1"></div>
      </div>
    </div>

    <!-- Quick Integration Guide Cards -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
      <!-- Chatbox Setup -->
      <div class="glass-card p-5 rounded-xl space-y-2 border border-slate-800">
        <div class="flex items-center space-x-2 text-indigo-400 font-bold text-sm">
          <i class="bx bx-mobile-alt text-lg"></i>
          <span>Use with Chatbox App (Mobile / Desktop)</span>
        </div>
        <ol class="list-decimal list-inside space-y-1 text-slate-300 leading-relaxed pt-1">
          <li>Download free <strong>Chatbox</strong> app on your phone/PC.</li>
          <li>Set Provider to <strong>OpenAI API</strong>.</li>
          <li><strong>API Host:</strong> <code class="text-indigo-300">{base_url}</code></li>
          <li><strong>API Key:</strong> <code class="text-amber-300">{active_key}</code></li>
          <li><strong>Model:</strong> <code class="text-emerald-300">N.1 Faster</code> (or <code>local-ai</code>)</li>
        </ol>
      </div>

      <!-- Python SDK -->
      <div class="glass-card p-5 rounded-xl space-y-2 border border-slate-800">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-2 text-indigo-400 font-bold text-sm">
            <i class="bx bxl-python text-lg"></i>
            <span>Python (OpenAI SDK)</span>
          </div>
          <button onclick="copyPythonCode()" id="btn-copy-py" class="text-[11px] text-slate-400 hover:text-white px-2 py-0.5 rounded bg-slate-800 border border-slate-700">Copy Code</button>
        </div>
        <pre id="py-snippet" class="p-2.5 rounded-lg bg-slate-900 border border-slate-800 font-mono text-[11px] text-slate-300 overflow-x-auto leading-relaxed">from openai import OpenAI
client = OpenAI(
    base_url="{base_url}",
    api_key="{active_key}"
)
res = client.chat.completions.create(
    model="N.1 Faster",
    messages=[{{"role": "user", "content": "Hello Noora!"}}]
)
print(res.choices[0].message.content)</pre>
      </div>
    </div>

    <!-- Footer -->
    <footer class="text-center text-xs text-slate-500 py-4 border-t border-slate-800/80">
      <p>Noora AI LAN Server • Developed & Trained by <span class="text-indigo-400 font-semibold">Nadeem</span> • 100% On-Device CPU Inference</p>
    </footer>

  </div>

  <script>
    function copyField(inputId, btnId) {{
      const input = document.getElementById(inputId);
      const btn = document.getElementById(btnId);
      if (input) {{
        navigator.clipboard.writeText(input.value);
        if (btn) {{
          const origHtml = btn.innerHTML;
          btn.innerHTML = '<i class="bx bx-check"></i><span>Copied!</span>';
          setTimeout(() => {{ btn.innerHTML = origHtml; }}, 2000);
        }}
      }}
    }}

    function copyPythonCode() {{
      const snippet = document.getElementById('py-snippet');
      const btn = document.getElementById('btn-copy-py');
      if (snippet) {{
        navigator.clipboard.writeText(snippet.innerText);
        if (btn) {{
          btn.innerText = 'Copied!';
          setTimeout(() => {{ btn.innerText = 'Copy Code'; }}, 2000);
        }}
      }}
    }}

    async function sendTestChat() {{
      const input = document.getElementById('chat-prompt-input');
      const btn = document.getElementById('btn-send-chat');
      const container = document.getElementById('chat-response-container');
      const respText = document.getElementById('chat-response-text');
      const latencyLabel = document.getElementById('resp-latency');
      const modelSelect = document.getElementById('chat-model-select');
      const modelLabel = document.getElementById('resp-model-label');

      const prompt = input.value.trim();
      if (!prompt) return;

      const chosenModel = modelSelect ? modelSelect.value : 'N.1 Faster';
      if (modelLabel) modelLabel.innerText = chosenModel;

      const webSearchToggle = document.getElementById('chat-web-search-toggle');
      const useWebSearch = webSearchToggle ? webSearchToggle.checked : true;

      btn.disabled = true;
      btn.innerHTML = '<i class="bx bx-loader-alt animate-spin"></i><span>Analyzing & Generating...</span>';
      container.classList.remove('hidden');
      respText.innerHTML = '<span class="text-indigo-400 flex items-center gap-1.5"><i class="bx bx-loader-alt animate-spin"></i> Noora AI is analyzing prompt & generating response on CPU...</span>';
      latencyLabel.innerText = '';

      const startTime = performance.now();

      try {{
        const res = await fetch('{base_url}/chat/completions', {{
          method: 'POST',
          headers: {{
            'Content-Type': 'application/json',
            'Authorization': 'Bearer {active_key}'
          }},
          body: JSON.stringify({{
            model: chosenModel,
            web_search: useWebSearch,
            messages: [
              {{"role": "system", "content": "You are Noora, an intelligent and courteous AI assistant developed and trained by Nadeem. Running locally on Noora LAN AI Server."}},
              {{"role": "user", "content": prompt}}
            ],
            max_tokens: 400,
            stream: false
          }})
        }});

        const duration = Math.round(performance.now() - startTime);
        latencyLabel.innerText = `${{duration}} ms`;

        if (!res.ok) {{
          const err = await res.json().catch(() => ({{}}));
          respText.innerText = `⚠️ Error (${{res.status}}): ${{err.detail || 'Inference request failed'}}`;
          return;
        }}

        const data = await res.json();
        const content = data.choices?.[0]?.message?.content || 'No response generated.';
        
        // Render markdown links and collapsible sources details tag
        let formattedHtml = content
          .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
          .replace(/&lt;details class="noora-sources-accordion"(.*?)&gt;/g, '<details class="noora-sources-accordion mt-3 p-3 rounded-xl bg-slate-950 border border-indigo-500/30 text-xs" $1>')
          .replace(/&lt;\/details&gt;/g, '</details>')
          .replace(/&lt;summary class="noora-sources-summary"&gt;(.*?)&lt;\/summary&gt;/g, '<summary class="cursor-pointer font-semibold text-indigo-400 hover:text-indigo-300 flex items-center gap-1.5 select-none">$1</summary>')
          .replace(/&lt;div class="noora-sources-body"&gt;/g, '<div class="mt-2.5 space-y-2 text-slate-300 pl-2 border-l-2 border-indigo-500/40">')
          .replace(/&lt;\/div&gt;/g, '</div>')
          .replace(/\[([^\]]+)\]\((https?:\/\/[^\)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="text-indigo-400 hover:underline inline-flex items-center gap-0.5 font-medium">$1 <i class="bx bx-link-external text-[10px]"></i></a>')
          .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
          .replace(/\*([^*]+)\*/g, '<em>$1</em>');

        respText.innerHTML = formattedHtml;
      }} catch (err) {{
        const duration = Math.round(performance.now() - startTime);
        latencyLabel.innerText = `${{duration}} ms`;
        respText.innerText = `⚠️ Connection error: ${{err.message || 'Server unreachable'}}. Please check if server is running.`;
      }} finally {{
        btn.disabled = false;
        btn.innerHTML = '<i class="bx bx-send"></i><span>Send Prompt</span>';
      }}
    }}
  </script>
</body>
</html>"""


# ----------------- OpenAI-Compatible Endpoints -----------------

@app.get("/v1", response_class=HTMLResponse)
@app.get("/v1/", response_class=HTMLResponse)
async def v1_base_status(request: Request):
    """
    Renders an interactive status & connection page when accessed via browser,
    or returns OpenAI-compatible server status JSON when queried by an API client.
    """
    lan_ip = get_primary_lan_ip()
    port = int(get_server_setting("server_port", str(DEFAULT_GATEWAY_PORT)))
    engine_stats = engine.get_stats()
    active_key = get_active_working_key()
    active_key_str = active_key["raw_key"] if active_key else "sk-local-noora-default-lan-key"
    active_model = engine_stats.get("active_model", "Noora N.1 Faster")

    accept_header = request.headers.get("accept", "")
    format_param = request.query_params.get("format", "")

    # If client explicitly requests JSON (e.g. cURL with Accept: application/json or ?format=json)
    if "application/json" in accept_header and "text/html" not in accept_header or format_param == "json":
        return JSONResponse({
            "status": engine_stats["status"],
            "app_name": APP_NAME,
            "ai_name": AI_NAME,
            "developer": "Developed & Trained by Nadeem",
            "version": VERSION,
            "active_model": active_model,
            "active_key_status": "Active & Ready",
            "active_working_key": active_key_str,
            "lan_base_url": f"http://{lan_ip}:{port}/v1",
            "models_available": [
                {"id": "N.1 Faster", "name": "Noora N.1 Faster", "capability": "Ultra-Low Latency & High Speed", "developer": "Nadeem"},
                {"id": "N.1 Pro", "name": "Noora N.1 Pro Reasoning", "capability": "Deep Reasoning & Code Generation", "developer": "Nadeem"},
                {"id": "N.1 Core", "name": "Noora N.1 Core", "capability": "Balanced Versatility & Knowledge", "developer": "Nadeem"},
                {"id": "local-ai", "name": "Noora AI (Active)", "capability": "Auto-selected active model", "developer": "Nadeem"}
            ],
            "endpoints": {
                "models": "/v1/models",
                "chat_completions": "/v1/chat/completions",
                "completions": "/v1/completions"
            }
        })

    # Return rich interactive HTML landing page
    is_net_online, _ = check_internet_connectivity()
    html_content = render_v1_landing_html(
        lan_ip=lan_ip,
        port=port,
        active_key=active_key_str,
        active_model=active_model,
        server_status=engine_stats["status"],
        cpu_model=CPU_MODEL_NAME,
        is_internet_online=is_net_online
    )
    return HTMLResponse(content=html_content, status_code=200)


@app.get("/v1/models")
async def list_models(auth: Dict[str, Any] = Depends(authenticate_request)):
    # Curated Capability-Based Model Entries
    now = int(time.time())
    model_entries = [
        {
            "id": "N.1 Faster",
            "name": "Noora N.1 Faster (Developed & Trained by Nadeem)",
            "object": "model",
            "created": now,
            "owned_by": "Nadeem",
            "capability": "Ultra-Low Latency & High Speed",
            "permission": []
        },
        {
            "id": "noora-n.1-faster",
            "name": "Noora N.1 Faster",
            "object": "model",
            "created": now,
            "owned_by": "Nadeem",
            "permission": []
        },
        {
            "id": "N.1 Pro",
            "name": "Noora N.1 Pro Reasoning (Developed & Trained by Nadeem)",
            "object": "model",
            "created": now,
            "owned_by": "Nadeem",
            "capability": "Deep Reasoning & Code Generation",
            "permission": []
        },
        {
            "id": "noora-n.1-pro",
            "name": "Noora N.1 Pro Reasoning",
            "object": "model",
            "created": now,
            "owned_by": "Nadeem",
            "permission": []
        },
        {
            "id": "N.1 Core",
            "name": "Noora N.1 Core (Developed & Trained by Nadeem)",
            "object": "model",
            "created": now,
            "owned_by": "Nadeem",
            "capability": "Balanced Versatility & Knowledge",
            "permission": []
        },
        {
            "id": "noora-n.1-core",
            "name": "Noora N.1 Core",
            "object": "model",
            "created": now,
            "owned_by": "Nadeem",
            "permission": []
        },
        {
            "id": "local-ai",
            "name": "Noora AI (Active Model)",
            "object": "model",
            "created": now,
            "owned_by": "Nadeem",
            "permission": []
        }
    ]
    return {"object": "list", "data": model_entries}

@app.post("/v1/chat/completions")
async def chat_completions(
    req: ChatCompletionRequest,
    request: Request,
    auth: Dict[str, Any] = Depends(authenticate_request)
):
    client_ip = request.client.host if request.client else "127.0.0.1"
    start_time = time.time()

    # Model resolution & dynamic switching
    requested_model = req.model or "N.1 Faster"
    target_model_info = resolve_model_filename(requested_model)
    target_model_path = target_model_info["path"] if target_model_info else None

    # Check if target model is running
    needs_start = engine.status != "ONLINE"
    needs_switch = target_model_path and engine.active_model_path != str(Path(target_model_path).resolve())

    if needs_start or needs_switch:
        log_system_event("INFO", "INFERENCE", f"Dynamically launching {target_model_info['name'] if target_model_info else 'default model'}...")
        started, s_msg = engine.start_engine(model_path=target_model_path)
        if not started:
            log_api_request(client_ip, "/v1/chat/completions", "POST", 503, 0.0, api_key_name=auth["name"], error_message=s_msg)
            raise HTTPException(status_code=503, detail=f"AI Server failed to launch model: {s_msg}")

    # Prepare messages & inject identity with real-time clock anchor
    import datetime
    now_dt = datetime.datetime.now()
    cur_date_str = now_dt.strftime("%A, %B %d, %Y")
    cur_time_str = now_dt.strftime("%I:%M %p")
    temporal_anchor = (
        f"\n[Real-Time Clock & Calendar Data: Today is {cur_date_str}. Current local system time is {cur_time_str}. "
        f"Whenever asked about today's date, the current day, or current time, state these exact values clearly. "
        f"CRITICAL: Never output template placeholders like '[current date and time]' or '[current name of the current president]'. "
        f"Always provide real names, factual numbers, and direct answers.]"
    )

    messages_payload = []
    has_system = False
    for m in req.messages:
        if m.role == "system":
            has_system = True
            messages_payload.append({
                "role": "system",
                "content": f"{m.content}\n[Identity: You are {AI_NAME}, an intelligent, fast, and helpful AI assistant powered by Noora N.1, developed and trained by {DEVELOPER}.]{temporal_anchor}"
            })
        else:
            messages_payload.append({"role": m.role, "content": m.content})

    if not has_system:
        messages_payload.insert(0, {
            "role": "system",
            "content": f"You are {AI_NAME}, an intelligent, helpful, and courteous local AI assistant powered by Noora N.1. Developed and trained by {DEVELOPER}. You run 100% locally on this Windows machine with absolute privacy and high efficiency.{temporal_anchor}"
        })

    # ---------------- Intelligent AI-Powered Web Search Determination ----------------
    latest_user_text = ""
    for msg in reversed(req.messages):
        if msg.role == "user" and msg.content.strip():
            latest_user_text = msg.content.strip()
            break

    cfg_enable_search = get_server_setting("enable_web_search", "true").lower() == "true"
    cfg_search_mode = get_server_setting("web_search_mode", "auto").lower()
    max_search_res = int(get_server_setting("web_search_max_results", "4"))

    # Analyze question: Intelligent auto-detection in AI Mode
    intent_analysis = analyze_search_intent(latest_user_text) if latest_user_text else {"needs_search": False, "reason": "No input"}

    perform_search = False
    if req.web_search is False:
        # Explicitly disabled by client
        perform_search = False
    elif req.web_search == "force":
        # Explicitly forced by client
        perform_search = bool(latest_user_text)
    elif cfg_enable_search:
        # AI Mode: AI analyzes the question before generating an answer
        if cfg_search_mode == "always" and req.web_search is True:
            perform_search = bool(latest_user_text and len(latest_user_text) >= 3)
        else:
            # Automatic intelligent decision:
            # If the question requires current, recent, updated, or externally verifiable info -> True
            # If the question can be answered accurately using existing knowledge (coding, greeting, math, concepts) -> False
            perform_search = intent_analysis["needs_search"]

    search_sources = []
    # Fast-path 1: Date & Time Queries (Always accurate, zero external lag)
    if is_datetime_query(latest_user_text):
        dt_data = get_datetime_search_data()
        search_sources = dt_data["results"]
        web_context = format_search_context(dt_data)
        messages_payload[0]["content"] += f"\n\n{web_context}"
        log_system_event("INFO", "WEB_SEARCH", f"Supplied live authoritative date/time for: '{latest_user_text[:50]}'")
    # Fast-path 2: Live Web Search
    elif perform_search and latest_user_text:
        online, _ = check_internet_connectivity()
        if online:
            log_system_event("INFO", "WEB_SEARCH", f"AI triggered live web search ({intent_analysis.get('reason', 'real-time fact')}) for: '{latest_user_text[:60]}'")
            search_res = perform_web_search(latest_user_text, max_results=max_search_res)
            if search_res.get("results"):
                search_sources = search_res["results"]
                web_context = format_search_context(search_res)
                messages_payload[0]["content"] += f"\n\n{web_context}"
                log_system_event("INFO", "WEB_SEARCH", f"Retrieved {len(search_sources)} search results successfully.")
        else:
            log_system_event("INFO", "WEB_SEARCH", "Server is offline. Web search skipped; using local offline model.")
            messages_payload[0]["content"] += "\n\n[System Note: Web search was deemed beneficial, but the server is currently offline. Answering using internal local neural model knowledge.]"
    else:
        log_system_event("INFO", "INFERENCE", f"AI Mode decided direct neural answer without web search. Reason: {intent_analysis.get('reason', 'direct knowledge')}")

    # ---------------- AI Trained Knowledge Memory Retrieval ----------------
    memory_sources = []
    if latest_user_text:
        try:
            matched_chunks = search_knowledge_memory(latest_user_text, top_k=2)
            if matched_chunks:
                memory_sources = matched_chunks
                knowledge_context = format_knowledge_context(matched_chunks)
                messages_payload[0]["content"] += f"\n\n{knowledge_context}"
                log_system_event("INFO", "KNOWLEDGE", f"Applied {len(matched_chunks)} trained knowledge memory chunks for: '{latest_user_text[:50]}'")
        except Exception as e:
            log_system_event("WARN", "KNOWLEDGE", f"Knowledge memory lookup warning: {str(e)}")

    # Context Guardrail: Prevent exceed_context_size_error on big questions
    # Estimate token count (~3.5 chars per token)
    total_estimated_tokens = sum(len(m["content"]) for m in messages_payload) // 3.5
    max_safe_prompt_tokens = 7200  # Safe limit within 8192 context

    if total_estimated_tokens > max_safe_prompt_tokens and len(messages_payload) > 2:
        # Keep system message (0) and latest user prompt (-1), truncate older middle history
        sys_msg = messages_payload[0]
        latest_msg = messages_payload[-1]
        truncated_history = []
        cur_tokens = len(sys_msg["content"]) // 3.5 + len(latest_msg["content"]) // 3.5
        
        for m in reversed(messages_payload[1:-1]):
            t_count = len(m["content"]) // 3.5
            if cur_tokens + t_count < max_safe_prompt_tokens:
                truncated_history.insert(0, m)
                cur_tokens += t_count
            else:
                break
        messages_payload = [sys_msg] + truncated_history + [latest_msg]
        log_system_event("INFO", "GATEWAY", f"Context guardrail adjusted big prompt to fit safe window.")

    llama_payload = {
        "messages": messages_payload,
        "temperature": req.temperature or 0.7,
        "top_p": req.top_p or 0.95,
        "max_tokens": req.max_tokens or 2048,
        "stream": req.stream
    }

    engine_url = f"http://{engine.host}:{engine.port}/v1/chat/completions"
    http_timeout = httpx.Timeout(connect=25.0, read=600.0, write=60.0, pool=60.0)

    if req.stream:
        async def event_generator():
            accumulated_text = ""
            # Send initial keepalive comment immediately so client connects in 0ms without timing out
            yield ": connected\n\n"
            try:
                async with httpx.AsyncClient(timeout=http_timeout) as client:
                    async with client.stream("POST", engine_url, json=llama_payload) as resp:
                        if resp.status_code != 200:
                            err_body = await resp.aread()
                            yield f"data: {json.dumps({'error': err_body.decode('utf-8', 'ignore')})}\n\n"
                            return
                        async for line in resp.aiter_lines():
                            if line:
                                if line.startswith("data: ") and line.strip().endswith("[DONE]"):
                                    appended_blocks = []
                                    if memory_sources:
                                        appended_blocks.append(format_collapsible_memory_markdown(memory_sources))
                                    if search_sources:
                                        appended_blocks.append(format_collapsible_sources_markdown(search_sources))

                                    if appended_blocks:
                                        source_chunk = {
                                            "choices": [{
                                                "delta": {"content": "\n".join(appended_blocks)},
                                                "index": 0,
                                                "finish_reason": None
                                            }]
                                        }
                                        yield f"data: {json.dumps(source_chunk)}\n\n"
                                yield f"{line}\n\n"
                                if line.startswith("data: ") and not line.strip().endswith("[DONE]"):
                                    try:
                                        chunk_json = json.loads(line[6:])
                                        delta = chunk_json.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                        accumulated_text += delta
                                    except Exception:
                                        pass
                latency_ms = round((time.time() - start_time) * 1000, 2)
                est_tokens = max(1, len(accumulated_text) // 4)
                log_api_request(
                    client_ip, "/v1/chat/completions", "POST", 200, latency_ms,
                    tokens_prompt=len(str(messages_payload)) // 4,
                    tokens_completion=est_tokens,
                    api_key_name=auth["name"]
                )
            except Exception as e:
                latency_ms = round((time.time() - start_time) * 1000, 2)
                log_api_request(client_ip, "/v1/chat/completions", "POST", 500, latency_ms, api_key_name=auth["name"], error_message=str(e))
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    else:
        try:
            async with httpx.AsyncClient(timeout=http_timeout) as client:
                resp = await client.post(engine_url, json=llama_payload)
                latency_ms = round((time.time() - start_time) * 1000, 2)
                if resp.status_code != 200:
                    err_text = resp.text
                    log_api_request(client_ip, "/v1/chat/completions", "POST", resp.status_code, latency_ms, api_key_name=auth["name"], error_message=err_text)
                    raise HTTPException(status_code=resp.status_code, detail=err_text)

                data = resp.json()
                usage = data.get("usage", {})
                tokens_prompt = usage.get("prompt_tokens", 0)
                tokens_completion = usage.get("completion_tokens", 0)

                # Set model name and attach sources in response
                data["model"] = target_model_info["name"] if target_model_info else "Noora N.1 Faster"
                appended_texts = []
                if memory_sources:
                    data["knowledge_memory"] = memory_sources
                    appended_texts.append(format_collapsible_memory_markdown(memory_sources))
                if search_sources:
                    data["sources"] = search_sources
                    appended_texts.append(format_collapsible_sources_markdown(search_sources))

                if appended_texts and data.get("choices") and len(data["choices"]) > 0:
                    data["choices"][0]["message"]["content"] += "\n" + "\n".join(appended_texts)

                log_api_request(
                    client_ip, "/v1/chat/completions", "POST", 200, latency_ms,
                    tokens_prompt=tokens_prompt,
                    tokens_completion=tokens_completion,
                    api_key_name=auth["name"]
                )
                return data
        except HTTPException:
            raise
        except Exception as e:
            latency_ms = round((time.time() - start_time) * 1000, 2)
            log_api_request(client_ip, "/v1/chat/completions", "POST", 500, latency_ms, api_key_name=auth["name"], error_message=str(e))
            raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")

@app.post("/v1/completions")
async def text_completions(
    req: CompletionRequest,
    request: Request,
    auth: Dict[str, Any] = Depends(authenticate_request)
):
    client_ip = request.client.host if request.client else "127.0.0.1"
    start_time = time.time()

    if engine.status != "ONLINE":
        engine.start_engine()

    engine_url = f"http://{engine.host}:{engine.port}/v1/completions"
    http_timeout = httpx.Timeout(connect=25.0, read=600.0, write=60.0, pool=60.0)

    try:
        async with httpx.AsyncClient(timeout=http_timeout) as client:
            resp = await client.post(engine_url, json={
                "prompt": req.prompt,
                "max_tokens": req.max_tokens,
                "temperature": req.temperature,
                "stream": False
            })
            latency_ms = round((time.time() - start_time) * 1000, 2)
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
            data = resp.json()
            usage = data.get("usage", {})
            log_api_request(
                client_ip, "/v1/completions", "POST", 200, latency_ms,
                tokens_prompt=usage.get("prompt_tokens", 0),
                tokens_completion=usage.get("completion_tokens", 0),
                api_key_name=auth["name"]
            )
            return data
    except HTTPException:
        raise
    except Exception as e:
        latency_ms = round((time.time() - start_time) * 1000, 2)
        log_api_request(client_ip, "/v1/completions", "POST", 500, latency_ms, api_key_name=auth["name"], error_message=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# ----------------- Dashboard & Admin API -----------------

@app.post("/api/server/start")
async def start_server():
    threads = int(get_server_setting("cpu_threads", str(CPU_PHYSICAL_CORES)))
    ctx = int(get_server_setting("context_size", str(DEFAULT_CONTEXT_SIZE)))
    success, msg = engine.start_engine(threads=threads, context_size=ctx)
    return {"success": success, "message": msg, "status": engine.status}

@app.post("/api/server/stop")
async def stop_server():
    success, msg = engine.stop_engine()
    return {"success": success, "message": msg, "status": engine.status}

@app.post("/api/server/restart")
async def restart_server():
    success, msg = engine.restart_engine()
    return {"success": success, "message": msg, "status": engine.status}

@app.get("/api/models")
async def get_models():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM models ORDER BY is_active DESC, id DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/models/active")
async def set_active_model(payload: Dict[str, int]):
    model_id = payload.get("id")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE models SET is_active = 0")
    cur.execute("UPDATE models SET is_active = 1 WHERE id = ?", (model_id,))
    cur.execute("SELECT path, name, model_id FROM models WHERE id = ?", (model_id,))
    target = cur.fetchone()
    conn.commit()
    conn.close()

    if target and engine.status == "ONLINE":
        engine.restart_engine(model_path=target["path"])

    return {"success": True, "message": f"Active model updated to {target['name'] if target else 'None'}"}

@app.delete("/api/models/{model_id}")
async def delete_model(model_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT path, filename, is_active FROM models WHERE id = ?", (model_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Model not found")

    if row["is_active"] and engine.status == "ONLINE":
        engine.stop_engine()

    path = Path(row["path"])
    if path.exists():
        try:
            path.unlink()
        except Exception as e:
            conn.close()
            raise HTTPException(status_code=500, detail=f"Failed to delete model file: {e}")

    cur.execute("DELETE FROM models WHERE id = ?", (model_id,))
    conn.commit()
    conn.close()
    return {"success": True, "message": f"Model {row['filename']} deleted."}

@app.get("/api/models/catalog")
async def get_catalog():
    return TRUSTED_MODELS_CATALOG

@app.get("/api/models/download/status")
async def get_download_status():
    return _active_downloads

@app.post("/api/models/download")
async def download_catalog_model(req: ModelDownloadRequest, background_tasks: BackgroundTasks):
    item = next((m for m in TRUSTED_MODELS_CATALOG if m["id"] == req.catalog_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Model catalog entry not found.")

    filename = item["filename"]
    dest_path = MODELS_DIR / filename
    if dest_path.exists():
        return {"success": False, "message": "Model already downloaded and exists."}

    if filename in _active_downloads and _active_downloads[filename]["status"] == "downloading":
        return {"success": True, "message": "Download is already in progress."}

    _active_downloads[filename] = {
        "status": "downloading",
        "progress_percent": 0.0,
        "downloaded_mb": 0.0,
        "total_mb": item["size_mb"],
        "error": None
    }

    def run_download():
        import urllib.request
        try:
            url = item["download_url"]
            part_path = str(dest_path) + ".part"
            req_dl = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req_dl) as resp, open(part_path, "wb") as f:
                total = int(resp.headers.get("Content-Length", item["size_mb"] * 1024 * 1024))
                downloaded = 0
                while True:
                    chunk = resp.read(1024 * 512)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    _active_downloads[filename]["downloaded_mb"] = round(downloaded / (1024 * 1024), 1)
                    _active_downloads[filename]["progress_percent"] = round((downloaded * 100.0) / total, 1)

            os.rename(part_path, str(dest_path))
            _active_downloads[filename]["status"] = "completed"
            _active_downloads[filename]["progress_percent"] = 100.0

            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO models (name, model_id, capability, filename, path, size_bytes, format, is_active, downloaded_at)
            VALUES (?, ?, ?, ?, ?, ?, 'GGUF', 0, ?)
            ON CONFLICT(filename) DO NOTHING
            """, (item["name"], item.get("model_id", item["name"]), item.get("capability", "General Intelligence"), filename, str(dest_path.resolve()), dest_path.stat().st_size, time.time()))
            conn.commit()
            conn.close()

        except Exception as e:
            _active_downloads[filename]["status"] = "failed"
            _active_downloads[filename]["error"] = str(e)

    background_tasks.add_task(run_download)
    return {"success": True, "message": f"Download started for {item['name']}"}

# ----------------- API Key Endpoints -----------------

@app.get("/api/keys")
async def list_keys():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, key_prefix, raw_key, created_at, last_used_at, request_count, is_active, rate_limit_rpm FROM api_keys ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/api/keys/active")
async def get_active_key_info():
    active = get_active_working_key()
    lan_ip = get_primary_lan_ip()
    port = int(get_server_setting("server_port", str(DEFAULT_GATEWAY_PORT)))
    raw_key = active["raw_key"] if active else "sk-local-noora-default-lan-key"
    base_url = f"http://{lan_ip}:{port}/v1"

    return {
        "active_key": active,
        "raw_key": raw_key,
        "base_url": base_url,
        "model": "N.1 Faster",
        "models_available": ["N.1 Faster", "N.1 Pro", "N.1 Core"],
        "quick_curl": f'curl -X POST "{base_url}/chat/completions" -H "Authorization: Bearer {raw_key}" -H "Content-Type: application/json" -d \'{{"model":"N.1 Faster","messages":[{{"role":"user","content":"Hello Noora!"}}]}}\'',
        "python_sample": f'''from openai import OpenAI\n\nclient = OpenAI(\n    base_url="{base_url}",\n    api_key="{raw_key}"\n)\n\nresponse = client.chat.completions.create(\n    model="N.1 Faster",\n    messages=[{{"role": "user", "content": "Hello Noora!"}}]\n)\nprint(response.choices[0].message.content)'''
    }

@app.post("/api/keys/create")
async def create_key(req: KeyCreateRequest):
    raw_key, record = generate_api_key(req.name, req.rate_limit_rpm or 240)
    return {
        "success": True,
        "raw_key": raw_key,
        "record": record
    }

@app.post("/api/keys/{key_id}/toggle")
async def toggle_key(key_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE api_keys SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END WHERE id = ?", (key_id,))
    cur.execute("SELECT id, is_active FROM api_keys WHERE id = ?", (key_id,))
    row = cur.fetchone()
    conn.commit()
    conn.close()
    return {"success": True, "is_active": row["is_active"] if row else 0}

@app.delete("/api/keys/{key_id}")
async def revoke_key(key_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM api_keys WHERE id = ?", (key_id,))
    conn.commit()
    conn.close()
    return {"success": True, "message": "API key revoked and deleted."}

# ----------------- Connected Devices Endpoints -----------------

@app.get("/api/devices")
async def list_devices():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM devices ORDER BY last_seen DESC")
    rows = cur.fetchall()
    conn.close()
    devices = []
    now = time.time()
    for r in rows:
        d = dict(r)
        diff = now - d["last_seen"]
        if diff < 600:
            d["observed_status"] = "Active"
        elif diff < 86400:
            d["observed_status"] = "Recent"
        else:
            d["observed_status"] = "Idle"
        devices.append(d)
    return devices

@app.post("/api/devices/{ip}/block")
async def block_device(ip: str):
    set_ip_blocked_status(ip, True, reason="Manual block from dashboard")
    return {"success": True, "message": f"IP {ip} has been blocked."}

@app.post("/api/devices/{ip}/unblock")
async def unblock_device(ip: str):
    set_ip_blocked_status(ip, False)
    return {"success": True, "message": f"IP {ip} has been unblocked."}

# ----------------- Logs & Analytics Endpoints -----------------

@app.get("/api/logs/requests")
async def get_request_logs(limit: int = 50, offset: int = 0):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM api_requests ORDER BY timestamp DESC LIMIT ? OFFSET ?", (limit, offset))
    rows = cur.fetchall()
    cur.execute("SELECT COUNT(*) as count FROM api_requests")
    total = cur.fetchone()["count"]
    conn.close()
    return {"total": total, "items": [dict(r) for r in rows]}

@app.get("/api/logs/system")
async def get_system_logs(limit: int = 100):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM application_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/logs/clear")
async def clear_logs():
    prune_old_logs(days=0)
    return {"success": True, "message": "Audit and system logs purged."}

# ----------------- Network & Firewall Endpoints -----------------

@app.get("/api/network/interfaces")
async def list_interfaces():
    return {
        "interfaces": get_network_interfaces(),
        "primary_lan_ip": get_primary_lan_ip()
    }

@app.get("/api/firewall/status")
async def get_firewall_status():
    port = int(get_server_setting("server_port", str(DEFAULT_GATEWAY_PORT)))
    return check_firewall_rule(port=port)

@app.post("/api/firewall/configure")
async def configure_firewall(action: Dict[str, str]):
    port = int(get_server_setting("server_port", str(DEFAULT_GATEWAY_PORT)))
    act = action.get("action", "add")
    if act == "add":
        return add_firewall_rule(port=port)
    elif act == "remove":
        return remove_firewall_rule()
    return {"success": False, "message": "Invalid action"}

# ----------------- Settings Endpoints -----------------

@app.get("/api/settings")
async def get_settings():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT key, value FROM server_settings")
    rows = cur.fetchall()
    conn.close()
    settings = {r["key"]: r["value"] for r in rows}
    return settings

@app.post("/api/settings")
async def update_settings(payload: SettingsUpdateRequest):
    updates = payload.model_dump(exclude_unset=True)
    for k, v in updates.items():
        if v is not None:
            update_server_setting(k, str(v))
    return {"success": True, "message": "Settings updated."}

# ----------------- AI Training & Knowledge Memory Endpoints -----------------

@app.post("/api/knowledge/upload")
async def upload_knowledge_payload(request: Request):
    """
    Accepts JSON body: { "filename": "example.md", "content": "# My Doc..." }
    Or raw text / markdown body.
    """
    content_type = request.headers.get("content-type", "")
    filename = request.query_params.get("filename", "uploaded_knowledge.md")
    
    if "application/json" in content_type:
        try:
            body = await request.json()
            filename = body.get("filename", filename)
            content = body.get("content", "")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON format.")
    else:
        raw_bytes = await request.body()
        try:
            content = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            content = raw_bytes.decode("latin-1", errors="replace")
            
    if not content.strip():
        raise HTTPException(status_code=400, detail="Document content cannot be empty.")
        
    result = analyze_and_train_markdown(filename, content)
    log_system_event("INFO", "KNOWLEDGE", f"Trained document '{filename}' ({result['chunk_count']} chunks, {result['word_count']} words)")
    return result

@app.post("/api/knowledge/train-text")
async def train_knowledge_text(payload: KnowledgeUploadTextRequest):
    if not payload.content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty.")
    result = analyze_and_train_markdown(payload.filename, payload.content)
    log_system_event("INFO", "KNOWLEDGE", f"Trained direct text '{payload.filename}' ({result['chunk_count']} chunks, {result['word_count']} words)")
    return result

@app.get("/api/knowledge/documents")
async def list_knowledge_documents():
    docs = get_all_knowledge_documents()
    total_chunks = sum(d.get("chunk_count", 0) for d in docs)
    total_words = sum(d.get("word_count", 0) for d in docs)
    return {
        "documents": docs,
        "total": len(docs),
        "total_chunks": total_chunks,
        "total_words": total_words
    }

@app.get("/api/knowledge/documents/{doc_id}")
async def get_knowledge_doc_details(doc_id: int):
    doc = get_knowledge_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Knowledge document not found")
    chunks = get_chunks_by_document(doc_id)
    return {"document": doc, "chunks": chunks}

@app.delete("/api/knowledge/documents/{doc_id}")
async def remove_knowledge_document(doc_id: int):
    deleted = delete_knowledge_document(doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Knowledge document not found")
    log_system_event("INFO", "KNOWLEDGE", f"Deleted knowledge document #{doc_id}")
    return {"success": True, "message": "Knowledge document and associated memory chunks deleted successfully."}

@app.post("/api/knowledge/query")
async def test_knowledge_query(payload: KnowledgeQueryRequest):
    matches = search_knowledge_memory(payload.query, top_k=payload.top_k or 3, min_score=payload.min_score or 0.5)
    return {
        "query": payload.query,
        "matches": matches,
        "count": len(matches)
    }

if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
