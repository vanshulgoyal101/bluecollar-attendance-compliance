"""Tests for the Markdown report generator (IRM brief + warning letter)."""

import datetime

from src.report_generator import ComplianceReportGenerator


def _results():
    return {
        "current_points": 0.5,
        "history": [
            {
                "date": datetime.date(2025, 1, 10),
                "code": "IANS",
                "points_deducted": 3.0,
                "is_exempted": False,
                "roll_on_date": datetime.date(2026, 1, 10),
                "note": "No call no show.",
                "exempt_reason": None,
            },
            {
                "date": datetime.date(2025, 3, 4),
                "code": "skps",
                "points_deducted": 0.0,
                "is_exempted": True,
                "roll_on_date": datetime.date(2025, 3, 4),
                "note": "FMLA protected.",
                "exempt_reason": "FMLA protected sick leave",
            },
        ],
        "warnings": [
            {"date": datetime.date(2026, 2, 15), "level": "Termination Warning (<= 1.0)", "points": 0.5},
        ],
        "freeze_periods": [
            {"start": datetime.date(2026, 2, 15), "end": datetime.date(2100, 1, 1)},
        ],
    }


def test_irm_brief_has_core_sections_and_status():
    brief = ComplianceReportGenerator.generate_irm_brief("EMP101", _results())
    assert "# Investigative Review Meeting (IRM) Brief" in brief
    assert "**Employee ID:** EMP101" in brief
    assert "Termination Warning Active" in brief  # 0.5 pts -> termination warning
    assert "## Escalation & Warning Triggers" in brief
    assert "## Freeze Periods" in brief
    assert "## Detailed Infraction & Audit Trail" in brief


def test_irm_brief_lists_infractions_and_exemptions():
    brief = ComplianceReportGenerator.generate_irm_brief("EMP101", _results())
    assert "`IANS`" in brief
    assert "-3.0" in brief
    assert "FMLA protected sick leave" in brief
    # A freeze ending in the far future is still Active.
    assert "Active" in brief


def test_irm_brief_handles_empty_history():
    empty = {"current_points": 7.0, "history": [], "warnings": [], "freeze_periods": []}
    brief = ComplianceReportGenerator.generate_irm_brief("EMP110", empty)
    assert "Good Standing" in brief
    assert "*No compliance action thresholds crossed.*" in brief
    assert "*No freeze periods activated.*" in brief


def test_warning_letter_includes_level_and_points():
    letter = ComplianceReportGenerator.generate_warning_letter(
        "EMP104", "Written Warning (<= 2.0)", 1.5
    )
    assert "EMP104" in letter
    assert "Written Warning (<= 2.0)" in letter
    assert "1.5 Points" in letter
