import os
import sys
import platform
import psutil
from pathlib import Path

# Base Paths
APP_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = APP_ROOT / "data"
MODELS_DIR = APP_ROOT / "models"
ENGINE_DIR = APP_ROOT / "engine"
STATIC_DIR = APP_ROOT / "frontend" / "dist"

# Ensure essential directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)
ENGINE_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "noora_ai.db"
LLAMA_SERVER_EXE = ENGINE_DIR / "llama-server.exe"

# Branding & Metadata
APP_NAME = "Noora AI - LAN AI Server"
AI_NAME = "Noora"
DEVELOPER = "Nadeem"
VERSION = "1.0.0"

# Default Network Settings
DEFAULT_GATEWAY_PORT = 8080
DEFAULT_INFERENCE_PORT = 8081
LOOPBACK_HOST = "127.0.0.1"

# Hardware Auto-Detection
CPU_PHYSICAL_CORES = psutil.cpu_count(logical=False) or 4
CPU_LOGICAL_CORES = os.cpu_count() or 4
CPU_MODEL_NAME = platform.processor() or "Multi-Core CPU"

# Optimal CPU threads for inference (Equal to physical cores avoids context switching overhead)
DEFAULT_CPU_THREADS = max(1, min(6, CPU_PHYSICAL_CORES))
DEFAULT_CONTEXT_SIZE = 2048
DEFAULT_PARALLEL_SLOTS = 1
MIN_FREE_RAM_MB = 450  # Minimum free system RAM before allowing model load
DEFAULT_MODEL_FILENAME = "qwen2.5-0.5b-instruct-q4_k_m.gguf"

# Trusted Model Catalog (Curated for lightweight 4GB RAM Intel i5 hardware)
TRUSTED_MODELS_CATALOG = [
    {
        "id": "qwen2.5-0.5b-instruct",
        "name": "Qwen 2.5 0.5B Instruct (Default - Recommended)",
        "filename": "qwen2.5-0.5b-instruct-q4_k_m.gguf",
        "size_mb": 468,
        "required_ram_mb": 650,
        "format": "GGUF Q4_K_M",
        "description": "Ultra-lightweight, extremely fast on CPU (1.2s responses), ideal for 4GB RAM laptops.",
        "download_url": "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf"
    },
    {
        "id": "qwen2.5-1.5b-instruct",
        "name": "Qwen 2.5 1.5B Instruct",
        "filename": "qwen2.5-1.5b-instruct-q4_k_m.gguf",
        "size_mb": 1100,
        "required_ram_mb": 1600,
        "format": "GGUF Q4_K_M",
        "description": "Higher reasoning capacity, excellent for coding and structured tasks.",
        "download_url": "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf"
    },
    {
        "id": "llama-3.2-1b-instruct",
        "name": "Llama 3.2 1B Instruct",
        "filename": "Llama-3.2-1B-Instruct-Q4_K_M.gguf",
        "size_mb": 800,
        "required_ram_mb": 1200,
        "format": "GGUF Q4_K_M",
        "description": "Meta's highly capable 1B model, balanced speed and knowledge.",
        "download_url": "https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf"
    }
]
