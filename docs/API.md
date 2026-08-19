# API Reference

Base URL (dev): `http://127.0.0.1:5001`. All request/response bodies are JSON
unless noted. When auth is enabled, every endpoint except the public ones
(`/login`, `/api/login`, `/api/health`, `/favicon.ico`) requires a valid session
cookie or `Authorization: Bearer <token>` header.

---

## Data

### `GET /api/employees`
Returns the full canonical dataset — an object keyed by employee ID. Each value is
a record as described in [DATA_MODEL.md](DATA_MODEL.md).

```json
{ "EMP101": { "name": "Vanshul Goyal", "current_points": 0.5, "...": "..." }, "EMP102": { "...": "..." } }
```

### `GET /api/employees/<id>`
One employee. `id` must match `^EMP\d{2,6}$`. Returns the **live-computed** record
from `ComplianceService` when available, else the stored record.

| Status | Meaning |
| :----- | :------ |
| 200 | Record returned |
| 400 | `{"error": "Invalid employee id."}` |
| 404 | `{"error": "No record for EMPxxx."}` |

---

## Analytics

### `GET /api/analytics`
Aggregate stats computed from the live records (mirrors the dashboard Analytics
tab). `at_risk` = balance ≤ 2.0.

```json
{
  "total_employees": 10,
  "at_risk_count": 3,
  "average_points": 5.05,
  "departments": [
    { "department": "Facilities", "count": 2, "avg_points": 2.25, "at_risk": 1 }
  ],
  "distribution": [
    { "label": "<=0 (Termination)", "count": 1 },
    { "label": "0-1 (Termination Warning)", "count": 1 },
    { "label": "1-2 (Written Warning)", "count": 1 },
    { "label": "2-4", "count": 1 },
    { "label": "4-6", "count": 0 },
    { "label": "6-7 (Good Standing)", "count": 6 }
  ],
  "at_risk": [ { "id": "EMP105", "name": "Kyle Reese", "current_points": 0.0, "department": "Facilities", "warning_status": "TERMINATION PROTOCOL TRIGGERED" } ]
}
```

---

## Health & usage

### `GET /api/health` (public)
```json
{ "status": "ok", "llm_configured": false, "providers": [], "auth_required": false }
```
`providers` lists `{name, key_count}` for each configured provider.

### `GET /api/usage`
Process-global LLM token counters (contract 3.4). No prompts or answers are
stored — only counts.
```json
{ "requests": 12, "prompt_tokens": 8421, "completion_tokens": 1930, "total_tokens": 10351,
  "by_provider": { "google": { "requests": 12, "prompt_tokens": 8421, "completion_tokens": 1930 } } }
```

---

## Chat

### `POST /api/chat`
Request:
```json
{ "question": "Who is at risk of termination?", "history": [ { "role": "user", "content": "hi" }, { "role": "assistant", "content": "..." } ] }
```
`question` ≤ 2000 chars; `history` is truncated to the last 12 turns.

Response:
```json
{ "answer": "…markdown…", "provider": "google", "model": "gemini-2.0-flash", "grounded": true, "suggestions": ["Who is closest to a written warning?", "…"] }
```
With no LLM keys, `provider` is `"offline"` and the answer is a deterministic data
lookup. Errors: `400` (empty/oversized question), `502` (all providers failed).

### `POST /api/chat/stream`
Same request shape; responds with `text/event-stream`. Frames:
```
data: {"delta": "Kyle "}

data: {"delta": "Reese is "}

data: {"done": true, "provider": "google", "model": "gemini-2.0-flash"}
```
On error a `{"error": "..."}` frame precedes the terminal `{"done": true,
"provider": "error"}`. The stream is offline-safe (one delta with the full
offline answer when no keys are set).

---

## Export

### `POST /api/export/irm`
Request `{ "employee_id": "EMP101" }`. Returns a Markdown IRM brief as a file
download (`Content-Disposition: attachment`). Errors: `400` invalid id, `404`
unknown employee.

---

## Auth

Auth is **off** unless `APP_AUTH_TOKEN` is set (and `AUTH_DEV_BYPASS` is not
truthy). See [DEPLOYMENT.md](DEPLOYMENT.md).

### `POST /api/login`
`{ "token": "<APP_AUTH_TOKEN>" }` → sets a session cookie. `401` on mismatch
(constant-time compared).

### `POST /api/logout`
Clears the session. Always `{ "ok": true }`.

### `GET /login`
Serves the login page (public).

---

## Status codes summary

| Code | When |
| :--- | :--- |
| 200 | Success |
| 400 | Validation error (bad id, empty/oversized question) |
| 401 | Auth required / invalid token |
| 404 | Unknown employee |
| 502 | All LLM providers failed |

## Client notes

- The dashboard uses `apiFetch()` which redirects to `/login` on a `401`.
- All responses set JSON content types; the SSE endpoint sets
  `Cache-Control: no-cache` and `X-Accel-Buffering: no` for proxy-friendly
  streaming.
