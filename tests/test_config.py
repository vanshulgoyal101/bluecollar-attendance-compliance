"""Tests for the policy configuration loader."""

from src.config import PolicyConfig


def test_defaults_load_from_config_yaml():
    cfg = PolicyConfig()
    assert cfg.start_points == 7.0
    assert cfg.roll_off_months == 12
    assert cfg.freeze_trigger == 1.0
    assert cfg.freeze_duration_months == 4


def test_warning_thresholds():
    cfg = PolicyConfig()
    assert cfg.warning_written == 2.0
    assert cfg.warning_termination_warning == 1.0
    assert cfg.warning_termination == 0.0


def test_infraction_deductions():
    cfg = PolicyConfig()
    assert cfg.get_deduction("IANS") == 3.0
    assert cfg.get_deduction("LTNC") == 2.0
    assert cfg.get_deduction("skp") == 1.0
    assert cfg.get_deduction("Lo") == 0.5
    assert cfg.get_deduction("skps") == 0.0
    assert cfg.lo_freebies == 3


def test_unknown_code_has_zero_deduction():
    assert PolicyConfig().get_deduction("NOPE") == 0.0
