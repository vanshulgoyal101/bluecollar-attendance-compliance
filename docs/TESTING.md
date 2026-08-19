# Testing

The suite is **fully offline** — no network, no API keys. LLM providers are faked
with monkeypatched `requests`, and the chatbot/LLM tests use in-memory fakes.

```bash
make test          # or: pytest -q
pytest -q tests/test_engine.py            # one module
pytest -q -k "analytics or providers"      # by keyword
```

CI (`.github/workflows/ci.yml`) runs `pytest -q` on Python 3.10 / 3.11 / 3.12 and
then `python scripts/build_employees.py --check` to guarantee `employees.json` is
in sync with its source data.

---

## Coverage map

| Module under test | Test file | What it covers |
| :---------------- | :-------- | :------------- |
| `engine.py` | `test_engine.py` | deductions, consecutive `skp`, `Lo` freebies, freeze + 12-month roll-on, note exemptions, points floor, warnings |
| `config.py` | `test_config.py` | thresholds, deductions, freebies, unknown code |
| `parser.py` | `test_parser.py` | CSV/JSON ingestion, normalization, validation errors |
| `llm_client.py` | `test_llm_client.py` | offline mock branches (FMLA / override / protected / none) |
| `compliance_service.py` | `test_compliance_service.py` | live points per employee, history balance, status, freezes, `list_by_status`, `lowest_points`, `infractions`, `as_of` |
| `scripts/build_employees.py` | `test_build_employees.py` | dataset build, idempotency, `--check` staleness, data-store round-trip |
| `db.py` | `test_db.py` | schema, loaders, queries, file + in-memory DBs |
| `report_generator.py` | `test_report_generator.py` | IRM brief sections/status, exemptions, empty history, warning letter |
| `llm/providers.py` | `test_providers.py` | Gemini + OpenAI complete/stream/tool-calling, HTTP errors, key redaction |
| `llm/rotating_client.py` | `test_rotating_client.py` | rotation, cooldown, failover, streaming semantics |
| `llm/tools.py` | `test_llm_tools.py` | tool specs + dispatch, stub service, arg validation |
| `llm/usage.py` | `test_llm_usage.py` | counters, per-provider buckets, estimates, reset |
| `chatbot.py` | `test_chatbot.py` | offline intents, grounded prompt assembly, suggestions |
| `chat_store.py` | `test_chat_store.py` | append/read JSONL, employee-ID extraction, privacy |
| streaming | `test_chat_stream.py` | chatbot/stream chunks, SSE-shaped output |
| `server.py` | `test_server.py` | routing, validation, auth guard, error handling |
| HTTP API | `test_api.py` | end-to-end endpoint behavior with fakes |
| `/api/analytics` | `test_analytics.py` | aggregation, department/distribution/at-risk, endpoint |

---

## Conventions

- **No network** — anything touching an LLM provider must fake `requests` or
  inject a fake client. Tests that need an app use `create_app(chatbot=..., store=...)`.
- **Deterministic** — the compliance layer is evaluated as of **2026-05-31**;
  assert exact points/dates.
- **Add a test with every module** — new `src/` code ships with a matching
  `tests/test_*.py`. Keep the CI green (`pytest -q` + `--check`).
- **Fixtures** — prefer small, explicit fixtures over shared global state; reset
  process-global counters (`llm.usage.reset()`) when asserting on them.
