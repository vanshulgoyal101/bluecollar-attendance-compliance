"""Tests for the optional SQLite persistence layer (F-42)."""

import json

import pytest

from src import db


@pytest.fixture
def conn():
    connection = db.build_database(":memory:")
    yield connection
    connection.close()


def test_schema_and_employee_load(conn):
    employees = db.all_employees(conn)
    assert len(employees) == 10
    ids = {e["id"] for e in employees}
    assert {"EMP101", "EMP110"}.issubset(ids)


def test_get_employee_returns_row(conn):
    emp = db.get_employee(conn, "EMP101")
    assert emp is not None
    assert emp["name"] == "Vanshul Goyal"
    assert emp["current_points"] is not None


def test_get_unknown_employee_returns_none(conn):
    assert db.get_employee(conn, "EMP999") is None


def test_punches_loaded_and_queryable(conn):
    punches = db.punches_for(conn, "EMP101")
    assert len(punches) >= 10
    assert all(p["employee_id"] == "EMP101" for p in punches)
    assert punches == sorted(punches, key=lambda p: p["date"])


def test_notes_loaded(conn):
    notes = db.notes_for(conn, "EMP106")
    assert len(notes) == 3
    assert all("FMLA" in n["note"] or "protected" in n["note"].lower() for n in notes)


def test_build_database_persists_to_file(tmp_path):
    db_path = tmp_path / "attendance.db"
    conn = db.build_database(str(db_path))
    conn.close()
    assert db_path.exists()

    reopened = db.connect(str(db_path))
    try:
        assert len(db.all_employees(reopened)) == 10
    finally:
        reopened.close()


def test_load_employees_accepts_explicit_dict():
    conn = db.connect(":memory:")
    try:
        db.init_schema(conn)
        payload = {
            "EMP900": {
                "name": "Test User",
                "join_date": "2025-01-01",
                "role": "Tester",
                "department": "QA",
                "starting_points": 7.0,
                "current_points": 6.0,
                "warning_status": "Good Standing",
            }
        }
        count = db.load_employees(conn, employees=payload)
        assert count == 1
        assert db.get_employee(conn, "EMP900")["current_points"] == 6.0
    finally:
        conn.close()
