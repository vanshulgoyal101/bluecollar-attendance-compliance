"""Web server for the attendance dashboard + chatbot.

Serves the static dashboard and exposes a small JSON API. Track C owns all the
route wiring here; the chatbot, data store, LLM usage metering and report
generator are consumed through their stable contracts (see
``docs/PARALLEL_WORK_PLAN.md`` §3):

- GET  /                     -> dashboard (auth-gated when a token is configured)
- GET  /login                -> login page (public)
- POST /api/login            -> exchange a token for a session cookie
- POST /api/logout           -> clear the session
- GET  /api/employees        -> the canonical employee dataset
- GET  /api/employees/<id>   -> a single employee (live record via ComplianceService)
- GET  /api/health           -> configured LLM providers + auth status (public)
- GET  /api/usage            -> LLM usage snapshot (contract 3.4)
- GET  /api/analytics        -> department / at-risk / points-distribution stats (F-45)
- POST /api/chat             -> {question, history?} -> grounded answer
- POST /api/chat/stream      -> Server-Sent Events stream of the answer (contract 3.3)
- POST /api/export/irm       -> {employee_id} -> downloadable IRM brief (Markdown)
"""

import datetime
import hmac
import json
import os
import re
from typing import Any, Dict, Iterable, Iterator, List, Optional

from flask import (
    Flask,
    Response,
    jsonify,
    redirect,
    request,
    send_from_directory,
    session,
    stream_with_context,
)

from src.chatbot import AttendanceChatbot
from src.data_store import EmployeeDataStore
from src.report_generator import ComplianceReportGenerator

# --- LLM usage metering (contract 3.4, owned by Track B) --------------------- #
# Wire against the contract; fall back to a zeroed snapshot until B lands it so
# the endpoint always works offline.
try:  # pragma: no cover - exercised indirectly
    from src.llm.usage import usage_snapshot as _usage_snapshot
except Exception:  # noqa: BLE001 - any import failure -> use the local stub

    def _usage_snapshot() -> Dict[str, Any]:
        return {
            "requests": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "by_provider": {},
        }


# --- Live employee record (contract 3.2, owned by Track A) ------------------- #
try:  # pragma: no cover - exercised indirectly
    from src.compliance_service import ComplianceService as _ComplianceService
except Exception:  # noqa: BLE001
    _ComplianceService = None


DASHBOARD_DIR = os.path.join(os.path.dirname(__file__), "dashboard")
MAX_QUESTION_LEN = 2000
MAX_HISTORY_TURNS = 12
STREAM_CHUNK_SIZE = 60
EMP_ID_RE = re.compile(r"^EMP\d{2,6}$")

# Points-distribution buckets for /api/analytics, evaluated top-down (first match
# wins) so they mirror the dashboard's Analytics view exactly.
POINT_BUCKETS = (
    ("<=0 (Termination)", lambda p: p <= 0),
    ("0-1 (Termination Warning)", lambda p: p <= 1),
    ("1-2 (Written Warning)", lambda p: p <= 2),
    ("2-4", lambda p: p <= 4),
    ("4-6", lambda p: p <= 6),
    ("6-7 (Good Standing)", lambda p: True),
)

# Endpoints reachable without a session (login flow + liveness probe).
PUBLIC_PATHS = frozenset({"/login", "/api/login", "/api/health", "/favicon.ico"})


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes", "on")


def _sse(payload: Dict[str, Any]) -> str:
    """Encode one Server-Sent Event frame (JSON keeps newlines SSE-safe)."""
    return f"data: {json.dumps(payload)}\n\n"


def _to_date(value: Any) -> datetime.date:
    try:
        return datetime.date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return datetime.date.today()


def _results_from_record(emp: Dict[str, Any]) -> Dict[str, Any]:
    """Adapt a stored/live employee record into the engine-results shape the
    report generator expects. Recovery (roll-on) rows are dropped so the brief's
    audit trail lists infractions only."""
    history: List[Dict[str, Any]] = []
    for h in emp.get("history", []) or []:
        code = h.get("code", "")
        points = h.get("points", 0) or 0
        if code == "ROLL-ON" or points > 0:
            continue
        exempted = points == 0 or "exempt" in str(h.get("status", "")).lower()
        history.append(
            {
                "date": h.get("date"),
                "code": code,
                "points_deducted": (-points if points < 0 else 0),
                "is_exempted": exempted,
                "roll_on_date": h.get("roll_on"),
                "note": h.get("details"),
                "exempt_reason": h.get("details") if exempted else None,
            }
        )

    freeze_periods = [
        {"start": _to_date(f.get("start")), "end": _to_date(f.get("end"))}
        for f in (emp.get("freeze_history") or [])
    ]

    return {
        "current_points": emp.get("current_points"),
        "history": history,
        "warnings": emp.get("warnings") or [],
        "freeze_periods": freeze_periods,
    }


