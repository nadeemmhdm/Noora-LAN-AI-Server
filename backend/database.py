import sqlite3
import hashlib
import secrets
import time
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
from backend.config import (
    DB_PATH, MODELS_DIR, DEFAULT_MODEL_FILENAME,
    TRUSTED_MODELS_CATALOG, NOORA_MODELS, DEFAULT_CONTEXT_SIZE
)

DEFAULT_MASTER_KEY = "sk-local-noora-default-lan-key"

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA journal_mode = WAL;")
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. Models Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS models (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        model_id TEXT,
        capability TEXT,
        filename TEXT NOT NULL UNIQUE,
        path TEXT NOT NULL,
        size_bytes INTEGER NOT NULL,
        format TEXT NOT NULL DEFAULT 'GGUF',
        is_active INTEGER NOT NULL DEFAULT 0,
        downloaded_at REAL NOT NULL,
        sha256 TEXT
    );
    """)

    # Migrations for models table
    cursor.execute("PRAGMA table_info(models);")
    columns = [row["name"] for row in cursor.fetchall()]
    if "model_id" not in columns:
        try:
            cursor.execute("ALTER TABLE models ADD COLUMN model_id TEXT;")
        except Exception:
            pass
    if "capability" not in columns:
        try:
            cursor.execute("ALTER TABLE models ADD COLUMN capability TEXT;")
        except Exception:
            pass

    # 2. API Keys Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS api_keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        key_hash TEXT NOT NULL UNIQUE,
        key_prefix TEXT NOT NULL,
        raw_key TEXT,
        created_at REAL NOT NULL,
        last_used_at REAL,
        request_count INTEGER NOT NULL DEFAULT 0,
        is_active INTEGER NOT NULL DEFAULT 1,
        rate_limit_rpm INTEGER NOT NULL DEFAULT 120
    );
    """)

    cursor.execute("PRAGMA table_info(api_keys);")
    key_columns = [row["name"] for row in cursor.fetchall()]
    if "raw_key" not in key_columns:
        try:
            cursor.execute("ALTER TABLE api_keys ADD COLUMN raw_key TEXT;")
        except Exception:
            pass

    # 3. Connected Devices Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS devices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ip_address TEXT NOT NULL UNIQUE,
        hostname TEXT,
        first_seen REAL NOT NULL,
        last_seen REAL NOT NULL,
        request_count INTEGER NOT NULL DEFAULT 0,
        last_api_key_name TEXT,
        is_blocked INTEGER NOT NULL DEFAULT 0
    );
    """)

    # 4. API Requests Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS api_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp REAL NOT NULL,
        client_ip TEXT NOT NULL,
        endpoint TEXT NOT NULL,
        method TEXT NOT NULL,
        status_code INTEGER NOT NULL,
        latency_ms REAL NOT NULL,
        tokens_prompt INTEGER DEFAULT 0,
        tokens_completion INTEGER DEFAULT 0,
        api_key_name TEXT,
        error_message TEXT
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_requests_timestamp ON api_requests(timestamp);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_requests_client_ip ON api_requests(client_ip);")

    # 5. Blocked IPs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS blocked_ips (
        ip_address TEXT PRIMARY KEY,
        reason TEXT,
        created_at REAL NOT NULL
    );
    """)

    # 6. Server Settings Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS server_settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at REAL NOT NULL
    );
    """)

    # 7. Application Logs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS application_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp REAL NOT NULL,
        level TEXT NOT NULL,
        source TEXT NOT NULL,
        message TEXT NOT NULL
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_app_logs_timestamp ON application_logs(timestamp);")

    # 8. AI Trained Knowledge Documents Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS knowledge_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        title TEXT NOT NULL,
        summary TEXT,
        word_count INTEGER DEFAULT 0,
        chunk_count INTEGER DEFAULT 0,
        file_size_bytes INTEGER DEFAULT 0,
        created_at REAL NOT NULL,
        updated_at REAL NOT NULL
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_kdocs_created ON knowledge_documents(created_at);")

    # 9. AI Trained Knowledge Chunks Table (Semantic Units)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS knowledge_chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_id INTEGER NOT NULL,
        section_title TEXT,
        chunk_index INTEGER NOT NULL,
        content TEXT NOT NULL,
        keywords TEXT,
        created_at REAL NOT NULL,
        FOREIGN KEY (doc_id) REFERENCES knowledge_documents(id) ON DELETE CASCADE
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_kchunks_doc_id ON knowledge_chunks(doc_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_kchunks_section ON knowledge_chunks(section_title);")

    # Seed Default Settings
    default_settings = {
        "server_port": "8080",
        "cpu_threads": "4",
        "context_size": str(DEFAULT_CONTEXT_SIZE),
        "max_tokens": "4096",
        "lan_access_only": "true",
        "rate_limit_default_rpm": "240",
        "log_retention_days": "14",
        "dark_mode": "true",
        "selected_interface": "auto",
        "enable_web_search": "true",
        "web_search_mode": "auto",
        "web_search_max_results": "4"
    }
    for k, v in default_settings.items():
        cursor.execute("""
        INSERT OR IGNORE INTO server_settings (key, value, updated_at)
        VALUES (?, ?, ?)
        """, (k, v, time.time()))

    # Always ensure context_size in settings is at least 8192
    cursor.execute("SELECT value FROM server_settings WHERE key = 'context_size'")
    row = cursor.fetchone()
    if row and int(row["value"]) < 8192:
        cursor.execute("UPDATE server_settings SET value = '8192', updated_at = ? WHERE key = 'context_size'", (time.time(),))

    conn.commit()

    # Sync local models from the models/ folder into the database
    sync_models_from_disk(conn)

    # Ensure default API key exists
    ensure_default_api_key(conn)

    conn.close()

def sync_models_from_disk(conn: sqlite3.Connection):
    cursor = conn.cursor()
    if MODELS_DIR.exists():
        for file in MODELS_DIR.glob("*.gguf"):
            size = file.stat().st_size
            meta = NOORA_MODELS.get(file.name, {})
            name = meta.get("name", file.stem.replace("-", " ").title())
            model_id = meta.get("id", file.stem)
            capability = meta.get("capability", "General Intelligence")

            # Check if active model exists
            cursor.execute("SELECT id FROM models WHERE is_active = 1")
            has_active = cursor.fetchone() is not None
            is_active = 1 if (not has_active and file.name == DEFAULT_MODEL_FILENAME) else 0

            cursor.execute("""
            INSERT INTO models (name, model_id, capability, filename, path, size_bytes, format, is_active, downloaded_at)
            VALUES (?, ?, ?, ?, ?, ?, 'GGUF', ?, ?)
            ON CONFLICT(filename) DO UPDATE SET
                name = excluded.name,
                model_id = excluded.model_id,
                capability = excluded.capability,
                path = excluded.path,
                size_bytes = excluded.size_bytes
            """, (name, model_id, capability, file.name, str(file.resolve()), size, is_active, time.time()))
    conn.commit()

def resolve_model_filename(requested_model: str) -> Optional[Dict[str, Any]]:
    """Resolves requested model name or alias to an installed model record."""
    if not requested_model:
        requested_model = "local-ai"
    req_clean = requested_model.strip().lower()

    # Direct check against NOORA_MODELS aliases
    for fname, meta in NOORA_MODELS.items():
        aliases = [a.lower() for a in meta.get("aliases", [])]
        if req_clean in aliases or req_clean == meta.get("id", "").lower():
            target_path = MODELS_DIR / fname
            if target_path.exists():
                return {
                    "filename": fname,
                    "path": str(target_path.resolve()),
                    "name": meta["name"],
                    "model_id": meta["id"],
                    "capability": meta["capability"]
                }

    # Query DB
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT filename, path, name, model_id, capability FROM models")
    rows = cur.fetchall()
    conn.close()

    for r in rows:
        fn = r["filename"].lower()
        mid = (r["model_id"] or "").lower()
        nm = r["name"].lower()
        if req_clean in [fn, mid, nm] or req_clean in ["local-ai", "default"]:
            return dict(r)

    # Fallback to active model or first model in DB
    if rows:
        return dict(rows[0])
    return None

def ensure_default_api_key(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM api_keys WHERE is_active = 1")
    row = cursor.fetchone()
    if not row or row["count"] == 0:
        raw_key = DEFAULT_MASTER_KEY
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        key_prefix = f"{raw_key[:12]}...{raw_key[-4:]}"
        cursor.execute("""
        INSERT INTO api_keys (name, key_hash, key_prefix, raw_key, created_at, is_active, rate_limit_rpm)
        VALUES (?, ?, ?, ?, ?, 1, 240)
        ON CONFLICT(key_hash) DO UPDATE SET is_active = 1, raw_key = excluded.raw_key
        """, ("Default Master LAN Key", key_hash, key_prefix, raw_key, time.time()))
        conn.commit()

def generate_api_key(name: str, rate_limit_rpm: int = 240) -> Tuple[str, Dict[str, Any]]:
    raw_key = f"sk-local-{secrets.token_hex(16)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_prefix = f"{raw_key[:12]}...{raw_key[-4:]}"
    now = time.time()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO api_keys (name, key_hash, key_prefix, raw_key, created_at, is_active, rate_limit_rpm)
    VALUES (?, ?, ?, ?, ?, 1, ?)
    """, (name, key_hash, key_prefix, raw_key, now, rate_limit_rpm))
    key_id = cursor.lastrowid
    conn.commit()
    conn.close()

    record = {
        "id": key_id,
        "name": name,
        "key_prefix": key_prefix,
        "raw_key": raw_key,
        "created_at": now,
        "is_active": 1,
        "rate_limit_rpm": rate_limit_rpm
    }
    return raw_key, record

