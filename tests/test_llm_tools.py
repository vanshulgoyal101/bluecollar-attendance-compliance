"""Tests for the function-calling tool layer (F-40).

Cover the ComplianceService stub, the toolset specs/dispatch, and the chatbot's
tool-calling loop driven by a fake client (no network).
"""

import pytest

from src.chatbot import AttendanceChatbot
from src.llm.rotating_client import ToolCall, ToolCompletion
from src.llm.tools import ComplianceToolset, StubComplianceService, ToolError


class FakeToolClient:
    """Returns scripted ToolCompletion responses on each complete_tools call."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def is_configured(self):
        return True

    def complete_tools(self, messages, tools, **kwargs):
        self.calls.append((messages, tools))
        return self.script.pop(0)


# --- Stub ComplianceService (contract 3.2) ------------------------------- #


def test_stub_get_employee_returns_record_with_id():
    svc = StubComplianceService()
    emp = svc.get_employee("EMP101")
    assert emp["id"] == "EMP101"
    assert emp["name"] == "Vanshul Goyal"
    assert svc.get_employee("NOPE") == {}


def test_stub_roster_shape():
    svc = StubComplianceService()
    roster = svc.roster()
    assert len(roster) == 10
    assert {"id", "name", "role", "department", "current_points", "warning_status"} <= set(
        roster[0]
    )


def test_stub_list_by_status_filters():
    svc = StubComplianceService()
    matches = svc.list_by_status("termination")
    assert matches
    assert all("termination" in r["warning_status"].lower() for r in matches)


def test_stub_lowest_points_sorted_ascending():
    svc = StubComplianceService()
    lowest = svc.lowest_points(3)
    points = [r["current_points"] for r in lowest]
    assert points == sorted(points)
    assert len(lowest) == 3


def test_stub_infractions_only_deductions_and_year_filter():
    svc = StubComplianceService()
    infractions = svc.infractions("EMP101", year=2023)
    assert infractions
    assert all(i["points"] < 0 for i in infractions)
    assert all(str(i["date"]).startswith("2023") for i in infractions)
    assert all(i["code"] != "ROLL-ON" for i in infractions)


# --- Toolset ------------------------------------------------------------- #


def test_specs_expose_all_five_tools():
    toolset = ComplianceToolset(StubComplianceService())
    assert set(toolset.names()) == {
        "get_employee",
        "roster",
        "list_by_status",
        "lowest_points",
        "infractions",
    }
    for spec in toolset.specs():
        assert spec["type"] == "function"
        assert "name" in spec["function"]
        assert "parameters" in spec["function"]


def test_gemini_declarations_unwrapped():
    toolset = ComplianceToolset(StubComplianceService())
    decls = toolset.gemini_declarations()
    assert {d["name"] for d in decls} == set(toolset.names())
    assert all("type" not in d or d.get("type") != "function" for d in decls)


def test_dispatch_routes_to_service():
    toolset = ComplianceToolset(StubComplianceService())
    assert toolset.dispatch("get_employee", {"emp_id": "EMP101"})["id"] == "EMP101"
    assert len(toolset.dispatch("lowest_points", {"n": 2})) == 2
    assert isinstance(toolset.dispatch("roster", {}), list)


def test_dispatch_unknown_tool_raises():
    toolset = ComplianceToolset(StubComplianceService())
    with pytest.raises(ToolError):
        toolset.dispatch("frobnicate", {})


def test_dispatch_missing_required_arg_raises():
    toolset = ComplianceToolset(StubComplianceService())
    with pytest.raises(ToolError):
        toolset.dispatch("get_employee", {})


# --- Chatbot tool loop --------------------------------------------------- #


def test_chatbot_tool_loop_executes_calls_and_grounds_answer():
    script = [
        ToolCompletion(
            text="",
            provider="groq",
            model="m",
            tool_calls=[ToolCall(id="c1", name="lowest_points", arguments={"n": 1})],
        ),
        ToolCompletion(
            text="EMP104 is most at risk at 0 pts.",
            provider="groq",
            model="m",
            tool_calls=[],
        ),
    ]
    client = FakeToolClient(script)
    bot = AttendanceChatbot(client=client, use_tools=True)

    result = bot.answer("Who is most at risk?")

    assert result["answer"] == "EMP104 is most at risk at 0 pts."
    assert result["tools_used"] == ["lowest_points"]
    assert result["grounded"] is True
    # The second round must carry the tool result back to the model.
    second_round_messages = client.calls[1][0]
    assert any(
        m.get("role") == "tool" and m.get("name") == "lowest_points"
        for m in second_round_messages
    )


def test_chatbot_tool_loop_handles_bad_tool_arguments():
    script = [
        ToolCompletion(
            text="",
            provider="groq",
            model="m",
            tool_calls=[ToolCall(id="c1", name="get_employee", arguments={})],
        ),
        ToolCompletion(
            text="I don't have that employee.",
            provider="groq",
            model="m",
            tool_calls=[],
        ),
    ]
    client = FakeToolClient(script)
    bot = AttendanceChatbot(client=client, use_tools=True)

    result = bot.answer("Tell me about someone")

    assert result["answer"] == "I don't have that employee."
    tool_msg = next(m for m in client.calls[1][0] if m.get("role") == "tool")
    assert "error" in tool_msg["content"]
