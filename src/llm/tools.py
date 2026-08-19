"""Function-calling tools over the compliance data (F-40).

Instead of dumping the whole dataset into the prompt, the model can call a small
set of structured tools that map 1:1 to the ``ComplianceService`` interface
(contract 3.2). This scales past full-context grounding as the roster grows.

``ComplianceToolset`` is provider-agnostic: it exposes JSON tool ``specs()`` and
a ``dispatch()`` that executes a named tool. It works against the real
``ComplianceService`` (owned by Worker A) or the ``StubComplianceService`` here,
which is backed by the read-only ``EmployeeDataStore`` (contract 3.1).
"""

from typing import Any, Dict, List, Optional

from src.data_store import EmployeeDataStore


class ToolError(Exception):
    """Raised when a tool name is unknown or its arguments are invalid."""


class StubComplianceService:
    """Contract-3.2 ComplianceService backed by the static ``employees.json``.

    Used until Worker A's live-computed ``src/compliance_service.py`` is merged.
    The method signatures and return shapes match contract 3.2 exactly so the
    real service can be dropped in without touching the toolset or chatbot.
    """

    def __init__(self, store: Optional[EmployeeDataStore] = None):
        self.store = store or EmployeeDataStore()

    def get_employee(self, emp_id: str) -> dict:
        emp = self.store.get(emp_id)
        if not emp:
            return {}
        record = dict(emp)
        record["id"] = emp_id
        return record

    def roster(self) -> List[dict]:
        return self.store.roster()

    def list_by_status(self, status: str) -> List[dict]:
        needle = (status or "").lower()
        return [
            row
            for row in self.store.roster()
            if needle in (row.get("warning_status") or "").lower()
        ]

    def lowest_points(self, n: int = 1) -> List[dict]:
        def points(row: Dict[str, Any]) -> float:
            value = row.get("current_points")
            return float(value) if value is not None else 7.0

        return sorted(self.store.roster(), key=points)[: max(1, n)]

    def infractions(self, emp_id: str, year: Optional[int] = None) -> List[dict]:
        emp = self.store.get(emp_id) or {}
        result: List[dict] = []
        for entry in emp.get("history") or []:
            points = entry.get("points")
            if points is None or points >= 0 or entry.get("code") == "ROLL-ON":
                continue  # keep only real point-deducting infractions
            date = entry.get("date", "")
            if year is not None and not str(date).startswith(str(year)):
                continue
            result.append(
                {
                    "emp_id": emp_id,
                    "date": date,
                    "code": entry.get("code"),
                    "points": points,
                    "status": entry.get("status"),
                    "details": entry.get("details"),
                }
            )
        return result


TOOL_SPECS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_employee",
            "description": (
                "Get the full attendance/compliance record for one employee by "
                "ID (e.g. EMP101)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "emp_id": {
                        "type": "string",
                        "description": "Employee ID, e.g. EMP101.",
                    }
                },
                "required": ["emp_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "roster",
            "description": (
                "List every employee with id, name, role, department, "
                "current_points and warning_status."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_by_status",
            "description": (
                "List employees whose warning_status contains the given text "
                "(e.g. 'termination', 'written', 'good standing')."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Substring of the warning status to match.",
                    }
                },
                "required": ["status"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lowest_points",
            "description": (
                "Return the n employees with the lowest current point balances "
                "(most at risk of a warning or termination)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "n": {
                        "type": "integer",
                        "description": "How many employees to return (default 1).",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "infractions",
            "description": (
                "List point-deducting infractions for an employee, optionally "
                "filtered to a calendar year."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "emp_id": {
                        "type": "string",
                        "description": "Employee ID, e.g. EMP101.",
                    },
                    "year": {
                        "type": "integer",
                        "description": "Optional 4-digit year filter, e.g. 2025.",
                    },
                },
                "required": ["emp_id"],
            },
        },
    },
]


class ComplianceToolset:
    """Exposes ComplianceService methods as callable LLM tools."""

    def __init__(self, service: Any):
        self.service = service

    def specs(self) -> List[Dict[str, Any]]:
        """OpenAI-style function-calling tool specs."""
        return TOOL_SPECS

    def gemini_declarations(self) -> List[Dict[str, Any]]:
        """Gemini ``functionDeclarations`` (the specs without the type wrapper)."""
        return [spec["function"] for spec in TOOL_SPECS]

    def names(self) -> List[str]:
        return [spec["function"]["name"] for spec in TOOL_SPECS]

    def dispatch(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """Execute a named tool and return a JSON-serializable result."""
        args = arguments or {}
        if name == "get_employee":
            return self.service.get_employee(str(_require(args, "emp_id", name)))
        if name == "roster":
            return self.service.roster()
        if name == "list_by_status":
            return self.service.list_by_status(str(args.get("status", "")))
        if name == "lowest_points":
            return self.service.lowest_points(_as_int(args.get("n"), default=1))
        if name == "infractions":
            year = args.get("year")
            return self.service.infractions(
                str(_require(args, "emp_id", name)),
                _as_int(year, default=None) if year not in (None, "") else None,
            )
        raise ToolError(f"Unknown tool: {name}")


def _require(args: Dict[str, Any], key: str, tool: str) -> Any:
    if key not in args or args[key] in (None, ""):
        raise ToolError(f"Tool '{tool}' requires argument '{key}'.")
    return args[key]


def _as_int(value: Any, default: Optional[int]) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
