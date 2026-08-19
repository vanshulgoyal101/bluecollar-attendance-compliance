# Data Model

All data lives in `data/`. The **source of truth for infractions** is the CSV +
notes; `employees.json` is **generated** from them and must never be hand-edited.

---

## 1. Sources

### `punch_logs.csv` (engine input)
One row per punch/exception. Columns:

| Column | Meaning |
| :----- | :------ |
| `employee_id` | e.g. `EMP101` |
| `date` | ISO date `YYYY-MM-DD` |
| `base_code` | scheduled code (usually `SW`, or `DTO` for a trade) |
| `actual_code` | what happened (`Lo`, `LT`, `skp`, `skps`, `LTDR`, `IANS`, `LTNC`, `SW`, `DO`) |

A row where `actual_code == base_code` (or `SW`) is a normal worked day.

### `supervisor_notes.json` (exemption input)
Free-text notes the note-analysis LLM (or its offline mock) reads to exempt an
infraction (FMLA, "approved / let it slide", protected sick):
```json
[ { "employee_id": "EMP106", "date": "2024-05-10", "note": "FMLA leave approved by HR." } ]
```

### `employees_meta.json` (static HR fields)
Everything that is **not** derived from punches — name, join date, role,
department, `starting_points`, and HR counters (`fmla_approved_cases`,
`excused_absences`, `freebies_used`, `sick_balance_hours`, `vacation_hours`).

---

## 2. Generated: `employees.json`

`ComplianceService` merges `employees_meta.json` with **engine-computed** fields
and `scripts/build_employees.py` writes the result. Per-employee record:

| Field | Source | Notes |
| :---- | :----- | :---- |
| `name`, `join_date`, `role`, `department` | meta | static |
| `starting_points`, `sick_balance_hours`, `vacation_hours` | meta | static |
| `fmla_approved_cases`, `excused_absences`, `freebies_used` | meta | HR counters |
| `current_points` | **engine** | balance as of 2026-05-31 |
| `warning_status` | **engine** | derived from points |
| `freeze_history` | **engine** | `[{start, end, status}]` (Active/Completed/Scheduled) |
| `history` | **engine** | infractions + ROLL-ON rows with running `balance` |
| `warnings` | **engine** | `[{date, level, points}]` |
| `schedule` | **engine** | per-punch view (base/actual/status/notes/supervisor_note) |

`history` row shape:
```json
{ "date": "2026-02-15", "code": "LTNC", "points": -2.0, "balance": 0.5,
  "status": "Active Deduction", "details": "Late reported absence", "roll_on": "2027-02-15" }
```
Recovery rows use `code: "ROLL-ON"`, positive `points`, and `status:
"Rolled-on (Expired)"`.

---

## 3. How balances are computed

`ComplianceEngine.process_employee_compliance` replays the timeline day-by-day:

1. **Start** at `starting_points` (7.0).
2. **Deduct** per `config.yaml` when an infraction occurs, unless exempt.
   - `skp` consecutive days group into one deduction.
   - First 3 `Lo` per rolling 12 months are free "freebies".
   - A supervisor note may exempt an infraction (FMLA / override / protected).
3. **Roll-on**: each deduction recovers exactly 12 months later (balance capped at
   7.0), **unless** a freeze is active.
4. **Freeze**: dropping to ≤ 1.0 starts a 4-month freeze; roll-ons pause and run
   once it ends. New deductions still apply.
5. **Warnings**: ≤ 2.0 Written, ≤ 1.0 Termination Warning, ≤ 0.0 Termination.

`ComplianceService` injects a synthetic `SW` punch at the reference date
(**2026-05-31**) so roll-ons that are due by "today" are applied — this is what
keeps the interactive view consistent with the dashboard.

Point costs (`config.yaml`): `skps` 0.0, `skp` 1.0, `LTDR` 1.0, `IANS` 3.0,
`LTNC` 2.0, `LT` 0.5, `Lo` 0.5.

---

## 4. Rebuilding the dataset

```bash
python scripts/build_employees.py            # rewrite data/employees.json
python scripts/build_employees.py --check     # CI: exit 1 if committed file is stale
python scripts/build_employees.py --sqlite data/attendance.db   # also emit SQLite
```
Output is deterministic (sorted keys, fixed indent), so `--check` reliably detects
drift. CI runs `--check` on every push.

---

## 5. Optional SQLite layer (`src/db.py`)

A minimal, **optional** store (the JSON path stays the default). Tables:

- `employees(id PK, name, join_date, role, department, starting_points, current_points, warning_status)`
- `punches(id PK, employee_id, date, base_code, actual_code)`
- `notes(id PK, employee_id, date, note)`

Loaders read the same CSV/JSON sources:
```python
from src import db
conn = db.build_database("data/attendance.db")   # or ":memory:"
db.all_employees(conn); db.punches_for(conn, "EMP101"); db.notes_for(conn, "EMP106")
```

---

## 6. Runtime artifacts (gitignored)

- `data/chat_log.jsonl` — append-only chat audit log (question + referenced IDs +
  provider + answer length; never the answer text).
- `reports/*.md` — generated IRM briefs and warning letters.
