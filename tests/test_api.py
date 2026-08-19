"""API route tests for server.py (Track C).

All tests inject a fake chatbot so nothing hits the network or requires keys.
"""

import json

import pytest

from server import create_app


class FakeClient:
    def is_configured(self):
        return False

    def provider_status(self):
        return []


class FakeChatbot:
    """Non-streaming fake: exercises /api/chat and the stream fallback path."""

    def __init__(self, answer_text="Fake answer about EMP101.", provider="offline"):
        self.client = FakeClient()
        self._answer = answer_text
        self._provider = provider
        self.last = None

    def answer(self, question, history=None):
        self.last = {"question": question, "history": history}
        return {
            "answer": self._answer,
            "provider": self._provider,
            "model": None,
            "grounded": True,
        }


class FakeStreamingChatbot(FakeChatbot):
    """Adds stream() so the SSE endpoint uses native streaming."""

    def __init__(self, chunks):
        super().__init__()
        self._chunks = chunks

    def stream(self, question, history=None):
        for chunk in self._chunks:
            yield chunk


def make_client(chatbot=None):
    app = create_app(chatbot=chatbot or FakeChatbot())
    app.testing = True
    return app.test_client()


def sse_events(body):
    events = []
    for frame in body.split("\n\n"):
        line = "".join(
            part[len("data:") :].strip()
            for part in frame.splitlines()
            if part.startswith("data:")
        )
        if line:
            events.append(json.loads(line))
    return events


# --- data endpoints ------------------------------------------------------- #


def test_employees_returns_full_roster():
    res = make_client().get("/api/employees")
    assert res.status_code == 200
    assert len(res.get_json()) == 10


def test_employee_by_id_ok():
    res = make_client().get("/api/employees/EMP101")
    assert res.status_code == 200
    assert res.get_json()["name"] == "Vanshul Goyal"


def test_employee_by_id_bad_format():
    assert make_client().get("/api/employees/not-an-id").status_code == 400


def test_employee_by_id_not_found():
    assert make_client().get("/api/employees/EMP999").status_code == 404


def test_health_reports_status_and_auth():
    data = make_client().get("/api/health").get_json()
    assert data["status"] == "ok"
    assert data["auth_required"] is False
    assert "providers" in data


def test_usage_snapshot_shape():
    data = make_client().get("/api/usage").get_json()
    for key in ("requests", "prompt_tokens", "completion_tokens", "by_provider"):
        assert key in data


# --- chat (non-streaming) ------------------------------------------------- #


def test_chat_returns_answer():
    res = make_client().post("/api/chat", json={"question": "Who is EMP101?"})
    assert res.status_code == 200
    assert res.get_json()["answer"] == "Fake answer about EMP101."


def test_chat_rejects_empty_question():
    assert make_client().post("/api/chat", json={"question": "  "}).status_code == 400


def test_chat_rejects_missing_question():
    assert make_client().post("/api/chat", json={}).status_code == 400


def test_chat_rejects_oversized_question():
    res = make_client().post("/api/chat", json={"question": "x" * 2001})
    assert res.status_code == 400


def test_chat_tolerates_bad_history_type():
    res = make_client().post(
        "/api/chat", json={"question": "hi", "history": "not-a-list"}
    )
    assert res.status_code == 200


def test_chat_bounds_history_length():
    bot = FakeChatbot()
    app = create_app(chatbot=bot)
    app.testing = True
    long_history = [{"role": "user", "content": str(i)} for i in range(50)]
    app.test_client().post(
        "/api/chat", json={"question": "hi", "history": long_history}
    )
    assert len(bot.last["history"]) == 12


# --- chat streaming (SSE) ------------------------------------------------- #


def test_chat_stream_fallback_chunks_answer():
    res = make_client().post("/api/chat/stream", json={"question": "hi"})
    assert res.status_code == 200
    assert res.mimetype == "text/event-stream"
    events = sse_events(res.get_data(as_text=True))
    text = "".join(e.get("delta", "") for e in events)
    assert "Fake answer about EMP101." in text
    assert events[-1].get("done") is True


def test_chat_stream_native_uses_chunks():
    client = make_client(FakeStreamingChatbot(["Hel", "lo ", "EMP101"]))
    res = client.post("/api/chat/stream", json={"question": "hi"})
    assert res.status_code == 200
    events = sse_events(res.get_data(as_text=True))
    text = "".join(e.get("delta", "") for e in events)
    assert text == "Hello EMP101"
    assert events[-1].get("done") is True


def test_chat_stream_validates_input():
    res = make_client().post("/api/chat/stream", json={"question": ""})
    assert res.status_code == 400


# --- IRM export ----------------------------------------------------------- #


def test_export_irm_returns_markdown_download():
    res = make_client().post("/api/export/irm", json={"employee_id": "EMP101"})
    assert res.status_code == 200
    assert res.mimetype == "text/markdown"
    assert "attachment" in res.headers["Content-Disposition"]
    assert "IRM_Brief_EMP101.md" in res.headers["Content-Disposition"]
    body = res.get_data(as_text=True)
    assert "Investigative Review Meeting" in body
    assert "EMP101" in body


def test_export_irm_rejects_bad_id():
    res = make_client().post("/api/export/irm", json={"employee_id": "bad;id"})
    assert res.status_code == 400


def test_export_irm_unknown_employee():
    res = make_client().post("/api/export/irm", json={"employee_id": "EMP999"})
    assert res.status_code == 404


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
