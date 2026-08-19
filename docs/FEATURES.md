# Features Catalog

Every feature has a stable ID so the [Parallel Work Plan](PARALLEL_WORK_PLAN.md)
can reference it. Status legend:

- ✅ **Done** — implemented and tested.
- 🟡 **Proposed** — near-term, well-scoped, ready to build.
- 🔵 **Future** — roadmap / larger effort.

---

## 1. Existing Features (baseline compliance engine)

| ID | Feature | Status | Components |
| :- | :------ | :----- | :--------- |
| F-01 | Deterministic point engine (day-by-day replay) | ✅ | `src/engine.py` |
| F-02 | Configurable policy (points, thresholds, codes) | ✅ | `config.yaml`, `src/config.py` |
| F-03 | 12-month roll-on/expiry with 7.0 cap | ✅ | `src/engine.py` |
| F-04 | 4-month roll-on freeze | ✅ | `src/engine.py` |
| F-05 | Warning & termination thresholds | ✅ | `src/engine.py` |
| F-06 | `Lo` freebies (3 per rolling 12m) | ✅ | `src/engine.py` |
| F-07 | Consecutive `skp` grouping | ✅ | `src/engine.py` |
| F-08 | CSV punch + JSON note ingestion | ✅ | `src/parser.py` |
| F-09 | LLM supervisor-note exception analysis (+ offline mock) | ✅ | `src/llm_client.py` |
| F-10 | IRM brief + warning letter generation | ✅ | `src/report_generator.py` |
| F-11 | Batch CLI pipeline | ✅ | `main.py` |
| F-12 | Static operations dashboard (10 employees, 2 tabs, modals) | ✅ | `dashboard/` |
| F-13 | Test suite (engine, parser, note mock) | ✅ | `tests/` |

---

## 2. New Features (this iteration — chatbot & platform)

| ID | Feature | Status | Components |
| :- | :------ | :----- | :--------- |
| F-20 | Canonical `employees.json` single source of truth | ✅ | `data/employees.json`, `src/data_store.py` |
| F-21 | Knowledge-base builder (grounding text) | ✅ | `src/data_store.py` |
| F-22 | Rotating multi-provider LLM client (adbrain pattern) | ✅ | `src/llm/rotating_client.py` |
| F-23 | Per-provider key pools + round-robin rotation | ✅ | `src/llm/env.py`, `rotating_client.py` |
| F-24 | 429 cooldown + provider failover | ✅ | `src/llm/rotating_client.py` |
| F-25 | Gemini + OpenAI-compatible providers | ✅ | `src/llm/providers.py` |
| F-26 | Env-configurable models per provider | ✅ | `src/llm/env.py` |
| F-27 | Grounded attendance chatbot (LLM + offline fallback) | ✅ | `src/chatbot.py` |
| F-28 | Flask API (`/api/chat`, `/api/employees`, `/api/health`) | ✅ | `server.py` |
| F-29 | Chat UI widget (safe markdown, suggestions, hydration) | ✅ | `dashboard/chat.js`, `index.html`, `index.css` |
| F-2A | Rotating-client + chatbot tests | ✅ | `tests/test_rotating_client.py`, `tests/test_chatbot.py` |

---

## 3. Delivered by Parallel Workers (Tracks A / B / C)

Built per [PARALLEL_WORK_PLAN.md](PARALLEL_WORK_PLAN.md). All ✅ and covered by the
test suite (**132 tests passing**).

### Track A — Data & Compliance Backbone
| ID | Feature | Status | Components |
| :- | :------ | :----- | :--------- |
| F-30 | Canonical `employees.json` **generated** from source data (idempotent, `--check` for CI) | ✅ | `scripts/build_employees.py` |
| F-31 | Engine-backed `ComplianceService` — live-computed records (contract 3.2) | ✅ | `src/compliance_service.py` |
| F-32 | Full punch histories for all 10 employees + static HR metadata | ✅ | `data/punch_logs.csv`, `data/employees_meta.json` |
| F-39 | GitHub Actions CI (`pytest` + data-staleness check) | ✅ | `.github/workflows/ci.yml` |
| F-42 | Optional SQLite layer (employees/punches/notes) | ✅ | `src/db.py` |

### Track B — AI / LLM Platform & Chatbot
| ID | Feature | Status | Components |
| :- | :------ | :----- | :--------- |
| F-33 | Streaming completions (generator `stream()`) | ✅ | `src/llm/rotating_client.py`, `src/chatbot.py` |
| F-34 | Conversation/query audit log | ✅ | `src/chat_store.py` |
| F-35 | Deterministic follow-up suggestions | ✅ | `src/chatbot.py` |
| F-36 | LLM usage/token metering (thread-safe, contract 3.4) | ✅ | `src/llm/usage.py` |
| F-40 | Tool/function-calling over `ComplianceService` | ✅ | `src/llm/tools.py`, `src/chatbot.py` |

### Track C — Web, Dashboard & DevOps
| ID | Feature | Status | Components |
| :- | :------ | :----- | :--------- |
| F-33 | SSE streaming endpoint + streaming render | ✅ | `server.py`, `dashboard/chat.js` |
| F-36 | `/api/usage` surfaced in chat footer | ✅ | `server.py`, `dashboard/chat.js` |
| F-37 | "Explain these points" deep-link to the assistant | ✅ | `dashboard/app.js`, `dashboard/chat.js` |
| F-38 | Export a chat answer to an IRM brief download | ✅ | `server.py`, `src/report_generator.py` |
| F-45 | Analytics tab (dept comparison, at-risk, distribution) | ✅ | `dashboard/analytics.js` |
| F-50 | Token/session auth + dev bypass | ✅ | `server.py`, `dashboard/login.html` |
| F-52 | Dockerfile + WSGI + gunicorn config | ✅ | `Dockerfile`, `wsgi.py`, `gunicorn.conf.py` |

---

## 4. Remaining Roadmap (not yet built)

| ID | Feature | Status | Notes |
| :- | :------ | :----- | :---- |
| F-41 | Retrieval (embeddings) over notes + policy docs | 🔵 | For rosters too large for full-context/tools |
| F-43 | HRIS/timeclock ingestion connectors (UKG/Kronos) | 🔵 | Integrations |
| F-44 | Proactive threshold alerts (Slack/email) | 🔵 | Background worker |
| F-46 | Policy what-if simulator | 🔵 | Engine variant |
| F-51 | PDF export + e-signature for letters | 🔵 | Reporting |
| F-53 | Multi-language chat for the workforce | 🔵 | i18n |

---

## 5. Dependency Notes

- **F-31** (`ComplianceService`) is the seam consumed by **F-40**'s tools and by
  Track C's `/api/employees/<id>`.
- **F-30** regenerates `employees.json` from `punch_logs.csv` + `employees_meta.json`,
  so the batch and interactive paths now share one source of truth.
- **F-41** builds on **F-40**'s tool interface for large rosters.
- **F-42** (SQLite) underpins future **F-44/F-45** at scale.