def _analytics_from_records(records: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate department, at-risk and points-distribution stats (F-45).

    Computed server-side from the canonical records so the figures match the
    dashboard and are available programmatically. ``at_risk`` is <= 2.0 points.
    """
    rows: List[Dict[str, Any]] = []
    for emp_id, emp in (records or {}).items():
        pts = emp.get("current_points")
        rows.append(
            {
                "id": emp_id,
                "name": emp.get("name", ""),
                "department": emp.get("department") or "Unassigned",
                "warning_status": emp.get("warning_status", ""),
                "current_points": float(pts) if pts is not None else 7.0,
            }
        )

    total = len(rows)
    at_risk = sorted(
        (r for r in rows if r["current_points"] <= 2.0),
        key=lambda r: r["current_points"],
    )
    avg = round(sum(r["current_points"] for r in rows) / total, 2) if total else 0.0

    dept: Dict[str, Dict[str, float]] = {}
    for r in rows:
        bucket = dept.setdefault(r["department"], {"count": 0, "sum": 0.0, "at_risk": 0})
        bucket["count"] += 1
        bucket["sum"] += r["current_points"]
        if r["current_points"] <= 2.0:
            bucket["at_risk"] += 1
    departments = [
        {
            "department": name,
            "count": int(b["count"]),
            "avg_points": round(b["sum"] / b["count"], 2) if b["count"] else 0.0,
            "at_risk": int(b["at_risk"]),
        }
        for name, b in sorted(dept.items())
    ]

    distribution = [{"label": label, "count": 0} for label, _ in POINT_BUCKETS]
    for r in rows:
        for i, (_, test) in enumerate(POINT_BUCKETS):
            if test(r["current_points"]):
                distribution[i]["count"] += 1
                break

    return {
        "total_employees": total,
        "at_risk_count": len(at_risk),
        "average_points": avg,
        "departments": departments,
        "distribution": distribution,
        "at_risk": at_risk,
    }


def _iter_stream(
    chatbot: Any, question: str, history: List[Dict[str, str]]
) -> Iterator[Dict[str, Any]]:
    """Yield SSE payload dicts for a streamed answer.

    Uses ``chatbot.stream`` (contract 3.3) when available and falls back to
    chunking a non-streaming ``answer`` so the endpoint works before Track B
    lands real streaming.
    """
    meta: Dict[str, Any] = {"provider": "stream", "model": None}
    stream = getattr(chatbot, "stream", None)
    if callable(stream):
        for chunk in stream(question, history=history):
            if chunk:
                yield {"delta": str(chunk)}
    else:
        result = chatbot.answer(question, history=history)
        meta["provider"] = result.get("provider", "offline")
        meta["model"] = result.get("model")
        text = result.get("answer", "")
        for i in range(0, len(text), STREAM_CHUNK_SIZE):
            yield {"delta": text[i : i + STREAM_CHUNK_SIZE]}
    yield {"done": True, **meta}


def create_app(
    chatbot: Optional[Any] = None, store: Optional[EmployeeDataStore] = None
) -> Flask:
    app = Flask(__name__, static_folder=DASHBOARD_DIR, static_url_path="")
    app.secret_key = os.getenv("APP_SECRET_KEY") or os.urandom(32)

    store = store or EmployeeDataStore()
    chatbot = chatbot or AttendanceChatbot(store=store)
    compliance = _ComplianceService() if _ComplianceService else None

    app.config["AUTH_TOKEN"] = os.getenv("APP_AUTH_TOKEN", "").strip()
    app.config["AUTH_DEV_BYPASS"] = _env_flag("AUTH_DEV_BYPASS")

    # ---------------------------------------------------------------- auth --- #
    def auth_enabled() -> bool:
        return bool(app.config["AUTH_TOKEN"]) and not app.config["AUTH_DEV_BYPASS"]

    def _request_token() -> str:
        header = request.headers.get("Authorization", "")
        if header.startswith("Bearer "):
            return header[len("Bearer ") :].strip()
        return request.headers.get("X-Auth-Token", "").strip()

    def _token_ok(token: str) -> bool:
        expected = app.config["AUTH_TOKEN"]
        return bool(token) and hmac.compare_digest(token, expected)

    @app.before_request
    def _guard():
        if not auth_enabled():
            return None
        if request.path in PUBLIC_PATHS:
            return None
        if session.get("authed") or _token_ok(_request_token()):
            return None
        if request.path.startswith("/api/"):
            return jsonify({"error": "Unauthorized"}), 401
        return redirect("/login")

    @app.get("/login")
    def login_page():
        return send_from_directory(DASHBOARD_DIR, "login.html")

    @app.post("/api/login")
    def api_login():
        payload = request.get_json(silent=True) or {}
        token = payload.get("token", "")
        if not isinstance(token, str) or not _token_ok(token.strip()):
            return jsonify({"error": "Invalid token."}), 401
        session["authed"] = True
        return jsonify({"ok": True})

    @app.post("/api/logout")
    def api_logout():
        session.clear()
        return jsonify({"ok": True})

    # ------------------------------------------------------------- static --- #
    @app.get("/")
    def index():
        return send_from_directory(DASHBOARD_DIR, "index.html")

    # ---------------------------------------------------------------- data --- #
    @app.get("/api/employees")
    def api_employees():
        return jsonify(store.all())

    @app.get("/api/employees/<emp_id>")
    def api_employee(emp_id: str):
        if not EMP_ID_RE.match(emp_id):
            return jsonify({"error": "Invalid employee id."}), 400
        record = None
        if compliance is not None:
            try:
                record = compliance.get_employee(emp_id)
            except Exception:  # noqa: BLE001 - fall back to the static store
                record = None
        if record is None:
            record = store.get(emp_id)
        if not record:
            return jsonify({"error": f"No record for {emp_id}."}), 404
        return jsonify(record)

    @app.get("/api/health")
    def api_health():
        return jsonify(
            {
                "status": "ok",
                "llm_configured": chatbot.client.is_configured(),
                "providers": chatbot.client.provider_status(),
                "auth_required": auth_enabled(),
            }
        )

    @app.get("/api/usage")
    def api_usage():
        try:
            snapshot = _usage_snapshot()
        except Exception:  # noqa: BLE001
            app.logger.exception("usage_snapshot failed")
            snapshot = {
                "requests": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "by_provider": {},
            }
        return jsonify(snapshot)

    @app.get("/api/analytics")
    def api_analytics():
        records: Optional[Dict[str, Any]] = None
        if compliance is not None:
            try:
                records = compliance.all_records()
            except Exception:  # noqa: BLE001 - fall back to the static store
                records = None
        if records is None:
            records = store.all()
        return jsonify(_analytics_from_records(records))

    # ---------------------------------------------------------------- chat --- #
    def _validate_chat(payload: Dict[str, Any]):
        question = payload.get("question", "")
        history = payload.get("history", [])
        if not isinstance(question, str) or not question.strip():
            return None, None, ("A non-empty 'question' string is required.", 400)
        if len(question) > MAX_QUESTION_LEN:
            return None, None, ("Question is too long.", 400)
        if not isinstance(history, list):
            history = []
        return question, history[-MAX_HISTORY_TURNS:], None

    @app.post("/api/chat")
    def api_chat():
        question, history, err = _validate_chat(request.get_json(silent=True) or {})
        if err:
            return jsonify({"error": err[0]}), err[1]
        try:
            result = chatbot.answer(question, history=history)
        except Exception as exc:  # noqa: BLE001 - surface a clean error to the UI
            app.logger.exception("Chat request failed")
            return jsonify({"error": f"Chat failed: {exc}"}), 502
        return jsonify(result)

    @app.post("/api/chat/stream")
    def api_chat_stream():
        question, history, err = _validate_chat(request.get_json(silent=True) or {})
        if err:
            return jsonify({"error": err[0]}), err[1]

        @stream_with_context
        def generate() -> Iterable[str]:
            try:
                for payload in _iter_stream(chatbot, question, history):
                    yield _sse(payload)
            except Exception as exc:  # noqa: BLE001
                app.logger.exception("Chat stream failed")
                yield _sse({"error": f"Chat failed: {exc}"})
                yield _sse({"done": True, "provider": "error", "model": None})

        return Response(
            generate(),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    # -------------------------------------------------------------- export --- #
    @app.post("/api/export/irm")
    def api_export_irm():
        payload = request.get_json(silent=True) or {}
        emp_id = payload.get("employee_id", "")
        if not isinstance(emp_id, str) or not EMP_ID_RE.match(emp_id.strip()):
            return (
                jsonify({"error": "A valid 'employee_id' (e.g. EMP101) is required."}),
                400,
            )
        emp_id = emp_id.strip()
        record = store.get(emp_id)
        if not record:
            return jsonify({"error": f"No record for {emp_id}."}), 404
        brief = ComplianceReportGenerator.generate_irm_brief(
            emp_id, _results_from_record(record)
        )
        return Response(
            brief,
            mimetype="text/markdown",
            headers={
                "Content-Disposition": f'attachment; filename="IRM_Brief_{emp_id}.md"'
            },
        )

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5001"))
    app.run(host="127.0.0.1", port=port, debug=True)
