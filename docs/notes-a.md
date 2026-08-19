# Track A — Data & Compliance Backbone (notes)

Delivers F-30, F-31, F-32, F-39 and the F-42 SQLite foundation. Consumers (B/C)
should integrate via the interfaces below — do not read the raw CSV directly.

## What landed

| Feature | File | Summary |
| :------ | :--- | :------ |
| F-32 | `data/punch_logs.csv` | Full punch histories for EMP101–EMP110. |
| F-31 | `src/compliance_service.py` | `ComplianceService` — live-computed records. |
| F-30 | `scripts/build_employees.py` | Regenerates canonical `data/employees.json`. |
| F-42 | `src/db.py` | Optional SQLite layer (employees/punches/notes). |
| F-39 | `.github/workflows/ci.yml` | Runs `pytest -q` + a staleness check. |

## Data model

- `data/employees_meta.json` — **static** HR fields (name, role, department,
  join_date, hour balances, FMLA/excused/freebie counters). Source of truth for
  everything that is *not* computed from punches.
- `data/punch_logs.csv` — infraction timeline per employee (engine input).
- `data/supervisor_notes.json` — notes that drive policy exemptions (FMLA / "let
  it slide"), consumed by the engine's note analysis.
- `data/employees.json` — **generated**, canonical dataset. Do not hand-edit;
  run the builder instead.

`ComplianceService` merges static metadata with engine-computed compliance
fields (`current_points`, `warning_status`, `freeze_history`, `schedule`,
`history`, `warnings`), evaluated as of **2026-05-31** (the dashboard's "today").

## Interfaces

`ComplianceService` (contract 3.2) — for B's tool-calling (F-40):

```python
svc = ComplianceService()
svc.get_employee("EMP101")     # -> full live record (employees.json shape)
svc.roster()                    # -> [{id,name,role,department,current_points,warning_status}]
svc.list_by_status("termination")
svc.lowest_points(3)
svc.infractions("EMP106", year=2024)
```

`EmployeeDataStore` (contract 3.1) is unchanged and still reads
`data/employees.json`.

## Regenerating data

```bash
python scripts/build_employees.py            # rewrite data/employees.json
python scripts/build_employees.py --check     # CI: fail if committed file is stale
python scripts/build_employees.py --sqlite data/attendance.db   # optional DB
```

The build is deterministic (sorted keys, fixed indent), so `--check` in CI fails
if `employees.json` drifts from the source data.

## Tests

`tests/test_compliance_service.py`, `tests/test_build_employees.py`,
`tests/test_db.py`. All offline (no keys/network). `pytest -q` is green.
