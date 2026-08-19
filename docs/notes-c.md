# Track C — Web, Dashboard & DevOps

Notes for the routes, UX, auth and deployment added by Track C
(F-33 frontend, F-36 wiring, F-37, F-38, F-45, F-50, F-52).

## What shipped

| Feature | Summary |
| :------ | :------ |
| F-33 | `POST /api/chat/stream` (SSE) + streaming render in `dashboard/chat.js`; non-streaming `/api/chat` kept as fallback |
| F-36 | `GET /api/usage` surfaced in the chat footer (`#chat-usage`) |
| F-37 | "Explain these points" button opens the assistant pre-asked about the selected employee |
| F-38 | "Export … to IRM brief" action on chat answers → `POST /api/export/irm` → Markdown download |
| F-45 | Analytics tab: department comparison, at-risk counts, points distribution (computed from `/api/employees`) |
| F-50 | Token/session auth over the API + dashboard with a dev bypass |
| F-52 | `Dockerfile` + `wsgi.py` + `gunicorn.conf.py` for production |

## HTTP API

| Method | Path | Notes |
| :----- | :--- | :---- |
| GET | `/` | Dashboard (auth-gated when a token is set) |
| GET | `/login` | Login page (public) |
| POST | `/api/login` | `{token}` → sets a session cookie |
| POST | `/api/logout` | Clears the session |
| GET | `/api/employees` | Full canonical dataset |
| GET | `/api/employees/<id>` | Single employee (live via `ComplianceService` when present, else the store) |
| GET | `/api/health` | `{status, llm_configured, providers, auth_required}` (public) |
| GET | `/api/usage` | `usage_snapshot()` (contract 3.4) |
| POST | `/api/chat` | `{question, history?}` → `{answer, provider, model, grounded}` |
| POST | `/api/chat/stream` | SSE of `chatbot.stream()` (contract 3.3); frames are `data: {json}` |
| POST | `/api/export/irm` | `{employee_id}` → downloadable IRM brief (`text/markdown`) |

Input bounds: `question` ≤ 2000 chars; history truncated to the last 12 turns;
`employee_id` must match `EMP\d{2,6}`.

### SSE frame shape
```
data: {"delta": "partial text "}
data: {"delta": "more text"}
data: {"done": true, "provider": "google", "model": "gemini-2.0-flash"}
```
An error mid-stream emits `data: {"error": "..."}` then a `done` frame. The
client falls back to `/api/chat` if streaming is unavailable.

### Contract fallbacks (before Tracks A/B fully merge)
- `chatbot.stream()` (B): if absent, the stream endpoint chunks a non-streaming
  `answer()` so it still streams to the browser.
- `usage_snapshot()` (B, `src/llm/usage.py`): if the module is missing, a zeroed
  snapshot is returned.
- `ComplianceService` (A): `/api/employees/<id>` falls back to the static store.

## Auth (F-50)

Auth is **off by default** so local dev and the offline path keep working. Enable
it by setting a token:

```bash
export APP_AUTH_TOKEN="a-long-random-token"
export APP_SECRET_KEY="another-long-random-value"   # signs session cookies
# optional local override that disables auth even when a token is set:
# export AUTH_DEV_BYPASS=1
```

When enabled:
- Browsers are redirected to `/login`; submitting the token sets a session cookie.
- API clients can send `Authorization: Bearer <token>` or `X-Auth-Token: <token>`.
- `/api/health` stays public for container/orchestrator liveness probes.

## Analytics (F-45)

The Analytics tab is computed client-side in `dashboard/analytics.js` from the
same `employeeData` the dashboard hydrates from `/api/employees`. Current balances
mirror the compliance tab (last history point on/before 2026-05-31). "At-risk"
means ≤ 2.0 points.

## Run in production (F-52)

Threaded gunicorn workers are used because SSE holds a request open per stream.

```bash
# Build
docker build -t attendance-compliance .

# Run (offline/dev — no auth, no LLM keys)
docker run --rm -p 5001:5001 attendance-compliance

# Run with LLM keys + auth via an env file
docker run --rm -p 5001:5001 --env-file .env attendance-compliance

# Override the port / concurrency
docker run --rm -p 8080:8080 -e PORT=8080 -e WEB_CONCURRENCY=4 attendance-compliance
```

Then open http://127.0.0.1:5001 . Without Docker:

```bash
pip install -r requirements.txt
gunicorn -c gunicorn.conf.py wsgi:app
```

Tunables (env): `PORT`, `WEB_CONCURRENCY`, `GUNICORN_THREADS`, `GUNICORN_TIMEOUT`,
`GUNICORN_LOG_LEVEL`.

## Tests

`tests/test_api.py` and `tests/test_server.py` cover the routes, streaming (native
+ fallback), export, input bounds and the auth matrix using an injected fake
chatbot — no network or keys required. Run `pytest -q`.
