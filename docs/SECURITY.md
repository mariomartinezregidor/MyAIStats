# Security Architecture & Financial Accuracy Guarantees

## 1. Local-First Network Isolation
- **Localhost Binding**: By default, the FastAPI backend binds exclusively to `127.0.0.1:8000` (`MYAISTATS_HOST=127.0.0.1`). It is not exposed to LAN or public interfaces unless explicitly overridden by the user.
- **Strict CORS**: Restricted to local Vite frontend origins (`http://localhost:5173`, `http://127.0.0.1:5173`).

## 2. Credential Encryption at Rest
- API keys are encrypted before being stored in the `credentials` SQLite table using **Fernet (`cryptography.fernet`)**, which provides `AES-128-CBC` encryption with `HMAC-SHA256` authentication.
- If `MYAISTATS_SECRET_KEY` is not set in `.env`, `CredentialVault` automatically generates a cryptographically strong 32-byte URL-safe base64 key in `./data/.secret.key` with `0600` (`rw-------`) file permissions.
- Raw API keys are **never** returned in any API response after submission, **never** stored in browser `localStorage`, and **never** printed in logs. Only a masked hint (e.g. `sk-pro...9876`) is shown in the UI.

## 3. Outbound SSRF Protection
- `SafeConnectorHttpClient` in `connectors/base/http_client.py` validates every outbound URL before opening a socket.
- Only `https://` requests to the explicit `APPROVED_PROVIDER_HOSTS` allowlist (`api.openai.com`, `openrouter.ai`, `api.anthropic.com`, `generativelanguage.googleapis.com`, `api.deepseek.com`, `api.together.xyz`, `api.groq.com`, `api.mistral.ai`, `api.fireworks.ai`) are permitted.
- Redirect following is disabled (`follow_redirects=False`) and strict timeouts (`5s` connect, `15s` read) are enforced.

## 4. Financial Accuracy Rules
- **Actual vs. Estimated Costs**: Stored in separate fields and labeled distinctly (`actual` vs. `estimated`) across all API responses and charts.
- **Zero Double-Counting**: During synchronization, official billing records (`CostRecord` with `cost_type="actual"`) are synced first. Estimated costs are only generated from token usage when an official actual cost record does not already exist for that account and date.
- **Confirmed Balances Only**: Balances are only displayed when `is_supported=True` from an official balance endpoint. Unsupported providers explicitly show `Balance API Unsupported`.
- **Original Currency Preservation**: Every usage, cost, and balance record retains its original currency (`USD`, `EUR`). Currency conversion uses stored `ExchangeRate` rows and reports the exact rate and effective date used.
