"""Minimal optional SQLite persistence layer (F-42).

This is an *optional* store: the JSON/CSV path remains the default and nothing
imports this module at runtime. It provides three tables — ``employees``,
``punches`` and ``notes`` — plus loaders from the existing CSV/JSON sources so
the same data can be queried with SQL. Foundation for a future Postgres move.
"""

import json
import os
import sqlite3
from typing import Any, Dict, List, Optional

from src.parser import DataIngestion

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DEFAULT_CSV_PATH = os.path.join(_DATA_DIR, "punch_logs.csv")
DEFAULT_NOTES_PATH = os.path.join(_DATA_DIR, "supervisor_notes.json")
DEFAULT_EMPLOYEES_PATH = os.path.join(_DATA_DIR, "employees.json")

SCHEMA = """
CREATE TABLE IF NOT EXISTS employees (
    id TEXT PRIMARY KEY,
    name TEXT,
    join_date TEXT,
    role TEXT,
    department TEXT,
    starting_points REAL,
    current_points REAL,
    warning_status TEXT
);
CREATE TABLE IF NOT EXISTS punches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT,
    date TEXT,
    base_code TEXT,
    actual_code TEXT
);
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT,
    date TEXT,
    note TEXT
);
CREATE INDEX IF NOT EXISTS idx_punches_emp ON punches(employee_id);
CREATE INDEX IF NOT EXISTS idx_notes_emp ON notes(employee_id);
"""


def connect(db_path: str = ":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def load_punches(conn: sqlite3.Connection, csv_path: str = DEFAULT_CSV_PATH) -> int:
    df = DataIngestion.load_punch_logs(csv_path)
    rows = [
        (r["employee_id"], r["date"].isoformat(), r["base_code"], r["actual_code"])
        for r in df.to_dict("records")
    ]
    conn.executemany(
        "INSERT INTO punches (employee_id, date, base_code, actual_code) VALUES (?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    return len(rows)


def load_notes(conn: sqlite3.Connection, notes_path: str = DEFAULT_NOTES_PATH) -> int:
    notes = DataIngestion.load_supervisor_notes(notes_path)
    rows = [(n["employee_id"], n["date"].isoformat(), n["note"]) for n in notes]
    conn.executemany(
        "INSERT INTO notes (employee_id, date, note) VALUES (?, ?, ?)", rows
    )
    conn.commit()
    return len(rows)


def load_employees(
    conn: sqlite3.Connection,
    employees: Optional[Dict[str, Dict[str, Any]]] = None,
    employees_path: str = DEFAULT_EMPLOYEES_PATH,
) -> int:
    if employees is None:
        with open(employees_path, "r") as f:
            employees = json.load(f)
    rows = [
        (
            emp_id,
            emp.get("name"),
            emp.get("join_date"),
            emp.get("role"),
            emp.get("department"),
            emp.get("starting_points"),
            emp.get("current_points"),
            emp.get("warning_status"),
        )
        for emp_id, emp in employees.items()
    ]
    conn.executemany(
        "INSERT OR REPLACE INTO employees "
        "(id, name, join_date, role, department, starting_points, current_points, warning_status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    return len(rows)


def build_database(
    db_path: str = ":memory:",
    csv_path: str = DEFAULT_CSV_PATH,
    notes_path: str = DEFAULT_NOTES_PATH,
    employees: Optional[Dict[str, Dict[str, Any]]] = None,
    employees_path: str = DEFAULT_EMPLOYEES_PATH,
) -> sqlite3.Connection:
    """Create (or open) a database and load all three tables from source data."""
    conn = connect(db_path)
    init_schema(conn)
    load_punches(conn, csv_path)
    load_notes(conn, notes_path)
    load_employees(conn, employees=employees, employees_path=employees_path)
    return conn


# --- query helpers ------------------------------------------------------- #


def all_employees(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    cur = conn.execute("SELECT * FROM employees ORDER BY id")
    return [dict(row) for row in cur.fetchall()]


def get_employee(conn: sqlite3.Connection, emp_id: str) -> Optional[Dict[str, Any]]:
    cur = conn.execute("SELECT * FROM employees WHERE id = ?", (emp_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def punches_for(conn: sqlite3.Connection, emp_id: str) -> List[Dict[str, Any]]:
    cur = conn.execute(
        "SELECT employee_id, date, base_code, actual_code FROM punches "
        "WHERE employee_id = ? ORDER BY date",
        (emp_id,),
    )
    return [dict(row) for row in cur.fetchall()]


def notes_for(conn: sqlite3.Connection, emp_id: str) -> List[Dict[str, Any]]:
    cur = conn.execute(
        "SELECT employee_id, date, note FROM notes WHERE employee_id = ? ORDER BY date",
        (emp_id,),
    )
    return [dict(row) for row in cur.fetchall()]
