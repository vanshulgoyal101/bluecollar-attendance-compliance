"""Attendance chatbot.

Answers natural-language questions about employee attendance and compliance.
The full (small) dataset is rendered to grounded text and passed to the LLM as
context; the model is instructed to answer only from that data. When no LLM
keys are configured, a deterministic offline fallback handles the common
question shapes so the feature still works.
"""

import json
from typing import Any, Dict, Iterator, List, Optional

from src.chat_store import ChatStore
from src.data_store import EmployeeDataStore
from src.llm import RotatingLLMClient
from src.llm.tools import ComplianceToolset, StubComplianceService, ToolError

TODAY = "2026-05-31"  # reference "today" the dashboard computes balances against

# Cap tool-calling round-trips so a misbehaving model can't loop forever.
MAX_TOOL_ROUNDS = 4

SYSTEM_PROMPT = f"""You are the Workforce Attendance & Compliance Assistant for a \
blue-collar operation. You answer HR and supervisor questions about employee \
attendance using ONLY the data provided below.

Treat today's date as {TODAY} when reasoning about recency, active freezes, or \
rolling 12-month windows.

Company "No-Fault" point policy (for interpreting the data):
- Everyone starts at 7.0 points. Infractions deduct points; deductions roll back \
on (recover) 12 months after the infraction date.
- Codes: skps=protected sick (0.0), skp=unprotected sick (1.0, consecutive days \
count once), LTDR=personal absence (1.0), IANS=no-call-no-show (3.0), \
LTNC=late-reported absence (2.0), LT=late >14min (0.5), Lo=late <=14min (0.5, \
first 3 per rolling 12 months are free "freebies").
- Warnings: <=2.0 pts Written Warning; <=1.0 pts Termination Warning + a 4-month \
roll-on freeze; <=0.0 pts Termination.

Rules for your answers:
- Use ONLY the DATA section. Never invent employees, dates, points or notes.
- If the answer is not in the data, say you don't have that information.
- Cite employee IDs (e.g. EMP101) and exact dates/points where relevant.
- Be concise and factual. Use short markdown lists or tables for multiple rows.
"""

TOOL_SYSTEM_PROMPT = f"""You are the Workforce Attendance & Compliance Assistant for a \
blue-collar operation. Answer HR and supervisor questions about employee attendance.

Treat today's date as {TODAY} when reasoning about recency, active freezes, or \
rolling 12-month windows.

You have tools that return authoritative compliance data (employee records, the \
roster, status filters, the lowest-point employees, and a person's infractions). \
Call the tools to fetch what you need, then answer ONLY from the tool results.
- Never invent employees, dates, points or notes. If the tools don't have it, \
say you don't have that information.
- Cite employee IDs (e.g. EMP101) and exact dates/points where relevant.
- Be concise and factual. Use short markdown lists or tables for multiple rows.
"""