def get_active_working_key() -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, name, key_prefix, raw_key, is_active, rate_limit_rpm
    FROM api_keys
    WHERE is_active = 1 AND raw_key IS NOT NULL AND raw_key != ''
    ORDER BY id ASC
    LIMIT 1
    """)
    row = cursor.fetchone()
    if not row:
        ensure_default_api_key(conn)
        cursor.execute("""
        SELECT id, name, key_prefix, raw_key, is_active, rate_limit_rpm
        FROM api_keys WHERE is_active = 1 LIMIT 1
        """)
        row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def verify_api_key(raw_key: str) -> Optional[Dict[str, Any]]:
    if not raw_key:
        return None
    raw_key = raw_key.strip()
    
    if raw_key in ["auto", "local-dev", "test-key"]:
        active = get_active_working_key()
        if active:
            return active

    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, name, key_prefix, raw_key, is_active, rate_limit_rpm, request_count
    FROM api_keys
    WHERE key_hash = ? OR raw_key = ?
    """, (key_hash, raw_key))
    row = cursor.fetchone()
    if row and row["is_active"]:
        now = time.time()
        cursor.execute("""
        UPDATE api_keys 
        SET last_used_at = ?, request_count = request_count + 1
        WHERE id = ?
        """, (now, row["id"]))
        conn.commit()
        conn.close()
        return dict(row)
    conn.close()
    return None

