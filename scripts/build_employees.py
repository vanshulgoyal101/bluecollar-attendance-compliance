#!/usr/bin/env python3
"""Regenerate the canonical ``data/employees.json`` from source data (F-30).

Runs :class:`ComplianceService` over ``punch_logs.csv`` + ``supervisor_notes.json``
+ ``employees_meta.json`` and writes a canonical, deterministic JSON file. The
output is stable (sorted keys, fixed indent) so the build is idempotent and can
be verified in CI.

Usage::

    python scripts/build_employees.py            # (re)write data/employees.json
    python scripts/build_employees.py --check     # exit 1 if the file is stale
    python scripts/build_employees.py --sqlite data/attendance.db   # also emit a DB
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.compliance_service import ComplianceService  # noqa: E402

DEFAULT_OUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "employees.json"
)


def build_dataset(service: ComplianceService | None = None) -> dict:
    service = service or ComplianceService()
    return service.all_records()


def canonical_json(data: dict) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _read(path: str) -> str | None:
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return f.read()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build canonical employees.json")
    parser.add_argument("--out", default=DEFAULT_OUT, help="output path")
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the committed file is up to date; exit 1 if stale",
    )
    parser.add_argument(
        "--sqlite",
        metavar="PATH",
        help="also load the freshly built data into a SQLite database at PATH",
    )
    args = parser.parse_args(argv)

    service = ComplianceService()
    text = canonical_json(build_dataset(service))

    if args.check:
        current = _read(args.out)
        if current == text:
            print(f"OK: {args.out} is up to date.")
            return 0
        print(
            f"STALE: {args.out} is out of date. Run scripts/build_employees.py to regenerate.",
            file=sys.stderr,
        )
        return 1

    with open(args.out, "w") as f:
        f.write(text)
    print(f"Wrote {len(service.employee_ids())} employees to {args.out}")

    if args.sqlite:
        from src import db

        conn = db.build_database(args.sqlite, employees=json.loads(text))
        conn.close()
        print(f"Wrote SQLite database to {args.sqlite}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
