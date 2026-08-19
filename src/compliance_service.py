"""Engine-backed compliance service (F-31).

Turns raw punch logs + supervisor notes into live-computed employee records
shaped like ``data/employees.json`` entries. Static HR metadata (name, role,
hour balances, ...) comes from ``data/employees_meta.json``; the compliance
fields (``current_points``, ``warning_status``, ``freeze_history``, ``schedule``,
``history`` and ``warnings``) are computed on demand by :class:`ComplianceEngine`.

Balances are evaluated as of :data:`DEFAULT_AS_OF` (the dashboard's reference
"today") so results are deterministic regardless of the wall clock. This is the
seam consumed by the chatbot's tool layer (contract 3.2).
"""

import datetime
import json
import os
from typing import Any, Dict, List, Optional

import pandas as pd

from src.config import PolicyConfig
from src.engine import ComplianceEngine
from src.parser import DataIngestion

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DEFAULT_META_PATH = os.path.join(_DATA_DIR, "employees_meta.json")
DEFAULT_CSV_PATH = os.path.join(_DATA_DIR, "punch_logs.csv")
DEFAULT_NOTES_PATH = os.path.join(_DATA_DIR, "supervisor_notes.json")

# The dashboard treats 2026-05-31 as "today" (see PROJECT_DOCUMENTATION §7).
DEFAULT_AS_OF = datetime.date(2026, 5, 31)

CODE_LABELS = {
    "SW": "SW (Scheduled Work)",
    "Lo": "Lo (Late <=14m)",
    "LT": "LT (Late >14m)",
    "skp": "skp (Unprotected Sick)",
    "skps": "skps (Protected Sick)",
    "LTDR": "LTDR (Personal)",
    "IANS": "IANS (No Call No Show)",
    "LTNC": "LTNC (Late Reported)",
    "DO": "DO (Day Off)",
    "DTO": "DTO (Day Trade)",
}

CODE_DETAILS = {
    "Lo": "Late <=14 mins",
    "LT": "Late >14 mins",
    "skp": "Unprotected sick period",
    "skps": "Protected sick leave",
    "LTDR": "Personal absence",
    "IANS": "No call no show",
    "LTNC": "Late reported absence",
}


def _iso(value: Any) -> Any:
    return value.isoformat() if isinstance(value, datetime.date) else value


