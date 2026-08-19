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
            lines.append(
                f"- {emp_id} {emp.get('name', '')} | {emp.get('role', '')}, "
                f"{emp.get('department', '')} | {pts}/"
                f"{emp.get('starting_points', 7.0)} pts | "
                f"{emp.get('warning_status', '')} | joined {emp.get('join_date', '?')}"
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
            f"Points {emp.get('current_points')}/{emp.get('starting_points', 7.0)} | "
            f"Status: {emp.get('warning_status', '')}",
            f"FMLA cases: {emp.get('fmla_approved_cases', 0)} | "
            f"Excused absences: {emp.get('excused_absences', 0)} | "
            f"Freebies used: {emp.get('freebies_used', 0)} | "
            f"Sick hours: {emp.get('sick_balance_hours', 0)} | "
            f"Vacation hours: {emp.get('vacation_hours', 0)}",
        ]

        freezes = emp.get("freeze_history") or []
        if freezes:
            frozen = ", ".join(
                f"{f.get('start')}→{f.get('end')} ({f.get('status')})" for f in freezes
            )
            lines.append(f"Freeze periods: {frozen}")

        history = emp.get("history") or []
        if history:
            lines.append("Attendance history (date, code, points, balance, status — details):")
            for h in history:
                roll = f", roll-on {h['roll_on']}" if h.get("roll_on") else ""
                lines.append(
                    f"  - {h.get('date')} {h.get('code')} {h.get('points')} pts "
                    f"(bal {h.get('balance')}) [{h.get('status')}] — "
                    f"{h.get('details', '')}{roll}"
                )

        warnings = emp.get("warnings") or []
        if warnings:
            lines.append("Warnings issued:")
            for w in warnings:
                lines.append(
                    f"  - {w.get('date')}: {w.get('level')} at {w.get('points')} pts"
                )

        sup_notes = [
            s for s in (emp.get("schedule") or []) if s.get("supervisor_note")
        ]
        if sup_notes:
            lines.append("Supervisor notes:")
            for s in sup_notes:
                lines.append(f"  - {s.get('date')}: \"{s.get('supervisor_note')}\"")

        return "\n".join(lines)

    def build_knowledge_base(self, question: Optional[str] = None) -> str:
        """Compact, grounded text of the full dataset.

        The dataset is small enough to include in full. Employees explicitly
        referenced in the question are listed first so the model anchors on them.
        """
        mentioned = self.find_mentioned(question or "")
        ordered_ids = mentioned + [
            emp_id for emp_id in self.employees if emp_id not in mentioned
        ]
        sections = [self.roster_summary_text(), ""]
        sections.extend(self.employee_detail_text(emp_id) for emp_id in ordered_ids)
        return "\n".join(sections)
