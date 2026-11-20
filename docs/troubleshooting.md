# Troubleshooting & Frequently Asked Questions

**Author:** Nadeem  
**Application:** Noora AI LAN Server

---

## 1. Common Issues & Solutions

### A. HTTP 401 Unauthorized ("Invalid or revoked API key")
- **Cause:** The client sent a truncated key prefix (e.g. `sk-local-243...5d2b`) instead of the full secret key, or missed the `Authorization` header.
- **Solution:** In the desktop dashboard, copy the full working API key displayed in the **Active Working Key** banner:
  ```
  sk-local-noora-default-lan-key
  ```
  Ensure your HTTP header is formatted as:
  ```http
  Authorization: Bearer sk-local-noora-default-lan-key
  ```

---

### B. Client Times Out While Waiting for Response
- **Cause:** Non-streaming inference requests wait for the entire prompt and generation to finish. If client software has a short timeout (e.g., 5 seconds), it drops the connection.
- **Solution:**
  1. Enable streaming (`"stream": true`). Tokens start appearing within ~120ms.
  2. Increase client timeout to 60-120 seconds for long generative tasks.
  3. Verify that CPU threads in Settings match your physical cores (e.g. 4 threads).

---

### C. Other Devices Cannot Connect ("Connection Refused" or "Host Unreachable")
- **Cause:** Windows Firewall is blocking inbound connections on port 8080, or the laptop and client are on different Wi-Fi subnets (e.g. Guest Wi-Fi vs Private Wi-Fi).
- **Solution:**
  1. Open the **Settings** tab in Noora AI and click **Add Firewall Rule**.
  2. Verify that both devices are connected to the same Wi-Fi router.
  3. Ensure the laptop is assigned a private IPv4 address (e.g. `192.168.x.x`).

---

### D. "Critically Low System Memory" Alert
- **Cause:** The laptop has less than 450 MB of free physical RAM.
- **Solution:** Close high-memory browser tabs or applications on the host laptop. Noora AI will automatically permit loading once system RAM frees up.

---

## 2. Diagnostics Commands

Test server reachability directly from PowerShell:
```powershell
# Test Health Endpoint
Invoke-RestMethod -Uri "http://localhost:8080/health"

# Test Chat Inference
$headers = @{ "Authorization" = "Bearer sk-local-noora-default-lan-key"; "Content-Type" = "application/json" }
$body = '{"model":"local-ai","messages":[{"role":"user","content":"ping"}]}'
Invoke-RestMethod -Uri "http://localhost:8080/v1/chat/completions" -Method POST -Headers $headers -Body $body
```
