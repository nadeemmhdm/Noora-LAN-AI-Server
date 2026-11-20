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
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import (
    APP_NAME, AI_NAME, DEVELOPER, VERSION,
    DEFAULT_GATEWAY_PORT, DEFAULT_INFERENCE_PORT, LOOPBACK_HOST,
    MODELS_DIR, TRUSTED_MODELS_CATALOG, STATIC_DIR,
    CPU_PHYSICAL_CORES, CPU_LOGICAL_CORES, CPU_MODEL_NAME
)
from backend.database import (
    init_db, get_db_connection, verify_api_key, generate_api_key,
    get_active_working_key, log_api_request, log_system_event,
    is_ip_blocked, set_ip_blocked_status, get_server_setting,
    update_server_setting, prune_old_logs
)
from backend.inference import engine
from backend.network_utils import (
    get_network_interfaces, get_primary_lan_ip, is_private_lan_ip, resolve_hostname
)
from backend.firewall import check_firewall_rule, add_firewall_rule, remove_firewall_rule

# Initialize Database on startup
init_db()

app = FastAPI(
    title=APP_NAME,
    version=VERSION,
    description=f"{APP_NAME} - Developed by {DEVELOPER}"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory rate-limiter: {key_id: [timestamps]}
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

    # 1. Check IP blocklist
    if is_ip_blocked(client_ip):
        log_api_request(client_ip, request.url.path, request.method, 403, 0.0, error_message="IP is blocked")
        raise HTTPException(status_code=403, detail="Access denied: Your IP address is blocked.")

    # 2. Check LAN Subnet Restriction
    lan_only = get_server_setting("lan_access_only", "true").lower() == "true"
    if lan_only and not is_private_lan_ip(client_ip):
        log_api_request(client_ip, request.url.path, request.method, 403, 0.0, error_message="Non-LAN IP access blocked")
        raise HTTPException(status_code=403, detail="Access restricted to local LAN subnet.")

    # 3. Handle Localhost / Web UI Playground Convenience
    is_localhost = client_ip in ["127.0.0.1", "::1", "localhost"]
    if is_localhost and (not authorization or authorization in ["Bearer auto", "Bearer local-dev", "Bearer test-key"]):
        active_key = get_active_working_key()
        if active_key:
            return active_key

    # 4. Authenticate Bearer API Key
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

    # 5. Check Rate Limits
    rpm_limit = key_record.get("rate_limit_rpm", 120)
    if not check_rate_limit(key_record["id"], rpm_limit):
        log_api_request(client_ip, request.url.path, request.method, 429, 0.0, api_key_name=key_record["name"], error_message="Rate limit exceeded")
        raise HTTPException(status_code=429, detail="Too Many Requests: Rate limit exceeded for this API key.")

    return key_record

# ----------------- Models & Schemas -----------------

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: Optional[str] = "local-ai"
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 0.95
    max_tokens: Optional[int] = 1024
    stream: Optional[bool] = False

class CompletionRequest(BaseModel):
    model: Optional[str] = "local-ai"
    prompt: str
    max_tokens: Optional[int] = 512
    temperature: Optional[float] = 0.7
    stream: Optional[bool] = False

class KeyCreateRequest(BaseModel):
    name: str
    rate_limit_rpm: Optional[int] = 120

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
        "lan_ip": lan_ip,
        "api_port": port,
        "base_url": f"http://{lan_ip}:{port}/v1",
        "hardware": {
            "cpu_model": CPU_MODEL_NAME,
            "physical_cores": CPU_PHYSICAL_CORES,
            "logical_cores": CPU_LOGICAL_CORES,
            "recommended_threads": CPU_PHYSICAL_CORES
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
        "total_requests": total_requests,
        "successful_requests": successful_requests,
        "failed_requests": failed_requests,
        "active_clients": active_clients
    }

@app.get("/api/hardware")
async def get_hardware_info():
    return {
        "cpu_model": CPU_MODEL_NAME,
        "physical_cores": CPU_PHYSICAL_CORES,
        "logical_cores": CPU_LOGICAL_CORES,
        "recommended_threads": CPU_PHYSICAL_CORES,
        "system_ram_gb": round(engine.get_stats()["system_ram_total_mb"] / 1024, 2),
        "available_ram_gb": round(engine.get_stats()["system_ram_free_mb"] / 1024, 2)
    }

# ----------------- OpenAI-Compatible Endpoints -----------------

@app.get("/v1/models")
async def list_models(auth: Dict[str, Any] = Depends(authenticate_request)):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT filename, name, downloaded_at FROM models")
    rows = cur.fetchall()
    conn.close()

    model_entries = []
    for r in rows:
        model_entries.append({
            "id": r["filename"],
            "object": "model",
            "created": int(r["downloaded_at"]),
            "owned_by": "local",
            "permission": []
        })
    model_entries.append({
        "id": "local-ai",
        "object": "model",
        "created": int(time.time()),
        "owned_by": "local",
        "permission": []
    })
    return {"object": "list", "data": model_entries}

@app.post("/v1/chat/completions")
async def chat_completions(
    req: ChatCompletionRequest,
    request: Request,
    auth: Dict[str, Any] = Depends(authenticate_request)
):
    client_ip = request.client.host if request.client else "127.0.0.1"
    start_time = time.time()

    # Auto-start engine if offline
    if engine.status != "ONLINE":
        log_system_event("INFO", "INFERENCE", "Auto-starting engine upon incoming request...")
        started, s_msg = engine.start_engine()
        if not started:
            log_api_request(client_ip, "/v1/chat/completions", "POST", 503, 0.0, api_key_name=auth["name"], error_message=s_msg)
            raise HTTPException(status_code=503, detail=f"AI Server is offline and failed to auto-start: {s_msg}")

    # Inject Noora AI identity
    messages_payload = []
    has_system = False
    for m in req.messages:
        if m.role == "system":
            has_system = True
            messages_payload.append({
                "role": "system",
                "content": f"{m.content}\n[Identity: You are {AI_NAME}, a fast, intelligent, and helpful local AI assistant running on Noora AI LAN Server. Developed by {DEVELOPER}.]"
            })
        else:
            messages_payload.append({"role": m.role, "content": m.content})

    if not has_system:
        messages_payload.insert(0, {
            "role": "system",
            "content": f"You are {AI_NAME}, an intelligent, helpful, and courteous local AI assistant running on Noora AI LAN Server. Developed by {DEVELOPER}. You run 100% locally on this Windows machine with absolute privacy and high efficiency."
        })

    llama_payload = {
        "messages": messages_payload,
        "temperature": req.temperature,
        "top_p": req.top_p,
        "max_tokens": req.max_tokens,
        "stream": req.stream
    }

    engine_url = f"http://{engine.host}:{engine.port}/v1/chat/completions"
    http_timeout = httpx.Timeout(connect=15.0, read=300.0, write=30.0, pool=30.0)

    if req.stream:
        async def event_generator():
            accumulated_text = ""
            try:
                async with httpx.AsyncClient(timeout=http_timeout) as client:
                    async with client.stream("POST", engine_url, json=llama_payload) as resp:
                        async for line in resp.aiter_lines():
                            if line:
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
                    log_api_request(client_ip, "/v1/chat/completions", "POST", resp.status_code, latency_ms, api_key_name=auth["name"], error_message=resp.text)
                    raise HTTPException(status_code=resp.status_code, detail=resp.text)

                data = resp.json()
                usage = data.get("usage", {})
                tokens_prompt = usage.get("prompt_tokens", 0)
                tokens_completion = usage.get("completion_tokens", 0)

                log_api_request(
                    client_ip, "/v1/chat/completions", "POST", 200, latency_ms,
                    tokens_prompt=tokens_prompt,
                    tokens_completion=tokens_completion,
                    api_key_name=auth["name"]
                )
                return data
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
    http_timeout = httpx.Timeout(connect=15.0, read=300.0, write=30.0, pool=30.0)

    try:
        async with httpx.AsyncClient(timeout=http_timeout) as client:
            resp = await client.post(engine_url, json={
                "prompt": req.prompt,
                "max_tokens": req.max_tokens,
                "temperature": req.temperature,
                "stream": False
            })
            latency_ms = round((time.time() - start_time) * 1000, 2)
            data = resp.json()
            usage = data.get("usage", {})
            log_api_request(
                client_ip, "/v1/completions", "POST", 200, latency_ms,
                tokens_prompt=usage.get("prompt_tokens", 0),
                tokens_completion=usage.get("completion_tokens", 0),
                api_key_name=auth["name"]
            )
            return data
    except Exception as e:
        latency_ms = round((time.time() - start_time) * 1000, 2)
        log_api_request(client_ip, "/v1/completions", "POST", 500, latency_ms, api_key_name=auth["name"], error_message=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# ----------------- Dashboard & Admin API -----------------

@app.post("/api/server/start")
async def start_server():
    threads = int(get_server_setting("cpu_threads", str(CPU_PHYSICAL_CORES)))
    ctx = int(get_server_setting("context_size", "2048"))
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
    cur.execute("SELECT path, name FROM models WHERE id = ?", (model_id,))
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
            INSERT INTO models (name, filename, path, size_bytes, format, is_active, downloaded_at)
            VALUES (?, ?, ?, ?, 'GGUF', 0, ?)
            ON CONFLICT(filename) DO NOTHING
            """, (item["name"], filename, str(dest_path.resolve()), dest_path.stat().st_size, time.time()))
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
        "model": "local-ai",
        "quick_curl": f'curl -X POST "{base_url}/chat/completions" -H "Authorization: Bearer {raw_key}" -H "Content-Type: application/json" -d \'{{"model":"local-ai","messages":[{{"role":"user","content":"Hello Noora!"}}]}}\'',
        "python_sample": f'''from openai import OpenAI\n\nclient = OpenAI(\n    base_url="{base_url}",\n    api_key="{raw_key}"\n)\n\nresponse = client.chat.completions.create(\n    model="local-ai",\n    messages=[{{"role": "user", "content": "Hello Noora!"}}]\n)\nprint(response.choices[0].message.content)'''
    }

@app.post("/api/keys/create")
async def create_key(req: KeyCreateRequest):
    raw_key, record = generate_api_key(req.name, req.rate_limit_rpm or 120)
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

# Mount static frontend build if present
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
