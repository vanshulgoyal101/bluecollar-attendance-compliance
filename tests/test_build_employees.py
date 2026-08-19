"""Tests for the canonical dataset builder (F-30)."""

import json
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

import build_employees  # noqa: E402

from src.compliance_service import ComplianceService  # noqa: E402
from src.data_store import EmployeeDataStore  # noqa: E402


def test_build_dataset_has_ten_valid_records():
    data = build_employees.build_dataset()
    assert len(data) == 10
    for rec in data.values():
        assert "current_points" in rec
        assert "warning_status" in rec
        assert isinstance(rec["history"], list)


def test_canonical_json_is_deterministic():
    data = build_employees.build_dataset()
    assert build_employees.canonical_json(data) == build_employees.canonical_json(data)


def test_generated_records_match_service():
    data = build_employees.build_dataset()
    service = ComplianceService()
    assert data["EMP105"] == service.get_employee("EMP105")


def test_committed_employees_json_is_up_to_date():
    # Guards against a stale data/employees.json slipping into the repo.
    assert build_employees.main(["--check"]) == 0


def test_check_mode_detects_staleness(tmp_path):
    out = tmp_path / "employees.json"
    assert build_employees.main(["--out", str(out)]) == 0
    assert build_employees.main(["--check", "--out", str(out)]) == 0

    out.write_text('{"stale": true}\n')
    assert build_employees.main(["--check", "--out", str(out)]) == 1


def test_written_file_loads_via_data_store(tmp_path):
    out = tmp_path / "employees.json"
    build_employees.main(["--out", str(out)])
    store = EmployeeDataStore(path=str(out))
    assert len(store.roster()) == 10
    assert store.get("EMP101")["name"] == "Vanshul Goyal"
    # The knowledge base still renders for grounding.
    assert "ROSTER" in store.build_knowledge_base("EMP101")
