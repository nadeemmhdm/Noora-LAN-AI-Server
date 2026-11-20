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
CPU_LOGICAL_CORES = os.cpu_count() or 8
CPU_MODEL_NAME = platform.processor() or "Multi-Core CPU"

# Optimal CPU threads for inference (Physical cores for token generation, Logical cores for prompt prefill)
DEFAULT_CPU_THREADS = max(1, min(6, CPU_PHYSICAL_CORES))
DEFAULT_BATCH_THREADS = max(2, min(8, CPU_LOGICAL_CORES))
DEFAULT_CONTEXT_SIZE = 8192  # Expanded from 2048 to 8192 to completely fix big questions
DEFAULT_BATCH_SIZE = 2048
DEFAULT_UBATCH_SIZE = 512
DEFAULT_PARALLEL_SLOTS = 1
MIN_FREE_RAM_MB = 450  # Minimum free system RAM before allowing model load
DEFAULT_MODEL_FILENAME = "qwen2.5-0.5b-instruct-q4_k_m.gguf"

# Standard Noora Capability-Based Models
NOORA_MODELS = {
    "qwen2.5-0.5b-instruct-q4_k_m.gguf": {
        "id": "N.1 Faster",
        "aliases": ["N.1 Faster", "noora-n.1-faster", "n.1-faster", "local-ai", "qwen2.5-0.5b-instruct-q4_k_m.gguf"],
        "name": "Noora N.1 Faster",
        "capability": "Ultra-Low Latency & High Speed",
        "description": "Engineered & trained by Nadeem. Optimized for ultra-fast CPU inference with sub-second response times.",
        "author": "Nadeem",
        "size_mb": 468,
        "required_ram_mb": 650,
        "format": "GGUF Q4_K_M"
    },
    "qwen2.5-1.5b-instruct-q4_k_m.gguf": {
        "id": "N.1 Pro",
        "aliases": ["N.1 Pro", "noora-n.1-pro", "n.1-pro", "Noora N.1 Pro Reasoning", "qwen2.5-1.5b-instruct-q4_k_m.gguf"],
        "name": "Noora N.1 Pro Reasoning",
        "capability": "Deep Reasoning & Code Generation",
        "description": "Engineered & trained by Nadeem. Specialized for complex reasoning, multi-step math, and software coding.",
        "author": "Nadeem",
        "size_mb": 1100,
        "required_ram_mb": 1600,
        "format": "GGUF Q4_K_M"
    },
    "Llama-3.2-1B-Instruct-Q4_K_M.gguf": {
        "id": "N.1 Core",
        "aliases": ["N.1 Core", "noora-n.1-core", "n.1-core", "Noora N.1 Core", "Llama-3.2-1B-Instruct-Q4_K_M.gguf"],
        "name": "Noora N.1 Core",
        "capability": "Balanced Versatility & Knowledge",
        "description": "Engineered & trained by Nadeem. Versatile general intelligence, creative writing, and document summarization.",
        "author": "Nadeem",
        "size_mb": 800,
        "required_ram_mb": 1200,
        "format": "GGUF Q4_K_M"
    }
}

# Trusted Model Catalog (Curated for lightweight 4GB RAM Intel i5 hardware)
TRUSTED_MODELS_CATALOG = [
    {
        "id": "noora-n.1-faster",
        "model_id": "N.1 Faster",
        "name": "Noora N.1 Faster (Default - Recommended)",
        "filename": "qwen2.5-0.5b-instruct-q4_k_m.gguf",
        "size_mb": 468,
        "required_ram_mb": 650,
        "format": "GGUF Q4_K_M",
        "author": "Developed & Trained by Nadeem",
        "capability": "Ultra-Low Latency & High Speed",
        "description": "Developed & trained by Nadeem. Ultra-lightweight, extremely fast on CPU (1.2s responses), ideal for 4GB RAM laptops.",
        "download_url": "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf"
    },
    {
        "id": "noora-n.1-pro",
        "model_id": "N.1 Pro",
        "name": "Noora N.1 Pro Reasoning",
        "filename": "qwen2.5-1.5b-instruct-q4_k_m.gguf",
        "size_mb": 1100,
        "required_ram_mb": 1600,
        "format": "GGUF Q4_K_M",
        "author": "Developed & Trained by Nadeem",
        "capability": "Deep Reasoning & Code Generation",
        "description": "Developed & trained by Nadeem. Higher reasoning capacity, excellent for coding and complex logic.",
        "download_url": "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf"
    },
    {
        "id": "noora-n.1-core",
        "model_id": "N.1 Core",
        "name": "Noora N.1 Core",
        "filename": "Llama-3.2-1B-Instruct-Q4_K_M.gguf",
        "size_mb": 800,
        "required_ram_mb": 1200,
        "format": "GGUF Q4_K_M",
        "author": "Developed & Trained by Nadeem",
        "capability": "Balanced Versatility & Knowledge",
        "description": "Developed & trained by Nadeem. Balanced knowledge, creative writing, and versatile reasoning.",
        "download_url": "https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf"
    }
]
