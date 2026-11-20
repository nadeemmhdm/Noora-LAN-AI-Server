import sys
import os
import time
import json
import threading
import urllib.request
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import APP_NAME, DEVELOPER
from backend.database import init_db, generate_api_key
from backend.inference import engine
import uvicorn

PORT = 8095
HOST = "127.0.0.1"

def run_server():
    from backend.gateway import app
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")

def run_tests():
    init_db()
    raw_key, record = generate_api_key("E2E Test Key", rate_limit_rpm=120)

    # 1. Test Static Frontend Serving
    print("[1] Testing static frontend root...")
    req = urllib.request.Request(f"http://{HOST}:{PORT}/")
    with urllib.request.urlopen(req, timeout=5) as resp:
        html = resp.read().decode()
        assert resp.status == 200
        assert "Noora AI" in html
        print("  -> Frontend served successfully.")

    # 2. Test Health Endpoint
    print("[2] Testing /health...")
    req = urllib.request.Request(f"http://{HOST}:{PORT}/health")
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode())
        assert resp.status == 200
        assert data["ai_name"] == "Noora"
        assert data["developer"] == "Nadeem"
        print("  -> /health passed.")

    # 3. Test Starting Server (Inference Engine)
    print("[3] Testing /api/server/start...")
    req = urllib.request.Request(f"http://{HOST}:{PORT}/api/server/start", method="POST")
    with urllib.request.urlopen(req, timeout=25) as resp:
        data = json.loads(resp.read().decode())
        assert data["success"] is True
        print("  -> Engine started successfully:", data["status"])

    time.sleep(2)

    # 4. Test Server Status Telemetry
    print("[4] Testing /api/server/status...")
    req = urllib.request.Request(f"http://{HOST}:{PORT}/api/server/status")
    with urllib.request.urlopen(req, timeout=5) as resp:
        status_data = json.loads(resp.read().decode())
        assert status_data["status"] == "ONLINE"
        assert status_data["engine_memory_mb"] > 0
        print(f"  -> Server is ONLINE. Engine RAM RSS: {status_data['engine_memory_mb']} MB, CPU: {status_data['engine_cpu_percent']}%")

    # 5. Test OpenAI Models List with Authentication
    print("[5] Testing GET /v1/models...")
    req = urllib.request.Request(
        f"http://{HOST}:{PORT}/v1/models",
        headers={"Authorization": f"Bearer {raw_key}"}
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        models_data = json.loads(resp.read().decode())
        assert resp.status == 200
        assert "data" in models_data
        print(f"  -> Found {len(models_data['data'])} models.")

    # 6. Test Real OpenAI Chat Completion
    print("[6] Testing POST /v1/chat/completions (Real Local AI Inference)...")
    payload = json.dumps({
        "model": "local-ai",
        "messages": [
            {"role": "user", "content": "What is 2+2? Answer in one word."}
        ],
        "max_tokens": 15
    }).encode()
    req = urllib.request.Request(
        f"http://{HOST}:{PORT}/v1/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {raw_key}"
        }
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        comp_data = json.loads(resp.read().decode())
        content = comp_data["choices"][0]["message"]["content"]
        assert len(content.strip()) > 0
        print(f"  -> AI Generated Response: '{content.strip()}'")

    # 7. Test Authentication Rejection with Invalid Key
    print("[7] Testing Unauthorized request rejection...")
    req_bad = urllib.request.Request(
        f"http://{HOST}:{PORT}/v1/models",
        headers={"Authorization": "Bearer sk-local-fakekey"}
    )
    try:
        urllib.request.urlopen(req_bad, timeout=5)
        assert False, "Should have failed with 401"
    except urllib.error.HTTPError as err:
        assert err.code == 401
        print("  -> Successfully rejected invalid API key (401).")

    # 8. Test Stopping Server (Freeing Memory)
    print("[8] Testing /api/server/stop...")
    req_stop = urllib.request.Request(f"http://{HOST}:{PORT}/api/server/stop", method="POST")
    with urllib.request.urlopen(req_stop, timeout=10) as resp:
        stop_data = json.loads(resp.read().decode())
        assert stop_data["success"] is True
        print("  -> Engine stopped. Status:", stop_data["status"])

    print("\n==========================================")
    print("ALL END-TO-END SERVER TESTS PASSED!")
    print("==========================================")

if __name__ == "__main__":
    server_t = threading.Thread(target=run_server, daemon=True)
    server_t.start()
    time.sleep(2)
    try:
        run_tests()
    finally:
        engine.stop_engine()
