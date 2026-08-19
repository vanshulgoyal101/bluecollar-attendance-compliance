# Deployment

The app is a standard WSGI application (`wsgi:app`) served by gunicorn in
production. `python server.py` is for local development only.

---

## 1. Environment variables

Copy `.env.example` to `.env` and fill in what you need. Nothing is required — with
no keys the chatbot uses a deterministic offline fallback.

| Variable | Purpose |
| :------- | :------ |
| `GOOGLE_AI_API_KEYS` / `GROQ_API_KEYS` / `OPENROUTER_API_KEYS` / `CEREBRAS_API_KEYS` | Comma-separated key pools; empty disables that provider |
| `LLM_PROVIDER_ORDER` | Failover order, e.g. `google,groq,openrouter,cerebras` |
| `GEMINI_MODEL` / `GROQ_MODEL` / `OPENROUTER_MODEL` / `CEREBRAS_MODEL` | Per-provider model overrides |
| `CHAT_MODEL_TEMPERATURE` | Sampling temperature (lower = more factual) |
| `APP_AUTH_TOKEN` | Access token for the dashboard + API; empty = auth disabled |
| `APP_SECRET_KEY` | Flask session signing key (**set a long random value in prod**) |
| `AUTH_DEV_BYPASS` | Truthy = force auth off even if a token is set (local only) |
| `PORT` | Bind port (default 5001) |
| `WEB_CONCURRENCY` / `GUNICORN_THREADS` / `GUNICORN_TIMEOUT` | gunicorn tuning |

**Never commit `.env`** — it is gitignored. Only `.env.example` is tracked.

---

## 2. Local development

```bash
make install
make run            # python server.py -> http://127.0.0.1:5001
```

---

## 3. Docker (recommended)

```bash
make docker-build            # docker build -t attendance-compliance .
docker run --rm -p 5001:5001 --env-file .env attendance-compliance
```

The image (`python:3.12-slim`) installs deps, runs as a non-root `appuser`, exposes
`5001`, defines a `/api/health` HEALTHCHECK, and launches
`gunicorn -c gunicorn.conf.py wsgi:app`.

---

## 4. Gunicorn directly

```bash
pip install -r requirements.txt
gunicorn -c gunicorn.conf.py wsgi:app
```

Config highlights (`gunicorn.conf.py`): **threaded** `gthread` workers (SSE holds
a request open), `WEB_CONCURRENCY` workers × `GUNICORN_THREADS` threads, a 120s
timeout so long streams aren't killed, and access/error logs to stdout/stderr.

---

## 5. Authentication

Auth is **off** until `APP_AUTH_TOKEN` is set (and `AUTH_DEV_BYPASS` is falsy).
When enabled:

- Browser: unauthenticated requests to non-public paths redirect to `/login`;
  submit the token to get a session cookie.
- API clients: send `Authorization: Bearer <token>` (or `X-Auth-Token: <token>`).
- Public paths (always open): `/login`, `/api/login`, `/api/health`, `/favicon.ico`.

Always set a strong `APP_SECRET_KEY` in production (otherwise a random key is used
and sessions won't survive a restart).

---

## 6. Production checklist

- [ ] `APP_SECRET_KEY` set to a long random value.
- [ ] `APP_AUTH_TOKEN` set (and `AUTH_DEV_BYPASS` unset) if the app is exposed.
- [ ] LLM keys provided (or accept the offline fallback).
- [ ] Reverse proxy passes through SSE (disable response buffering; the app sends
      `X-Accel-Buffering: no`).
- [ ] `data/chat_log.jsonl` on a writable volume if you want to retain the audit log.
- [ ] `python scripts/build_employees.py --check` passes in CI before deploy.
