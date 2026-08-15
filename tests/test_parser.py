"""Tests for the data-ingestion parser (CSV punch logs and JSON supervisor notes)."""

import datetime
import json

import pytest

from src.parser import DataIngestion


def test_load_punch_logs_parses_and_normalizes(tmp_path):
    csv = tmp_path / "punches.csv"
    csv.write_text(
        "employee_id,date,base_code,actual_code\n"
        "42,2025-01-01,SW,LT\n"
        "42,2025-01-02,SW,SW\n"
    )
    df = DataIngestion.load_punch_logs(str(csv))
    assert list(df.columns) >= ["employee_id", "date", "base_code", "actual_code"]
    # employee_id is coerced to string; date to python date objects.
    assert df["employee_id"].iloc[0] == "42"
    assert df["date"].iloc[0] == datetime.date(2025, 1, 1)


def test_load_punch_logs_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        DataIngestion.load_punch_logs(str(tmp_path / "nope.csv"))


def test_load_punch_logs_missing_columns_raises(tmp_path):
    csv = tmp_path / "bad.csv"
    csv.write_text("employee_id,date\n1,2025-01-01\n")
    with pytest.raises(ValueError, match="must contain columns"):
        DataIngestion.load_punch_logs(str(csv))


def test_load_supervisor_notes_normalizes_types(tmp_path):
    path = tmp_path / "notes.json"
    json.dump(
        [{"employee_id": 42, "date": "2025-01-01", "note": "On FMLA"}],
        path.open("w"),
    )
    notes = DataIngestion.load_supervisor_notes(str(path))
    assert notes[0]["employee_id"] == "42"
    assert notes[0]["date"] == datetime.date(2025, 1, 1)
    assert notes[0]["note"] == "On FMLA"


def test_load_supervisor_notes_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        DataIngestion.load_supervisor_notes(str(tmp_path / "missing.json"))
