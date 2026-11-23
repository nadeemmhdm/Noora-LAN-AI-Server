# Noora AI API Reference Manual

**Author:** Nadeem  
**Base URL Format:** `http://<LAN_IP>:8080/v1`  
**Authentication Scheme:** `Authorization: Bearer <API_KEY>`

---

## 1. Authentication

All requests to `/v1/*` endpoints require a Bearer token in the HTTP Authorization header:

```http
Authorization: Bearer sk-local-xxxxxxxxxxxxxxxx
```

API keys can be generated from the **API Keys** tab in the desktop dashboard or obtained using the default master key (`sk-local-noora-default-lan-key`).

---

## 2. OpenAI-Compatible Endpoints

### `GET /v1/models`
Returns a list of all currently imported and active GGUF models.

**Request:**
```bash
curl -X GET "http://192.168.1.100:8080/v1/models" \
  -H "Authorization: Bearer sk-local-noora-default-lan-key"
```

**Response (200 OK):**
```json
{
  "object": "list",
  "data": [
    {
      "id": "qwen2.5-0.5b-instruct-q4_k_m.gguf",
      "object": "model",
      "created": 1795020000,
      "owned_by": "local",
      "permission": []
    },
    {
      "id": "local-ai",
      "object": "model",
      "created": 1795020000,
      "owned_by": "local",
      "permission": []
    }
  ]
}
```

---

### `POST /v1/chat/completions`
Generates a chat completion for a list of messages. Supports both synchronous JSON and streaming SSE (`text/event-stream`).

**Request Parameters:**
| Parameter | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `model` | string | No | `"local-ai"` | Target model alias or filename (`N.1 Faster`, `N.1 Pro`, `N.1 Core`) |
| `messages` | array | Yes | - | Array of message objects (`role`, `content`) |
| `web_search` | boolean | No | `null` | Optional explicit toggle for online web search. If `null`, uses server setting (`auto`). Only triggers when system is online. |
| `temperature` | float | No | `0.7` | Sampling temperature between 0.0 and 1.5 |
| `top_p` | float | No | `0.95` | Nucleus sampling probability threshold |
| `max_tokens` | integer | No | `1024` | Maximum number of tokens to generate |
| `stream` | boolean | No | `false` | When true, returns tokens via Server-Sent Events |

**Synchronous Request Example:**
```bash
curl -X POST "http://192.168.1.100:8080/v1/chat/completions" \
  -H "Authorization: Bearer sk-local-noora-default-lan-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "local-ai",
    "messages": [
      {"role": "user", "content": "What are 3 benefits of local AI?"}
    ],
    "temperature": 0.7,
    "max_tokens": 150
  }'
```

**Synchronous Response (200 OK):**
```json
{
  "id": "chatcmpl-local-12345",
  "object": "chat.completion",
  "created": 1795020100,
  "model": "local-ai",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Three key benefits of local AI are: 1. Complete Privacy: Your data never leaves your network. 2. Zero Recurring Costs: No subscription or API token fees. 3. Offline Reliability: Functions without an active internet connection."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 18,
    "completion_tokens": 46,
    "total_tokens": 64
  }
}
```

**Streaming Request Example (`stream: true`):**
```bash
curl -N -X POST "http://192.168.1.100:8080/v1/chat/completions" \
  -H "Authorization: Bearer sk-local-noora-default-lan-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "local-ai",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": true
  }'
```

---

### `POST /v1/completions`
Generates raw text completions from a prompt string.

**Request:**
```json
{
  "prompt": "The future of edge computing is",
  "max_tokens": 60,
  "temperature": 0.7
}
```

---

## 3. Server Health & Telemetry Endpoints

### `GET /health`
Public health status endpoint.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "app_name": "Noora AI - LAN AI Server",
  "ai_name": "Noora",
  "developer": "Nadeem",
  "version": "1.0.0",
  "server_status": "ONLINE",
  "active_model": "Qwen 2.5 0.5B Instruct",
  "lan_ip": "192.168.1.100",
  "api_port": 8080,
  "base_url": "http://192.168.1.100:8080/v1",
  "hardware": {
    "cpu_model": "Intel Core i5 / AMD64",
    "physical_cores": 4,
    "logical_cores": 8,
    "recommended_threads": 4
  }
}
```

### `GET /api/server/status`
Returns real-time telemetry including CPU load, RAM allocation, engine memory RSS, active clients, request statistics, and internet online connectivity status.

### `GET /api/network/connectivity`
Checks whether the host machine has active external internet connectivity and returns latency and web search configuration.

**Response (200 OK):**
```json
{
  "online": true,
  "latency_ms": 68.4,
  "web_search_enabled": true,
  "web_search_mode": "auto"
}
```

### `POST /api/web_search`
Direct endpoint to perform live zero-API-key web queries without passing through LLM inference.

**Request Body:**
```json
{
  "query": "latest release notes python",
  "max_results": 3
}
```

**Response (200 OK):**
```json
{
  "query": "latest release notes python",
  "total_results": 3,
  "results": [
    {
      "title": "Python Release Python 3.13.2",
      "url": "https://www.python.org/downloads/release/python-3132/",
      "snippet": "Python 3.13.2 is the newest security bugfix release of the Python 3.13 series.",
      "domain": "python.org"
    }
  ],
  "latency_ms": 210.5
}
```

---

## 4. HTTP Status Code Summary

| Status Code | Reason | Resolution |
| :--- | :--- | :--- |
| `200 OK` | Request succeeded. | - |
| `401 Unauthorized` | Missing or invalid API key. | Pass `Authorization: Bearer <API_KEY>` with a valid key. |
| `403 Forbidden` | Client IP is blocked or outside LAN. | Verify client is connected to same Wi-Fi subnet. |
| `429 Too Many Requests` | Rate limit exceeded. | Adjust key RPM limit in the API Keys tab. |
| `503 Service Unavailable` | Engine is offline. | Click Start Server on the Dashboard. |
