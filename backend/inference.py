import os
import sys
import time
import signal
import socket
import psutil
import subprocess
import threading
from typing import Optional, Dict, Any, Generator
from pathlib import Path
import httpx

from backend.config import (
    LLAMA_SERVER_EXE, DEFAULT_INFERENCE_PORT, LOOPBACK_HOST,
    MIN_FREE_RAM_MB, DEFAULT_CPU_THREADS, DEFAULT_BATCH_THREADS,
    DEFAULT_CONTEXT_SIZE, DEFAULT_BATCH_SIZE, DEFAULT_UBATCH_SIZE,
    DEFAULT_PARALLEL_SLOTS, AI_NAME, DEVELOPER,
    CPU_PHYSICAL_CORES, CPU_LOGICAL_CORES, CPU_MODEL_NAME, NOORA_MODELS
)
from backend.database import log_system_event, get_db_connection, resolve_model_filename

class LlamaEngineManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LlamaEngineManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.process: Optional[subprocess.Popen] = None
        self.status = "OFFLINE"  # OFFLINE, STARTING, ONLINE, STOPPING, ERROR
        self.active_model_path: Optional[str] = None
        self.active_model_name: Optional[str] = None
        self.active_model_id: Optional[str] = None
        self.port = DEFAULT_INFERENCE_PORT
        self.host = LOOPBACK_HOST
        self.error_message: Optional[str] = None
        self.started_at: Optional[float] = None
        self.lock = threading.Lock()
        self.stdout_thread = None
        self.stderr_thread = None
        self.recent_logs: list[str] = []
        self.threads_used = DEFAULT_CPU_THREADS
        self.batch_threads_used = DEFAULT_BATCH_THREADS
        self.context_size_used = DEFAULT_CONTEXT_SIZE

    def get_stats(self) -> Dict[str, Any]:
        memory_usage_mb = 0.0
        cpu_percent = 0.0
        uptime_sec = 0

        if self.process and self.process.poll() is None:
            try:
                p = psutil.Process(self.process.pid)
                memory_usage_mb = round(p.memory_info().rss / (1024 * 1024), 1)
                cpu_percent = round(p.cpu_percent(interval=None), 1)
            except Exception:
                pass
            if self.started_at:
                uptime_sec = int(time.time() - self.started_at)
        else:
            if self.status == "ONLINE":
                self.status = "OFFLINE"

        vm = psutil.virtual_memory()
        return {
            "status": self.status,
            "active_model": self.active_model_name or "Noora N.1 Faster",
            "active_model_id": self.active_model_id or "N.1 Faster",
            "active_model_path": self.active_model_path,
            "uptime_seconds": uptime_sec,
            "engine_memory_mb": memory_usage_mb,
            "engine_cpu_percent": cpu_percent,
            "system_ram_total_mb": round(vm.total / (1024 * 1024), 1),
            "system_ram_used_mb": round(vm.used / (1024 * 1024), 1),
            "system_ram_free_mb": round(vm.available / (1024 * 1024), 1),
            "system_ram_percent": vm.percent,
            "system_cpu_percent": psutil.cpu_percent(),
            "cpu_model": CPU_MODEL_NAME,
            "cpu_physical_cores": CPU_PHYSICAL_CORES,
            "cpu_logical_cores": CPU_LOGICAL_CORES,
            "threads_used": self.threads_used,
            "batch_threads_used": self.batch_threads_used,
            "context_size": self.context_size_used,
            "port": self.port,
            "host": self.host,
            "error_message": self.error_message
        }

    def check_ram_availability(self, model_file_path: Path) -> tuple[bool, str]:
        if not model_file_path.exists():
            return False, f"Model file not found: {model_file_path.name}"
        
        file_size_mb = model_file_path.stat().st_size / (1024 * 1024)
        required_free_ram = file_size_mb + 250
        available_ram = psutil.virtual_memory().available / (1024 * 1024)

        if available_ram < MIN_FREE_RAM_MB:
            return False, f"Critically low system memory: Only {available_ram:.0f} MB available (Minimum required: {MIN_FREE_RAM_MB} MB)."
        
        if available_ram < required_free_ram * 0.65:
            return False, f"Insufficient memory to safely load {model_file_path.name}. Need ~{required_free_ram:.0f} MB, but only {available_ram:.0f} MB is available."
        
        return True, "RAM check passed."

    def start_engine(self, model_path: Optional[str] = None, threads: Optional[int] = None, 
                     context_size: Optional[int] = None) -> tuple[bool, str]:
        with self.lock:
            # If target model is specified and already running with that model, return immediately
            if model_path and self.active_model_path == str(Path(model_path).resolve()) and self.process and self.process.poll() is None:
                return True, "Engine is already running requested model."

            # If running a different model, stop first
            if self.process and self.process.poll() is None:
                if model_path and self.active_model_path != str(Path(model_path).resolve()):
                    self._stop_internal()
                else:
                    return True, "Engine is already running."

            if not LLAMA_SERVER_EXE.exists():
                self.status = "ERROR"
                msg = f"llama-server executable missing at {LLAMA_SERVER_EXE}"
                self.error_message = msg
                log_system_event("ERROR", "INFERENCE", msg)
                return False, msg

            # Resolve model
            target_path = None
            if model_path:
                target_path = Path(model_path)
                meta = NOORA_MODELS.get(target_path.name, {})
                self.active_model_name = meta.get("name", target_path.stem.replace("-", " ").title())
                self.active_model_id = meta.get("id", target_path.stem)
            else:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("SELECT path, name, model_id, filename FROM models WHERE is_active = 1 LIMIT 1")
                row = cur.fetchone()
                if not row:
                    cur.execute("SELECT path, name, model_id, filename FROM models LIMIT 1")
                    row = cur.fetchone()
                conn.close()
                if row:
                    target_path = Path(row["path"])
                    meta = NOORA_MODELS.get(row["filename"], {})
                    self.active_model_name = meta.get("name", row["name"])
                    self.active_model_id = meta.get("id", row["model_id"] or "N.1 Faster")

            if not target_path or not target_path.exists():
                self.status = "ERROR"
                msg = "No valid GGUF model found. Please download or import a model first."
                self.error_message = msg
                return False, msg

            # RAM validation check
            can_load, ram_msg = self.check_ram_availability(target_path)
            if not can_load:
                self.status = "ERROR"
                self.error_message = ram_msg
                log_system_event("WARNING", "INFERENCE", f"RAM check failed: {ram_msg}")
                return False, ram_msg

            self.status = "STARTING"
            self.error_message = None
            self.active_model_path = str(target_path.resolve())

            # Configure optimal threads and context size
            self.threads_used = threads or DEFAULT_CPU_THREADS
            self.batch_threads_used = DEFAULT_BATCH_THREADS
            self.context_size_used = context_size or DEFAULT_CONTEXT_SIZE

            th = str(self.threads_used)
            tb = str(self.batch_threads_used)
            ctx = str(self.context_size_used)
            b = str(DEFAULT_BATCH_SIZE)
            ub = str(DEFAULT_UBATCH_SIZE)

            cmd = [
                str(LLAMA_SERVER_EXE.resolve()),
                "-m", str(target_path.resolve()),
                "--host", self.host,
                "--port", str(self.port),
                "-t", th,
                "-tb", tb,
                "-c", ctx,
                "-b", b,
                "-ub", ub,
                "-np", str(DEFAULT_PARALLEL_SLOTS),
                "--log-disable"
            ]

            log_system_event("INFO", "INFERENCE", f"Starting {self.active_model_name} (threads={th}, batch_threads={tb}, ctx={ctx})")

            try:
                creation_flags = 0
                if sys.platform == "win32":
                    creation_flags = subprocess.CREATE_NO_WINDOW

                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    creationflags=creation_flags
                )

                def stream_logs(pipe, label):
                    try:
                        for line in iter(pipe.readline, ''):
                            if line.strip():
                                self.recent_logs.append(f"[{label}] {line.strip()}")
                                if len(self.recent_logs) > 200:
                                    self.recent_logs.pop(0)
                    except Exception:
                        pass

                self.stdout_thread = threading.Thread(target=stream_logs, args=(self.process.stdout, "OUT"), daemon=True)
                self.stderr_thread = threading.Thread(target=stream_logs, args=(self.process.stderr, "ERR"), daemon=True)
                self.stdout_thread.start()
                self.stderr_thread.start()

            except Exception as e:
                self.status = "ERROR"
                self.error_message = f"Failed to spawn engine process: {str(e)}"
                log_system_event("ERROR", "INFERENCE", self.error_message)
                return False, self.error_message

        # Wait and verify engine health
        start_time = time.time()
        timeout = 30
        while time.time() - start_time < timeout:
            if self.process.poll() is not None:
                self.status = "ERROR"
                err_text = "\n".join(self.recent_logs[-5:]) if self.recent_logs else "Unknown startup error"
                self.error_message = f"Engine exited prematurely (code {self.process.returncode}): {err_text}"
                log_system_event("ERROR", "INFERENCE", self.error_message)
                return False, self.error_message

            try:
                with httpx.Client(timeout=1.0) as client:
                    resp = client.get(f"http://{self.host}:{self.port}/health")
                    if resp.status_code == 200:
                        self.status = "ONLINE"
                        self.started_at = time.time()
                        log_system_event("INFO", "INFERENCE", f"AI Engine is ONLINE with {self.active_model_name} on {self.host}:{self.port}")
                        return True, "AI Engine started successfully."
            except Exception:
                pass
            time.sleep(0.5)

        self.stop_engine()
        self.status = "ERROR"
        self.error_message = "Engine startup timed out."
        return False, "Engine startup timed out."

    def _stop_internal(self):
        if not self.process or self.process.poll() is not None:
            self.status = "OFFLINE"
            self.process = None
            return

        self.status = "STOPPING"
        try:
            pid = self.process.pid
            self.process.terminate()
            try:
                self.process.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                if sys.platform == "win32":
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], 
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    self.process.kill()
                self.process.wait(timeout=2.0)
        except Exception as e:
            pass
        self.process = None
        self.status = "OFFLINE"
        self.started_at = None

    def stop_engine(self) -> tuple[bool, str]:
        with self.lock:
            if not self.process or self.process.poll() is not None:
                self.status = "OFFLINE"
                self.process = None
                return True, "Engine is already offline."

            log_system_event("INFO", "INFERENCE", "Stopping AI Engine...")
            self._stop_internal()
            log_system_event("INFO", "INFERENCE", "AI Engine stopped. Model memory released.")
            return True, "Engine stopped successfully."

    def restart_engine(self, model_path: Optional[str] = None) -> tuple[bool, str]:
        self.stop_engine()
        time.sleep(1.0)
        return self.start_engine(model_path=model_path)

# Global engine manager instance
engine = LlamaEngineManager()
