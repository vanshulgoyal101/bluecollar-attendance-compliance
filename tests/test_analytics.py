"""Tests for the server-side analytics aggregation (F-45)."""

import server
from server import _analytics_from_records, create_app


SAMPLE = {
    "EMP1": {"name": "A", "department": "Logistics", "current_points": 0.0, "warning_status": "TERMINATION PROTOCOL TRIGGERED"},
    "EMP2": {"name": "B", "department": "Logistics", "current_points": 7.0, "warning_status": "Good Standing"},
    "EMP3": {"name": "C", "department": "Facilities", "current_points": 1.5, "warning_status": "Termination Warning Active"},
}


def test_analytics_totals_and_average():
    out = _analytics_from_records(SAMPLE)
    assert out["total_employees"] == 3
    assert out["at_risk_count"] == 2  # 0.0 and 1.5 are <= 2.0
    assert out["average_points"] == round((0.0 + 7.0 + 1.5) / 3, 2)


def test_analytics_departments_sorted_and_counted():
    out = _analytics_from_records(SAMPLE)
    depts = {d["department"]: d for d in out["departments"]}
    assert depts["Logistics"]["count"] == 2
    assert depts["Logistics"]["at_risk"] == 1
    assert depts["Facilities"]["avg_points"] == 1.5


def test_analytics_distribution_first_match_wins():
    out = _analytics_from_records(SAMPLE)
    counts = {b["label"]: b["count"] for b in out["distribution"]}
    assert counts["<=0 (Termination)"] == 1
    assert counts["1-2 (Written Warning)"] == 1
    assert counts["6-7 (Good Standing)"] == 1
    assert sum(counts.values()) == 3


def test_analytics_at_risk_sorted_ascending():
    out = _analytics_from_records(SAMPLE)
    pts = [r["current_points"] for r in out["at_risk"]]
    assert pts == sorted(pts)


def test_analytics_empty_records():
    out = _analytics_from_records({})
    assert out["total_employees"] == 0
    assert out["average_points"] == 0.0
    assert out["at_risk"] == []


def test_analytics_endpoint_returns_full_roster():
    app = create_app()
    client = app.test_client()
    resp = client.get("/api/analytics")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total_employees"] == 10
    assert len(data["distribution"]) == 6
    assert "departments" in data