class ComplianceService:
    def __init__(
        self,
        config: Optional[PolicyConfig] = None,
        engine: Optional[ComplianceEngine] = None,
        meta_path: Optional[str] = None,
        csv_path: Optional[str] = None,
        notes_path: Optional[str] = None,
        as_of: Optional[datetime.date] = None,
    ):
        self.config = config or PolicyConfig()
        self.engine = engine or ComplianceEngine(self.config)
        self.as_of = as_of or DEFAULT_AS_OF
        with open(meta_path or DEFAULT_META_PATH, "r") as f:
            self.meta: Dict[str, Dict[str, Any]] = json.load(f)
        self.punch_df = DataIngestion.load_punch_logs(csv_path or DEFAULT_CSV_PATH)
        self.notes = DataIngestion.load_supervisor_notes(notes_path or DEFAULT_NOTES_PATH)
        self._notes_by_date: Dict[str, Dict[datetime.date, str]] = {}
        for note in self.notes:
            self._notes_by_date.setdefault(note["employee_id"], {})[note["date"]] = note["note"]
        self._cache: Dict[str, Dict[str, Any]] = {}

    # --- public API (contract 3.2) --------------------------------------- #

    def employee_ids(self) -> List[str]:
        return list(self.meta.keys())

    def get_employee(self, emp_id: str) -> Dict[str, Any]:
        if emp_id not in self.meta:
            raise KeyError(f"Unknown employee: {emp_id}")
        if emp_id not in self._cache:
            self._cache[emp_id] = self._build_record(emp_id)
        return self._cache[emp_id]

    def all_records(self) -> Dict[str, Dict[str, Any]]:
        return {emp_id: self.get_employee(emp_id) for emp_id in self.employee_ids()}

    def roster(self) -> List[Dict[str, Any]]:
        rows = []
        for emp_id in self.employee_ids():
            rec = self.get_employee(emp_id)
            rows.append(
                {
                    "id": emp_id,
                    "name": rec.get("name", ""),
                    "role": rec.get("role", ""),
                    "department": rec.get("department", ""),
                    "current_points": rec.get("current_points"),
                    "warning_status": rec.get("warning_status", ""),
                }
            )
        return rows

    def list_by_status(self, status: str) -> List[Dict[str, Any]]:
        needle = (status or "").strip().lower()
        return [r for r in self.roster() if needle in r["warning_status"].lower()]

    def lowest_points(self, n: int = 1) -> List[Dict[str, Any]]:
        ordered = sorted(self.roster(), key=lambda r: (r["current_points"], r["id"]))
        return ordered[: max(n, 0)]

    def infractions(self, emp_id: str, year: Optional[int] = None) -> List[Dict[str, Any]]:
        result = self.get_employee(emp_id)
        out = []
        for entry in self._engine_result(emp_id)["history"]:
            date = entry["date"]
            if year is not None and date.year != year:
                continue
            out.append(
                {
                    "date": _iso(date),
                    "code": entry["code"],
                    "points": 0.0 if entry["is_exempted"] else -round(entry["points_deducted"], 2),
                    "exempt": bool(entry["is_exempted"]),
                    "reason": entry.get("exempt_reason") or CODE_DETAILS.get(entry["code"], entry["code"]),
                    "roll_on": _iso(entry["roll_on_date"]) if not entry["is_exempted"] else None,
                }
            )
        # Reference the record so an unknown id still raises via get_employee.
        assert result is not None
        return out

    # --- internals ------------------------------------------------------- #

    def _employee_punches(self, emp_id: str) -> pd.DataFrame:
        emp = self.punch_df[self.punch_df["employee_id"] == emp_id]
        rows = emp.to_dict("records")
        last = emp["date"].max() if not emp.empty else None
        if last is None or self.as_of > last:
            rows.append(
                {
                    "employee_id": emp_id,
                    "date": self.as_of,
                    "base_code": "SW",
                    "actual_code": "SW",
                }
            )
        return pd.DataFrame(rows, columns=["employee_id", "date", "base_code", "actual_code"])

    def _engine_result(self, emp_id: str) -> Dict[str, Any]:
        key = f"_engine::{emp_id}"
        if key not in self._cache:
            df = self._employee_punches(emp_id)
            self._cache[key] = self.engine.process_employee_compliance(emp_id, df, self.notes)
        return self._cache[key]

    def _build_record(self, emp_id: str) -> Dict[str, Any]:
        meta = self.meta[emp_id]
        result = self._engine_result(emp_id)
        points = round(result["current_points"], 2)
        freeze_history = self._freeze_history(result["freeze_periods"])
        history = self._history(result["history"], meta.get("starting_points", self.config.start_points))
        record = dict(meta)
        record.update(
            {
                "current_points": points,
                "warning_status": self._warning_status(points),
                "freeze_history": freeze_history,
                "schedule": self._schedule(emp_id, result["history"]),
                "history": history,
                "warnings": [
                    {"date": _iso(w["date"]), "level": w["level"], "points": round(w["points"], 2)}
                    for w in result["warnings"]
                ],
            }
        )
        return record

    def _warning_status(self, points: float) -> str:
        if points <= self.config.warning_termination:
            return "TERMINATION PROTOCOL TRIGGERED"
        if points <= self.config.warning_termination_warning:
            return "Termination Warning Active"
        if points <= self.config.warning_written:
            return "Written Warning Active"
        return "Good Standing"

    def _freeze_history(self, periods: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out = []
        for period in periods:
            start, end = period["start"], period["end"]
            if self.as_of < start:
                status = "Scheduled"
            elif self.as_of <= end:
                status = "Active"
            else:
                status = "Completed"
            out.append({"start": _iso(start), "end": _iso(end), "status": status})
        return out

    def _history(self, deductions: List[Dict[str, Any]], starting_points: float) -> List[Dict[str, Any]]:
        events = []
        for dec in deductions:
            events.append({"sort": (dec["date"], 1, dec["date"]), "kind": "infraction", "dec": dec})
            if (
                not dec["is_exempted"]
                and dec["rolled_on"]
                and dec["actual_roll_on_date"] is not None
                and dec["actual_roll_on_date"] <= self.as_of
            ):
                events.append(
                    {
                        "sort": (dec["actual_roll_on_date"], 0, dec["date"]),
                        "kind": "rollon",
                        "dec": dec,
                    }
                )
        events.sort(key=lambda e: e["sort"])

        balance = starting_points
        out = []
        for event in events:
            dec = event["dec"]
            if event["kind"] == "rollon":
                balance = min(round(balance + dec["points_deducted"], 2), starting_points)
                out.append(
                    {
                        "date": _iso(dec["actual_roll_on_date"]),
                        "code": "ROLL-ON",
                        "points": round(dec["points_deducted"], 2),
                        "balance": balance,
                        "status": "Rolled-on (Expired)",
                        "details": f"Recovery of {_iso(dec['date'])} {dec['code']} deduction",
                    }
                )
            elif dec["is_exempted"]:
                out.append(
                    {
                        "date": _iso(dec["date"]),
                        "code": dec["code"],
                        "points": 0.0,
                        "balance": round(balance, 2),
                        "status": "Exempted",
                        "details": dec.get("exempt_reason") or "Exempted",
                    }
                )
            else:
                balance = max(round(balance - dec["points_deducted"], 2), 0.0)
                out.append(
                    {
                        "date": _iso(dec["date"]),
                        "code": dec["code"],
                        "points": -round(dec["points_deducted"], 2),
                        "balance": balance,
                        "status": "Active Deduction",
                        "details": CODE_DETAILS.get(dec["code"], dec["code"]),
                        "roll_on": _iso(dec["roll_on_date"]),
                    }
                )
        return out

    def _schedule(self, emp_id: str, deductions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        by_date = {dec["date"]: dec for dec in deductions}
        notes = self._notes_by_date.get(emp_id, {})
        emp = self.punch_df[self.punch_df["employee_id"] == emp_id].sort_values(by="date")
        out = []
        for _, punch in emp.iterrows():
            date = punch["date"]
            base_code, actual_code = punch["base_code"], punch["actual_code"]
            entry: Dict[str, Any] = {
                "date": _iso(date),
                "base": CODE_LABELS.get(base_code, base_code),
                "actual": CODE_LABELS.get(actual_code, actual_code),
                "dto": base_code == "DTO",
                "notes": "",
            }
            dec = by_date.get(date)
            if base_code == "DTO":
                entry["status"] = "Swapped"
            elif actual_code == base_code or actual_code == "SW":
                entry["status"] = "Normal"
            elif dec is None:
                entry["status"] = "Normal"
            elif dec["is_exempted"]:
                entry["status"] = self._exempt_status(dec.get("exempt_reason", ""))
                entry["notes"] = dec.get("exempt_reason", "")
            else:
                entry["status"] = f"Point Deducted (-{round(dec['points_deducted'], 1)})"
                entry["notes"] = CODE_DETAILS.get(actual_code, actual_code)
                entry["roll_on"] = _iso(dec["roll_on_date"])
            if date in notes:
                entry["supervisor_note"] = notes[date]
            out.append(entry)
        return out

    @staticmethod
    def _exempt_status(reason: str) -> str:
        reason = reason or ""
        if "FMLA" in reason:
            return "Exempted (FMLA)"
        if "Consecutive" in reason:
            return "Consecutive - No Penalty"
        if "Freebie" in reason:
            return "Excused"
        return "Excused (Supervisor Override)"
