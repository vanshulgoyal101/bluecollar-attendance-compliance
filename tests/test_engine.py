import pytest
import pandas as pd
import datetime
from src.config import PolicyConfig
from src.engine import ComplianceEngine
from src.llm_client import ExceptionAnalysis


class FakeLLMClient:
    """Deterministic LLM stub for engine tests."""

    def __init__(self, exempt: bool, exception_type: str = "FMLA"):
        self._exempt = exempt
        self._type = exception_type

    def analyze_note(self, note_text: str, infraction_type: str) -> ExceptionAnalysis:
        return ExceptionAnalysis(
            is_exempt=self._exempt,
            reason="stubbed",
            exception_type=self._type if self._exempt else "None",
        )


@pytest.fixture
def policy_config():
    return PolicyConfig()

@pytest.fixture
def engine(policy_config):
    return ComplianceEngine(config=policy_config)

def test_basic_deductions(engine):
    # Test individual deductions
    punches = pd.DataFrame([
        {"employee_id": "EMP01", "date": datetime.date(2025, 1, 1), "base_code": "SW", "actual_code": "LTDR"}, # -1.0
        {"employee_id": "EMP01", "date": datetime.date(2025, 1, 2), "base_code": "SW", "actual_code": "LT"},   # -0.5
        {"employee_id": "EMP01", "date": datetime.date(2025, 1, 3), "base_code": "SW", "actual_code": "IANS"}, # -3.0
    ])
    
    results = engine.process_employee_compliance("EMP01", punches, [])
    # 7.0 - 1.0 - 0.5 - 3.0 = 2.5
    assert results["current_points"] == 2.5
    assert len(results["history"]) == 3

def test_consecutive_skp(engine):
    # Consecutive days of skp should only deduct 1.0 points in total
    punches = pd.DataFrame([
        {"employee_id": "EMP02", "date": datetime.date(2025, 2, 1), "base_code": "SW", "actual_code": "skp"},
        {"employee_id": "EMP02", "date": datetime.date(2025, 2, 2), "base_code": "SW", "actual_code": "skp"},
        {"employee_id": "EMP02", "date": datetime.date(2025, 2, 3), "base_code": "SW", "actual_code": "skp"},
    ])
    
    results = engine.process_employee_compliance("EMP02", punches, [])
    # Should only deduct 1.0 point total
    assert results["current_points"] == 6.0
    assert results["history"][0]["points_deducted"] == 1.0
    assert results["history"][1]["points_deducted"] == 0.0
    assert results["history"][2]["points_deducted"] == 0.0

def test_lo_freebies(engine):
    # First 3 Lo are freebies (0.0 points), 4th is deducted (0.5 points)
    punches = pd.DataFrame([
        {"employee_id": "EMP03", "date": datetime.date(2025, 1, 1), "base_code": "SW", "actual_code": "Lo"},
        {"employee_id": "EMP03", "date": datetime.date(2025, 2, 1), "base_code": "SW", "actual_code": "Lo"},
        {"employee_id": "EMP03", "date": datetime.date(2025, 3, 1), "base_code": "SW", "actual_code": "Lo"},
        {"employee_id": "EMP03", "date": datetime.date(2025, 4, 1), "base_code": "SW", "actual_code": "Lo"},
    ])
    
    results = engine.process_employee_compliance("EMP03", punches, [])
    # 7.0 - 0.5 (only the 4th is charged) = 6.5
    assert results["current_points"] == 6.5
    assert results["history"][0]["points_deducted"] == 0.0
    assert results["history"][1]["points_deducted"] == 0.0
    assert results["history"][2]["points_deducted"] == 0.0
    assert results["history"][3]["points_deducted"] == 0.5

