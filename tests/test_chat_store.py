"""Tests for the conversation/query audit log (F-34)."""

import json

from src.chat_store import ChatStore
from src.chatbot import AttendanceChatbot


class OfflineClient:
    """A client that reports no keys, forcing the deterministic offline path."""

    def is_configured(self):
        return False


def test_log_query_appends_one_jsonl_record(tmp_path):
    path = tmp_path / "chat_log.jsonl"
    store = ChatStore(path=str(path))

    record = store.log_query(
        "How is EMP101 doing?",
        {
            "answer": "He has 0.5 pts",
            "provider": "google",
            "model": "gemini-2.0-flash",
            "grounded": True,
            "suggestions": ["a", "b"],
        },
    )

    assert path.exists()
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["question"] == "How is EMP101 doing?"
    assert data["employee_ids"] == ["EMP101"]
    assert data["provider"] == "google"
    assert data["model"] == "gemini-2.0-flash"
    assert data["grounded"] is True
    assert data["answer_chars"] == len("He has 0.5 pts")
    assert data["suggestions"] == 2
    assert data["conversation_id"] == record["conversation_id"]
    # Full answer text is not persisted, only its length (no derived PII).
    assert "answer" not in data


def test_log_is_append_only(tmp_path):
    path = tmp_path / "chat_log.jsonl"
    store = ChatStore(path=str(path))

    store.log_query("about EMP102", {"answer": "x", "provider": "offline", "grounded": True})
    store.log_query("no ids here", {"answer": "y", "provider": "offline", "grounded": True})

    records = store.read_all()
    assert len(records) == 2
    assert records[0]["employee_ids"] == ["EMP102"]
    assert records[1]["employee_ids"] == []


def test_extract_employee_ids_dedups_and_uppercases():
    assert ChatStore.extract_employee_ids("emp101, EMP101 and EMP103") == [
        "EMP101",
        "EMP103",
    ]
    assert ChatStore.extract_employee_ids("") == []


def test_read_all_missing_file_returns_empty(tmp_path):
    store = ChatStore(path=str(tmp_path / "does_not_exist.jsonl"))
    assert store.read_all() == []


def test_read_all_skips_malformed_lines(tmp_path):
    path = tmp_path / "chat_log.jsonl"
    path.write_text('{"ok": 1}\nnot-json\n{"ok": 2}\n', encoding="utf-8")
    store = ChatStore(path=str(path))
    records = store.read_all()
    assert [r["ok"] for r in records] == [1, 2]


def test_chatbot_wires_optional_logging(tmp_path):
    path = tmp_path / "chat_log.jsonl"
    bot = AttendanceChatbot(client=OfflineClient(), chat_store=ChatStore(path=str(path)))

    bot.answer("Tell me about EMP101")

    records = ChatStore(path=str(path)).read_all()
    assert len(records) == 1
    assert records[0]["employee_ids"] == ["EMP101"]
    assert records[0]["provider"] == "offline"


def test_chatbot_without_store_does_not_log(tmp_path):
    path = tmp_path / "chat_log.jsonl"
    bot = AttendanceChatbot(client=OfflineClient())
    bot.answer("Tell me about EMP101")
    assert not path.exists()