class AttendanceChatbot:
    def __init__(
        self,
        store: Optional[EmployeeDataStore] = None,
        client: Optional[RotatingLLMClient] = None,
        chat_store: Optional[ChatStore] = None,
        toolset: Optional[ComplianceToolset] = None,
        use_tools: bool = False,
    ):
        self.store = store or EmployeeDataStore()
        self.client = client or RotatingLLMClient()
        # Optional audit log (F-34). Logging is a no-op when this is None.
        self.chat_store = chat_store
        # Optional function-calling toolset (F-40). Built lazily when use_tools.
        self.toolset = toolset
        self.use_tools = use_tools

    def answer(
        self, question: str, history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        question = (question or "").strip()
        if not question:
            return {
                "answer": "Ask me anything about employee attendance or compliance.",
                "provider": "none",
                "grounded": False,
                "suggestions": [],
            }

        if not self.client.is_configured():
            return self._finalize(question, self._offline_answer(question))

        if self._tools_enabled():
            result = self._answer_with_tools(question, history)
        else:
            result = self._answer_grounded(question, history)
        return self._finalize(question, result)

    def stream(
        self, question: str, history: Optional[List[Dict[str, str]]] = None
    ) -> Iterator[str]:
        """Yield the answer as text chunks (F-33), offline-safe.

        With no LLM keys, the deterministic offline answer is yielded as one
        chunk so callers get a uniform streaming interface either way.
        """
        question = (question or "").strip()
        if not question:
            yield "Ask me anything about employee attendance or compliance."
            return

        if not self.client.is_configured():
            result = self._offline_answer(question)
            yield result["answer"]
            self._maybe_log(question, result)
            return

        messages = self._build_messages(question, history)
        parts: List[str] = []
        for chunk in self.client.stream(messages):
            parts.append(chunk)
            yield chunk

        self._maybe_log(
            question,
            {
                "answer": "".join(parts),
                "provider": getattr(self.client, "last_provider", None) or "stream",
                "model": getattr(self.client, "last_model", None),
                "grounded": True,
            },
        )

    # ------------------------------------------------------------------ #
    # Grounded LLM path (full-context)                                    #
    # ------------------------------------------------------------------ #
    def _answer_grounded(
        self, question: str, history: Optional[List[Dict[str, str]]]
    ) -> Dict[str, Any]:
        messages = self._build_messages(question, history)
        result = self.client.complete(messages)
        return {
            "answer": result.text,
            "provider": result.provider,
            "model": result.model,
            "grounded": True,
        }

    def _build_messages(
        self, question: str, history: Optional[List[Dict[str, str]]]
    ) -> List[Dict[str, str]]:
        knowledge_base = self.store.build_knowledge_base(question)
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": f"{SYSTEM_PROMPT}\n\nDATA:\n{knowledge_base}"}
        ]
        for turn in history or []:
            role = turn.get("role")
            content = turn.get("content")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": question})
        return messages

    # ------------------------------------------------------------------ #
    # Tool / function-calling path (F-40)                                 #
    # ------------------------------------------------------------------ #
    def _tools_enabled(self) -> bool:
        return self.use_tools or self.toolset is not None

    def _get_toolset(self) -> ComplianceToolset:
        if self.toolset is None:
            self.toolset = ComplianceToolset(StubComplianceService(self.store))
        return self.toolset

    def _answer_with_tools(
        self, question: str, history: Optional[List[Dict[str, str]]]
    ) -> Dict[str, Any]:
        toolset = self._get_toolset()
        tools = toolset.specs()
        messages: List[Dict[str, Any]] = [
            {
                "role": "system",
                "content": f"{TOOL_SYSTEM_PROMPT}\n\nROSTER:\n"
                f"{self.store.roster_summary_text()}",
            }
        ]
        for turn in history or []:
            role = turn.get("role")
            content = turn.get("content")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": question})

        tools_used: List[str] = []
        for _ in range(MAX_TOOL_ROUNDS):
            completion = self.client.complete_tools(messages, tools)
            if not completion.tool_calls:
                return {
                    "answer": completion.text,
                    "provider": completion.provider,
                    "model": completion.model,
                    "grounded": True,
                    "tools_used": tools_used,
                }
            messages.append(
                {
                    "role": "assistant",
                    "content": completion.text or "",
                    "tool_calls": [
                        {"id": tc.id, "name": tc.name, "arguments": tc.arguments}
                        for tc in completion.tool_calls
                    ],
                }
            )
            for call in completion.tool_calls:
                tools_used.append(call.name)
                try:
                    output = toolset.dispatch(call.name, call.arguments)
                except ToolError as err:
                    output = {"error": str(err)}
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "name": call.name,
                        "content": json.dumps(output, default=str),
                    }
                )

        # Safety net: force a final answer without offering more tools.
        final = self.client.complete_tools(messages, [])
        return {
            "answer": final.text,
            "provider": final.provider,
            "model": final.model,
            "grounded": True,
            "tools_used": tools_used,
        }

    # ------------------------------------------------------------------ #
    # Offline fallback (no LLM keys configured)                           #
    # ------------------------------------------------------------------ #
    def _offline_answer(self, question: str) -> Dict[str, Any]:
        q = question.lower()
        roster = self.store.roster()

        mentioned = self.store.find_mentioned(question)
        if mentioned:
            body = "\n\n".join(
                self.store.employee_detail_text(emp_id) for emp_id in mentioned
            )
            return self._offline_result(body)

        def points(row: Dict[str, Any]) -> float:
            value = row.get("current_points")
            return float(value) if value is not None else 7.0

        if any(w in q for w in ("lowest", "worst", "least", "at risk", "risk of")):
            row = min(roster, key=points)
            return self._offline_result(
                f"Lowest balance: **{row['id']} {row['name']}** at "
                f"{row['current_points']} pts ({row['warning_status']})."
            )
        if any(w in q for w in ("highest", "best", "most points")):
            row = max(roster, key=points)
            return self._offline_result(
                f"Highest balance: **{row['id']} {row['name']}** at "
                f"{row['current_points']} pts ({row['warning_status']})."
            )

        status_filters = {
            "termination": "termination",
            "written warning": "written",
            "good standing": "good standing",
        }
        for phrase, needle in status_filters.items():
            if phrase in q:
                matches = [
                    r for r in roster if needle in r["warning_status"].lower()
                ]
                if not matches:
                    return self._offline_result(f"No employees are currently '{phrase}'.")
                body = "\n".join(
                    f"- {r['id']} {r['name']}: {r['warning_status']} "
                    f"({r['current_points']} pts)"
                    for r in matches
                )
                return self._offline_result(f"Employees ({phrase}):\n{body}")

        return self._offline_result(self.store.roster_summary_text())

    def _offline_result(self, body: str) -> Dict[str, Any]:
        note = (
            "_No LLM keys configured, so this is a direct data lookup. "
            "Add keys to `.env` for full conversational answers._"
        )
        return {
            "answer": f"{body}\n\n{note}",
            "provider": "offline",
            "grounded": True,
        }

    # ------------------------------------------------------------------ #
    # Follow-up suggestions (F-35) + audit logging (F-34)                 #
    # ------------------------------------------------------------------ #
    def _suggestions(self, question: str) -> List[str]:
        """2–3 deterministic, context-aware follow-up questions."""
        mentioned = self.store.find_mentioned(question)
        if mentioned:
            emp = mentioned[0]
            return [
                f"What infractions does {emp} have this year?",
                f"When do {emp}'s points roll back on?",
                f"Does {emp} have an active freeze?",
            ]
        q = question.lower()
        if any(w in q for w in ("lowest", "risk", "termination", "worst", "fire")):
            return [
                "Who is closest to a written warning?",
                "Show everyone with a termination warning.",
                "What are the point totals across the whole roster?",
            ]
        return [
            "Who has the lowest points?",
            "Who is at risk of termination?",
            "Show everyone in good standing.",
        ]

    def _finalize(self, question: str, result: Dict[str, Any]) -> Dict[str, Any]:
        result.setdefault("suggestions", self._suggestions(question))
        self._maybe_log(question, result)
        return result

    def _maybe_log(self, question: str, result: Dict[str, Any]) -> None:
        if not self.chat_store:
            return
        try:
            ids = self.store.find_mentioned(question)
            self.chat_store.log_query(question, result, employee_ids=ids or None)
        except Exception:
            # Audit logging must never break answering.
            pass