def test_freeze_period_and_roll_on(engine):
    # 1. Day 1: IANS infraction (-3.0) -> balance = 4.0. Roll-on scheduled: Day 1 + 365.
    # 2. Day 2: IANS infraction (-3.0) -> balance = 1.0. This triggers freeze period (Day 2 to Day 2 + 120). Roll-on scheduled: Day 2 + 365.
    # 3. Day 366 (which is Day 1 + 365): The first infraction should roll on, but wait, the freeze period (Day 2 to Day 122) has already ended long ago!
    # Let's test a freeze period that overlaps with the roll-on of an infraction.
    # Say we get a deduction on 2025-01-01 (should roll on 2026-01-01).
    # We drop to <= 1.0 on 2025-11-01. Freeze active: 2025-11-01 to 2026-03-01.
    # On 2026-01-01, the first deduction's roll-on date is reached. But we are in freeze, so it doesn't roll on.
    # On 2026-03-02 (after freeze end), the roll-on should execute!
    punches = pd.DataFrame([
        {"employee_id": "EMP04", "date": datetime.date(2025, 1, 1), "base_code": "SW", "actual_code": "IANS"},   # -3.0
        {"employee_id": "EMP04", "date": datetime.date(2025, 11, 1), "base_code": "SW", "actual_code": "IANS"},  # -3.0, drops to 1.0, triggers freeze until 2026-03-01
        {"employee_id": "EMP04", "date": datetime.date(2026, 1, 1), "base_code": "SW", "actual_code": "SW"},     # Roll-on date of first IANS, but in freeze! No roll-on.
        {"employee_id": "EMP04", "date": datetime.date(2026, 3, 2), "base_code": "SW", "actual_code": "SW"},     # Day after freeze ended. The 2025-01-01 infraction should roll-on here!
    ])
    
    # Let's evaluate at 2026-01-01
    results_during_freeze = engine.process_employee_compliance("EMP04", punches[punches["date"] <= datetime.date(2026, 1, 1)], [])
    assert results_during_freeze["current_points"] == 1.0
    
    # Let's evaluate at 2026-03-02 (freeze ended)
    results_after_freeze = engine.process_employee_compliance("EMP04", punches, [])
    # 2025-01-01 infraction has rolled on (+3.0) -> 1.0 + 3.0 = 4.0
    assert results_after_freeze["current_points"] == 4.0


def test_empty_employee_starts_with_full_points(engine, policy_config):
    empty = pd.DataFrame(columns=["employee_id", "date", "base_code", "actual_code"])
    result = engine.process_employee_compliance("GHOST", empty, [])
    assert result["current_points"] == policy_config.start_points
    assert result["history"] == []


def test_supervisor_note_exempts_infraction(policy_config):
    engine = ComplianceEngine(config=policy_config, llm_client=FakeLLMClient(exempt=True))
    punches = pd.DataFrame([
        {"employee_id": "EMP10", "date": datetime.date(2025, 1, 1), "base_code": "SW", "actual_code": "IANS"},
    ])
    notes = [{"employee_id": "EMP10", "date": datetime.date(2025, 1, 1), "note": "On FMLA leave"}]

    result = engine.process_employee_compliance("EMP10", punches, notes)
    # Exempt -> no deduction, points remain full.
    assert result["current_points"] == policy_config.start_points
    assert result["history"][0]["points_deducted"] == 0.0
    assert result["history"][0]["is_exempted"] is True


def test_non_exempt_note_still_deducts(policy_config):
    engine = ComplianceEngine(config=policy_config, llm_client=FakeLLMClient(exempt=False))
    punches = pd.DataFrame([
        {"employee_id": "EMP11", "date": datetime.date(2025, 1, 1), "base_code": "SW", "actual_code": "IANS"},
    ])
    notes = [{"employee_id": "EMP11", "date": datetime.date(2025, 1, 1), "note": "No valid reason"}]

    result = engine.process_employee_compliance("EMP11", punches, notes)
    assert result["current_points"] == policy_config.start_points - 3.0


def test_points_never_go_below_zero(policy_config):
    engine = ComplianceEngine(config=policy_config, llm_client=FakeLLMClient(exempt=False))
    # Many severe infractions on consecutive days should floor at 0, not go negative.
    rows = [
        {"employee_id": "EMP12", "date": datetime.date(2025, 1, d), "base_code": "SW", "actual_code": "IANS"}
        for d in range(1, 6)
    ]
    result = engine.process_employee_compliance("EMP12", pd.DataFrame(rows), [])
    assert result["current_points"] == 0.0
    assert result["current_points"] >= 0.0


def test_warning_thresholds_are_recorded(engine):
    punches = pd.DataFrame([
        {"employee_id": "EMP13", "date": datetime.date(2025, 1, 1), "base_code": "SW", "actual_code": "IANS"},  # 7->4
        {"employee_id": "EMP13", "date": datetime.date(2025, 1, 2), "base_code": "SW", "actual_code": "IANS"},  # 4->1
    ])
    result = engine.process_employee_compliance("EMP13", punches, [])
    assert len(result["warnings"]) >= 1
    # Dropping to 1.0 should trigger a freeze period.
    assert len(result["freeze_periods"]) >= 1

