# Workforce Attendance & Compliance Platform

A production-minded platform that automates a blue-collar **"No-Fault" attendance
policy** end to end: a deterministic point **engine**, AI **note-analysis + a
grounded chatbot**, a **Flask JSON API**, and an interactive **operations
dashboard**.

The design keeps the **numbers deterministic** (a day-by-day policy engine) while
using **LLMs only for language** (interpreting supervisor notes and answering
natural-language questions), so compliance decisions stay auditable.

**Docs:** [Architecture](docs/ARCHITECTURE.md) · [API](docs/API.md) ·
[Data model](docs/DATA_MODEL.md) · [Features](docs/FEATURES.md) ·
[Testing](docs/TESTING.md) · [Deployment](docs/DEPLOYMENT.md)

It also ships a **grounded attendance chatbot** (ask natural-language questions about any employee) backed by a **multi-provider, key-rotating LLM client** and a Flask API.

---

## 📋 The "No-Fault" Attendance Policy Rules

The compliance engine evaluates employee actions against a strict, configurable point policy defined in `config.yaml`:

### 1. Point Deductions
All employees start with **7.0 points**. Infractions reduce points as follows:
* **`skps` (Protected Sick Period)**: **0.0 points** (FMLA / legally protected).
* **`skp` (Unprotected Sick)**: **1.0 point**. Multiple consecutive days of sickness are grouped and treated as **one** single unprotected period (deducting 1.0 point total).
* **`LTDR` (Personal Absence)**: **1.0 point** per day.
* **`IANS` (No Call No Show)**: **3.0 points**.
* **`LTNC` (Late Reported Absence)**: **2.0 points**.
* **`LT` (Late Arrival >14 mins)**: **0.5 points**.
* **`Lo` (Late Arrival <=14 mins)**: **0.5 points**. The first **3 `Lo` infractions** in a rolling 12-month period are granted as freebies (**0.0 points** impact).

### 2. Point Expirations & Roll-ons
* Point deductions expire and roll back on (recover) exactly **12 months** after the infraction date.
* Points balance is capped at the maximum starting balance of **7.0**.

### 3. Warning Levels
* **$\le$ 2.0 Points**: Triggers a **Written Warning**.
* **$\le$ 1.0 Points**: Triggers a **Termination Warning** and initiates a **4-month point roll-on freeze period**.
* **$\le$ 0.0 Points**: Triggers the **Termination Memo**.

### 4. The 4-Month Roll-on Freeze
When a points balance falls to or below **1.0**:
* A **4-month freeze period** is activated.
* New point deductions are still applied if new infractions occur.
* No point recovery (roll-on) is allowed to execute during the freeze.
* Once the freeze period ends, any paused or scheduled roll-ons execute instantly.

---

## 🛠 Project Structure

```
blue_collar_attendance_compliance/
├── config.yaml                 # Policy rules & thresholds
├── main.py                     # Batch compliance report CLI
├── server.py                   # Flask API + dashboard host (auth, SSE, analytics)
├── wsgi.py, gunicorn.conf.py   # Production entrypoint + config
├── Dockerfile, .dockerignore   # Container build
├── Makefile                    # install / test / run / build-data / docker
├── scripts/build_employees.py  # Regenerate canonical data/employees.json
├── src/
│   ├── config.py               # PolicyConfig loader
│   ├── parser.py               # CSV/JSON ingestion
│   ├── engine.py               # Deterministic ComplianceEngine
│   ├── compliance_service.py   # Engine-backed live records (contract 3.2)
│   ├── data_store.py           # EmployeeDataStore + knowledge base (contract 3.1)
│   ├── db.py                   # Optional SQLite layer
│   ├── llm_client.py           # Supervisor-note exception analysis (offline mock)
│   ├── report_generator.py     # IRM briefs + warning letters
│   ├── chatbot.py              # Grounded AttendanceChatbot (+ offline fallback)
│   ├── chat_store.py           # Append-only chat audit log
│   └── llm/                    # env, providers, rotating_client, tools, usage
├── dashboard/                  # index.html, index.css, app.js, chat.js,
│                              # analytics.js, login.html, data.js
├── data/                       # punch_logs.csv, supervisor_notes.json,
│                              # employees_meta.json, employees.json (generated)
├── tests/                      # pytest suite (see docs/TESTING.md)
└── .github/workflows/ci.yml    # CI: pytest + data-staleness check
```

See **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** for the component diagram and
data-flow walkthrough.

---

## 🚀 Getting Started

