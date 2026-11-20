# Hardware Optimization & Low-Footprint Tuning

**Author:** Nadeem  
**Target Hardware:** Intel Core i5 CPU, 4GB System RAM, No Dedicated GPU

---

## 1. Design Constraints & Objectives

Running local LLM inference on everyday consumer hardware (Intel Core i5, 4GB RAM) requires strict resource management to prevent system memory lockups, page file thrashing, and high latency.

| Resource | Target Threshold | Noora AI Tuning |
| :--- | :--- | :--- |
| **System RAM** | 4GB Total | Engine footprint restricted to < 600MB RSS |
| **CPU Utilization** | Dual/Quad Core | Thread allocation pinned to physical core count |
| **Context Memory** | 2048 Tokens | Key-Value cache limited to ~180MB RAM |
| **Storage** | Portable | Quantized GGUF 4-bit (Q4_K_M) models |

---

## 2. Automated Processor Detection

Noora AI inspects the host hardware on startup:
```python
CPU_PHYSICAL_CORES = psutil.cpu_count(logical=False) or 4
CPU_LOGICAL_CORES = os.cpu_count() or 4
DEFAULT_CPU_THREADS = max(1, min(6, CPU_PHYSICAL_CORES))
```

### Why Physical Cores Matter
Hyperthreading (logical cores) can introduce cache-thrashing during dense matrix multiplication in transformer inference. Setting `--threads` equal to the number of **physical cores** yields the lowest latency per token.

---

## 3. Pre-Flight RAM Validation

Before launching `llama-server.exe`, Noora AI calculates:
1. `required_free_ram = file_size_mb + 200`
2. `available_ram = psutil.virtual_memory().available / (1024 * 1024)`

If `available_ram < 450 MB` or `available_ram < required_free_ram * 0.7`, model loading is safely aborted with an informative alert, preventing Windows from becoming unresponsive.

---

## 4. Optimal CLI Engine Arguments

```bash
llama-server.exe \
  -m models/qwen2.5-0.5b-instruct-q4_k_m.gguf \
  --host 127.0.0.1 \
  --port 8081 \
  -t 4 \
  -tb 4 \
  -c 2048 \
  -b 512 \
  -ub 256 \
  -np 1 \
  --log-disable
```

- `-t 4`: 4 threads for token generation.
- `-tb 4`: 4 threads for prompt evaluation (batch phase).
- `-b 512 -ub 256`: Small batch size ensures immediate first-token response (<150ms).
- `-np 1`: Single parallel slot prevents multiple context allocations in low-RAM environments.
- `-c 2048`: 2048 context window balances sufficient memory for documents while keeping KV cache minimal.
