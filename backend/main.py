import sys
import os
import time
import argparse
import threading
import uvicorn
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import (
    APP_NAME, DEFAULT_GATEWAY_PORT, DEVELOPER, VERSION, STATIC_DIR
)
from backend.database import init_db, get_server_setting
from backend.inference import engine
from backend.network_utils import get_primary_lan_ip

def run_api_server(host: str, port: int):
    from backend.gateway import app
    uvicorn.run(app, host=host, port=port, log_level="warning")

def main():
    parser = argparse.ArgumentParser(description=f"{APP_NAME} - Developed by {DEVELOPER}")
    parser.add_argument("--host", default="0.0.0.0", help="Host interface to bind (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=None, help=f"Port to bind (default: {DEFAULT_GATEWAY_PORT})")
    parser.add_argument("--headless", action="store_true", help="Run without opening desktop WebView window")
    args = parser.parse_args()

    init_db()

    port = args.port or int(get_server_setting("server_port", str(DEFAULT_GATEWAY_PORT)))
    host = args.host
    lan_ip = get_primary_lan_ip()

    print(f"============================================================")
    print(f"  {APP_NAME} (v{VERSION})")
    print(f"  Developed by {DEVELOPER}")
    print(f"============================================================")
    print(f"  [+] LAN Gateway listening on: http://{lan_ip}:{port}")
    print(f"  [+] API Base URL:           http://{lan_ip}:{port}/v1")
    print(f"  [+] OpenAI Models Endpoint: http://{lan_ip}:{port}/v1/models")
    print(f"  [+] Local Dashboard:        http://127.0.0.1:{port}")
    print(f"============================================================")

    # Start FastAPI backend in a background daemon thread
    server_thread = threading.Thread(target=run_api_server, args=(host, port), daemon=True)
    server_thread.start()

    time.sleep(1.0)

    if args.headless:
        print("[*] Running in headless server mode. Press Ctrl+C to terminate.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[*] Shutting down Noora AI Server...")
            engine.stop_engine()
            print("[+] Done.")
            sys.exit(0)
    else:
        # Run desktop GUI with pywebview (Edge WebView2)
        try:
            import webview
            window = webview.create_window(
                title=f"{APP_NAME} - Developed by {DEVELOPER}",
                url=f"http://127.0.0.1:{port}",
                width=1280,
                height=840,
                min_size=(1024, 700),
                background_color="#0B0F19"
            )

            def on_closed():
                print("[*] Application closed. Stopping AI engine and freeing resources...")
                engine.stop_engine()

            window.events.closed += on_closed
            webview.start()

        except Exception as e:
            print(f"[*] Native GUI window error: {e}. Falling back to console server mode.")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                engine.stop_engine()

if __name__ == "__main__":
    main()