### 1. Requirements & Setup
Make sure you have Python 3.10+ installed. Clone the repository and install dependencies:
```bash
pip install -r requirements.txt
```

### 2. Run the Compliance Evaluation CLI
The CLI ingests logs and notes, evaluates each employee's history, parses supervisor notes for FMLA/excused statuses, and outputs formatted HR reports:
```bash
python3 main.py
```
This generates:
* **IRM Briefs** in `reports/IRM_Brief_EMPxxx.md` (Investigative Review Meeting briefs outlining the trajectory).
* **Warning / Termination Notices** in `reports/Warning_Letter_EMPxxx.md`.

### 3. Run the Unit Test Suite
The suite verifies the deterministic compliance engine and its supporting modules
without requiring network access or an LLM API key:

* **Engine** — basic deductions, consecutive sick (skp) grouping, rolling `Lo`
  freebies, freeze periods and 12-month roll-ons, supervisor-note exemptions (via
  an injected LLM stub), the points floor at zero, and warning thresholds.
* **LLM client** — the offline mock-fallback branches (FMLA, supervisor override,
  protected sick, and non-exempt notes) used when no API key is configured.
* **Parser** — CSV punch-log and JSON supervisor-note ingestion, type
  normalization, and validation errors.

```bash
python3 -m pytest
```

> The `litellm` dependency is imported lazily, so the full suite runs even if it
> is not installed; it is only required for live LLM analysis.


### 4. Run the Full App (Dashboard + Chatbot API)
Serve the dashboard and JSON API with Flask:
```bash
python3 server.py           # http://127.0.0.1:5001  (set PORT to override)
# or: make run
```
Open **[http://127.0.0.1:5001](http://127.0.0.1:5001)**. Without LLM keys the
chatbot uses a deterministic offline fallback, so everything still works. Add keys
to `.env` (copy `.env.example`) for full conversational answers. See the
**[API reference](docs/API.md)** for every endpoint and the
**[deployment guide](docs/DEPLOYMENT.md)** for Docker / gunicorn / auth.

---

## 📊 Dashboard Views

The application provides a two-dashboard linked tab interface:
1. **Compliance & Escalations**: Tracks point trajectory balances, remaining freebies, active/past freeze states, and features a Warning Letter generator previewer. Clicking a freebie date scrolls smoothly to its row, and clicking on an excused point opens a modal detail popup showing the parsed supervisor note.
2. **Operational Shift & Schedules**: Tracks remaining protected sick balances (starting at 40 hours/year), vacation days, base shift calendars, trade-off shift swaps (DTOs), and supervisor notes logs.
3. **Analytics**: Department comparisons, at-risk counts and a points-distribution histogram (also available programmatically at `GET /api/analytics`).

A floating **Attendance Assistant** (chat) answers natural-language questions
grounded in the live dataset, with streaming responses and follow-up suggestions.

---

## 🔌 API at a glance

| Method | Path | Purpose |
| :----- | :--- | :------ |
| GET | `/api/employees` | Full canonical dataset |
| GET | `/api/employees/<id>` | One live-computed employee record |
| GET | `/api/health` | LLM/provider + auth status |
| GET | `/api/usage` | LLM token-usage snapshot |
| GET | `/api/analytics` | Department / at-risk / distribution stats |
| POST | `/api/chat` | Grounded answer `{answer, provider, suggestions}` |
| POST | `/api/chat/stream` | Server-Sent Events stream of the answer |
| POST | `/api/export/irm` | Download an IRM brief (Markdown) |
| POST | `/api/login`, `/api/logout` | Optional token auth |

Full details, request/response shapes and the SSE format are in
**[docs/API.md](docs/API.md)**.

## 🧪 Testing & CI

`make test` (or `pytest -q`) runs the offline suite — engine, parser, config,
compliance service, data builder, SQLite, LLM providers/rotation/tools/usage,
chatbot, chat store, report generator, and the HTTP API. CI runs it on Python
3.10–3.12 plus a data-staleness check. See **[docs/TESTING.md](docs/TESTING.md)**.

## 📚 Documentation index

- **[Architecture](docs/ARCHITECTURE.md)** — components, data flows, design decisions.
- **[API reference](docs/API.md)** — every endpoint, auth, SSE, examples.
- **[Data model](docs/DATA_MODEL.md)** — schemas + how balances are computed.
- **[Features](docs/FEATURES.md)** — full catalogue (done / proposed / future).
- **[Testing](docs/TESTING.md)** — suite map and how to run it.
- **[Deployment](docs/DEPLOYMENT.md)** — Docker, gunicorn, env, auth.