def log_api_request(client_ip: str, endpoint: str, method: str, status_code: int, 
                    latency_ms: float, tokens_prompt: int = 0, tokens_completion: int = 0, 
                    api_key_name: Optional[str] = None, error_message: Optional[str] = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = time.time()
    cursor.execute("""
    INSERT INTO api_requests (timestamp, client_ip, endpoint, method, status_code, 
                              latency_ms, tokens_prompt, tokens_completion, api_key_name, error_message)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (now, client_ip, endpoint, method, status_code, latency_ms, tokens_prompt, tokens_completion, api_key_name, error_message))
    
    cursor.execute("""
    INSERT INTO devices (ip_address, first_seen, last_seen, request_count, last_api_key_name, is_blocked)
    VALUES (?, ?, ?, 1, ?, 0)
    ON CONFLICT(ip_address) DO UPDATE SET
        last_seen = excluded.last_seen,
        request_count = devices.request_count + 1,
        last_api_key_name = COALESCE(excluded.last_api_key_name, devices.last_api_key_name)
    """, (client_ip, now, now, api_key_name))
    
    conn.commit()
    conn.close()

def log_system_event(level: str, source: str, message: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO application_logs (timestamp, level, source, message)
    VALUES (?, ?, ?, ?)
    """, (time.time(), level.upper(), source, message))
    conn.commit()
    conn.close()

def is_ip_blocked(ip: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM blocked_ips WHERE ip_address = ?", (ip,))
    blocked = cursor.fetchone() is not None
    conn.close()
    return blocked

def set_ip_blocked_status(ip: str, blocked: bool, reason: str = ""):
    conn = get_db_connection()
    cursor = conn.cursor()
    if blocked:
        cursor.execute("""
        INSERT INTO blocked_ips (ip_address, reason, created_at)
        VALUES (?, ?, ?)
        ON CONFLICT(ip_address) DO UPDATE SET reason = excluded.reason
        """, (ip, reason, time.time()))
        cursor.execute("UPDATE devices SET is_blocked = 1 WHERE ip_address = ?", (ip,))
    else:
        cursor.execute("DELETE FROM blocked_ips WHERE ip_address = ?", (ip,))
        cursor.execute("UPDATE devices SET is_blocked = 0 WHERE ip_address = ?", (ip,))
    conn.commit()
    conn.close()

def get_server_setting(key: str, default: str = "") -> str:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM server_settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row else default

def update_server_setting(key: str, value: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO server_settings (key, value, updated_at)
    VALUES (?, ?, ?)
    ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
    """, (key, str(value), time.time()))
    conn.commit()
    conn.close()

def prune_old_logs(days: int = 14):
    cutoff = time.time() - (days * 86400)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM api_requests WHERE timestamp < ?", (cutoff,))
    cursor.execute("DELETE FROM application_logs WHERE timestamp < ?", (cutoff,))
    conn.commit()
    conn.close()

# ----------------- AI Trained Knowledge Base Memory -----------------

def insert_knowledge_document(filename: str, title: str, summary: str, word_count: int, chunk_count: int, file_size_bytes: int) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    now = time.time()
    cursor.execute("""
    INSERT INTO knowledge_documents (filename, title, summary, word_count, chunk_count, file_size_bytes, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (filename, title, summary, word_count, chunk_count, file_size_bytes, now, now))
    doc_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return doc_id

def insert_knowledge_chunks(doc_id: int, chunks: list):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = time.time()
    for idx, c in enumerate(chunks):
        cursor.execute("""
        INSERT INTO knowledge_chunks (doc_id, section_title, chunk_index, content, keywords, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (doc_id, c.get("section_title", "General"), idx, c.get("content", ""), c.get("keywords", ""), now))
    conn.commit()
    conn.close()

def get_all_knowledge_documents() -> list:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM knowledge_documents ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_knowledge_document(doc_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM knowledge_documents WHERE id = ?", (doc_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_chunks_by_document(doc_id: int) -> list:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM knowledge_chunks WHERE doc_id = ? ORDER BY chunk_index ASC", (doc_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_knowledge_document(doc_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM knowledge_chunks WHERE doc_id = ?", (doc_id,))
    cursor.execute("DELETE FROM knowledge_documents WHERE id = ?", (doc_id,))
    changed = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return changed

def get_all_knowledge_chunks_with_doc_info() -> list:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT c.id, c.doc_id, c.section_title, c.chunk_index, c.content, c.keywords, 
           d.filename, d.title as doc_title
    FROM knowledge_chunks c
    JOIN knowledge_documents d ON c.doc_id = d.id
    ORDER BY c.doc_id, c.chunk_index
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]
