"""Canonical employee attendance data store.

``data/employees.json`` is the single source of truth for both the dashboard
(served over HTTP) and the chatbot. This module loads that file and renders it
into a compact, grounded text "knowledge base" the LLM can reason over.
"""

import json
import os
from typing import Any, Dict, List, Optional

DEFAULT_DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "employees.json"
)


class EmployeeDataStore:
    def __init__(self, path: Optional[str] = None):
        self.path = path or DEFAULT_DATA_PATH
        with open(self.path, "r") as f:
            self.employees: Dict[str, Dict[str, Any]] = json.load(f)

    def all(self) -> Dict[str, Dict[str, Any]]:
        return self.employees

    def get(self, emp_id: str) -> Optional[Dict[str, Any]]:
        return self.employees.get(emp_id)

    def roster(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": emp_id,
                "name": emp.get("name", ""),
                "role": emp.get("role", ""),
                "department": emp.get("department", ""),
                "current_points": emp.get("current_points"),
                "warning_status": emp.get("warning_status", ""),
            }
            for emp_id, emp in self.employees.items()
        ]

    def find_mentioned(self, question: str) -> List[str]:
        """Return IDs of employees whose ID or name is referenced in the text."""
        q = (question or "").lower()
        mentioned = []
        for emp_id, emp in self.employees.items():
            name = emp.get("name", "")
            if emp_id.lower() in q:
                mentioned.append(emp_id)
                continue
            # Match on full name or any name part (e.g. first name only).
            parts = [name.lower()] + name.lower().split()
            if any(part and part in q for part in parts):
                mentioned.append(emp_id)
        return mentioned

    def roster_summary_text(self) -> str:
        lines = ["ROSTER (all employees):"]
        for emp_id, emp in self.employees.items():
            pts = emp.get("current_points")
            flags = []
            if emp.get("fmla_approved_cases"):
                flags.append(f"{emp['fmla_approved_cases']} FMLA")
            if emp.get("freebies_used"):
                flags.append(f"{emp['freebies_used']} freebies")
            active = next(
                (
                    f
                    for f in (emp.get("freeze_history") or [])
                    if f.get("status") == "Active"
                ),
                None,
            )
            if active:
                flags.append(f"freeze active→{active.get('end')}")
            extra = f" | {', '.join(flags)}" if flags else ""
            lines.append(
                f"- {emp_id} {emp.get('name', '')} | {emp.get('role', '')}, "
                f"{emp.get('department', '')} | {pts}/"
                f"{emp.get('starting_points', 7.0)} pts | "
                f"{emp.get('warning_status', '')} | joined "
                f"{emp.get('join_date', '?')}{extra}"
            )
        return "\n".join(lines)

    def employee_detail_text(self, emp_id: str) -> str:
        emp = self.employees.get(emp_id)
        if not emp:
            return f"(No record for {emp_id}.)"

        lines = [
            f"### {emp_id} — {emp.get('name', '')} "
            f"({emp.get('role', '')}, {emp.get('department', '')})",
            f"Joined {emp.get('join_date', '?')} | "
            f"{emp.get('current_points')}/{emp.get('starting_points', 7.0)} pts | "
            f"{emp.get('warning_status', '')} | "
            f"FMLA {emp.get('fmla_approved_cases', 0)}, "
            f"excused {emp.get('excused_absences', 0)}, "
            f"freebies {emp.get('freebies_used', 0)}, "
            f"sick {emp.get('sick_balance_hours', 0)}h, "
            f"vacation {emp.get('vacation_hours', 0)}h",
        ]

        freezes = emp.get("freeze_history") or []
        if freezes:
            frozen = ", ".join(
                f"{f.get('start')}→{f.get('end')} ({f.get('status')})" for f in freezes
            )
            lines.append(f"Freezes: {frozen}")

        notes_by_date = {
            s.get("date"): s.get("supervisor_note")
            for s in (emp.get("schedule") or [])
            if s.get("supervisor_note")
        }

        # ROLL-ON recovery rows are implied by each infraction's roll-on date,
        # so they are omitted here to keep the grounding context small.
        infractions = [
            h for h in (emp.get("history") or []) if h.get("code") != "ROLL-ON"
        ]
        if infractions:
            lines.append("Infractions (date code pts→balance [status] details):")
            for h in infractions:
                roll = f" roll-on {h['roll_on']}" if h.get("roll_on") else ""
                note = notes_by_date.get(h.get("date"))
                note_s = f' note:"{note}"' if note else ""
                lines.append(
                    f"  - {h.get('date')} {h.get('code')} "
                    f"{h.get('points')}→{h.get('balance')} "
                    f"[{h.get('status')}] {h.get('details', '')}{roll}{note_s}"
                )

        warnings = emp.get("warnings") or []
        if warnings:
            lines.append(
                "Warnings: "
                + "; ".join(
                    f"{w.get('date')} {w.get('level')} @ {w.get('points')}pts"
                    for w in warnings
                )
            )

        infr_dates = {h.get("date") for h in infractions}
        extra_notes = {d: n for d, n in notes_by_date.items() if d not in infr_dates}
        if extra_notes:
            lines.append(
                "Notes: " + "; ".join(f'{d}: "{n}"' for d, n in extra_notes.items())
            )

        return "\n".join(lines)

    def build_knowledge_base(self, question: Optional[str] = None) -> str:
        """Grounded text scoped to the employees a question is about.

        The enriched roster (points, status, FMLA/freebie/freeze flags) always
        covers everyone, so summary questions stay fully answerable. Full per-
        employee detail is included only for the employees the question targets
        — those explicitly mentioned, or the at-risk staff for roster-wide
        questions — which keeps the prompt small without dropping relevant facts.
        """
        mentioned = self.find_mentioned(question or "")
        if mentioned:
            focus = mentioned
        else:
            focus = [
                emp_id
                for emp_id, emp in self.employees.items()
                if (emp.get("warning_status") or "").strip().lower() != "good standing"
            ]
        sections = [self.roster_summary_text(), ""]
        sections.extend(self.employee_detail_text(emp_id) for emp_id in focus)
        return "\n".join(sections)
