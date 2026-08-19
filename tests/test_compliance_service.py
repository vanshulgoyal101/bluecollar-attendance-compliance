"""Tests for the engine-backed ComplianceService (F-31)."""

import datetime

import pytest

from src.compliance_service import ComplianceService

REQUIRED_KEYS = {
    "name", "join_date", "role", "department", "starting_points",
    "current_points", "warning_status", "fmla_approved_cases", "excused_absences",
    "freebies_used", "sick_balance_hours", "vacation_hours", "freeze_history",
    "schedule", "history", "warnings",
}

EXPECTED_POINTS = {
    "EMP101": 0.5, "EMP102": 7.0, "EMP103": 7.0, "EMP104": 1.0, "EMP105": 0.0,
    "EMP106": 7.0, "EMP107": 6.5, "EMP108": 4.5, "EMP109": 7.0, "EMP110": 7.0,
}


@pytest.fixture(scope="module")
def service():
    return ComplianceService()


def test_roster_has_ten_employees_with_stable_shape(service):
    roster = service.roster()
    assert len(roster) == 10
    for row in roster:
        assert set(row) == {"id", "name", "role", "department", "current_points", "warning_status"}


def test_get_employee_returns_record_with_required_keys(service):
    rec = service.get_employee("EMP101")
    assert REQUIRED_KEYS.issubset(rec.keys())
    assert rec["name"] == "Vanshul Goyal"


@pytest.mark.parametrize("emp_id,points", EXPECTED_POINTS.items())
def test_live_points_match_expected(service, emp_id, points):
    assert service.get_employee(emp_id)["current_points"] == points


def test_history_final_balance_equals_current_points(service):
    for emp_id in service.employee_ids():
        rec = service.get_employee(emp_id)
        if rec["history"]:
            assert rec["history"][-1]["balance"] == rec["current_points"]


def test_warning_status_reflects_points(service):
    assert service.get_employee("EMP105")["warning_status"] == "TERMINATION PROTOCOL TRIGGERED"
    assert service.get_employee("EMP101")["warning_status"] == "Termination Warning Active"
    assert service.get_employee("EMP102")["warning_status"] == "Good Standing"


def test_active_freeze_is_reported(service):
    freezes = service.get_employee("EMP101")["freeze_history"]
    assert freezes and freezes[-1]["status"] == "Active"
    assert freezes[-1]["start"] == "2026-02-15"


def test_list_by_status_filters(service):
    at_risk = {r["id"] for r in service.list_by_status("termination")}
    assert {"EMP101", "EMP104", "EMP105"}.issubset(at_risk)
    assert "EMP102" not in at_risk


def test_lowest_points_is_sorted_ascending(service):
    lowest = service.lowest_points(3)
    assert [r["id"] for r in lowest] == ["EMP105", "EMP101", "EMP104"]
    assert lowest[0]["current_points"] == 0.0


def test_infractions_can_filter_by_year(service):
    all_106 = service.infractions("EMP106")
    assert len(all_106) == 3
    assert all(i["exempt"] for i in all_106)
    only_2024 = service.infractions("EMP106", year=2024)
    assert len(only_2024) == 2
    assert {i["date"][:4] for i in only_2024} == {"2024"}


def test_unknown_employee_raises(service):
    with pytest.raises(KeyError):
        service.get_employee("EMP999")


def test_as_of_controls_roll_on_recovery():
    # EMP102's two infractions roll on Jan 2026; before then the balance is low.
    before = ComplianceService(as_of=datetime.date(2025, 6, 1)).get_employee("EMP102")
    after = ComplianceService(as_of=datetime.date(2026, 5, 31)).get_employee("EMP102")
    assert before["current_points"] == 2.0
    assert after["current_points"] == 7.0


def test_fmla_and_excused_metadata_preserved(service):
    assert service.get_employee("EMP106")["fmla_approved_cases"] == 3
    assert service.get_employee("EMP108")["excused_absences"] == 1
