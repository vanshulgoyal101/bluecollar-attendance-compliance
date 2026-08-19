"""Tests for the data store and chatbot (offline + mocked-LLM paths)."""

from src.chatbot import AttendanceChatbot
from src.data_store import EmployeeDataStore
from src.llm.env import LLMSettings
from src.llm.rotating_client import CompletionResult, RotatingLLMClient


def no_key_client():
    return RotatingLLMClient(
        settings=LLMSettings(
            google_keys=[],
            groq_keys=[],
            openrouter_keys=[],
            cerebras_keys=[],
            provider_order=[],
            gemini_model="m",
            groq_model="m",
            openrouter_model="m",
            cerebras_model="m",
            temperature=0.2,
        )
    )


class RecordingClient:
    """Stand-in LLM client that captures the messages it is given."""

    def __init__(self):
        self.messages = None

    def is_configured(self):
        return True

    def complete(self, messages, **kwargs):
        self.messages = messages
        return CompletionResult(text="canned answer", provider="google", model="m")


# --- Data store ---------------------------------------------------------- #


def test_store_loads_all_employees():
    store = EmployeeDataStore()
    assert len(store.roster()) == 10
    assert store.get("EMP101")["name"] == "Vanshul Goyal"


def test_find_mentioned_by_id_and_name():
    store = EmployeeDataStore()
    assert "EMP101" in store.find_mentioned("how is EMP101 doing?")
    assert "EMP102" in store.find_mentioned("tell me about Sarah")


def test_knowledge_base_includes_roster_and_details():
    store = EmployeeDataStore()
    kb = store.build_knowledge_base("EMP101")
    assert "ROSTER" in kb
    assert "EMP101" in kb
    # Mentioned employee is placed first in the detail sections.
    assert kb.index("### EMP101") < kb.index("### EMP102")


# --- Chatbot offline fallback -------------------------------------------- #


def test_offline_answer_for_specific_employee():
    bot = AttendanceChatbot(client=no_key_client())
    result = bot.answer("Give me EMP101's record")
    assert result["provider"] == "offline"
    assert "EMP101" in result["answer"]


def test_offline_answer_for_lowest_points():
    bot = AttendanceChatbot(client=no_key_client())
    result = bot.answer("Who has the lowest points?")
    assert result["provider"] == "offline"
    assert "pts" in result["answer"]


def test_empty_question_is_handled():
    bot = AttendanceChatbot(client=no_key_client())
    result = bot.answer("   ")
    assert result["grounded"] is False


# --- Suggested follow-ups (F-35) ----------------------------------------- #


def test_answer_includes_employee_suggestions():
    bot = AttendanceChatbot(client=no_key_client())
    result = bot.answer("Tell me about EMP101")
    assert isinstance(result["suggestions"], list)
    assert 2 <= len(result["suggestions"]) <= 5
    assert any("EMP101" in s for s in result["suggestions"])


def test_answer_includes_roster_suggestions():
    bot = AttendanceChatbot(client=no_key_client())
    result = bot.answer("Who is at risk of termination?")
    assert 2 <= len(result["suggestions"]) <= 5
    assert all(isinstance(s, str) for s in result["suggestions"])



# --- Chatbot LLM path (mocked) ------------------------------------------- #


def test_llm_path_builds_grounded_prompt():
    recording = RecordingClient()
    bot = AttendanceChatbot(client=recording)
    result = bot.answer("Who is at risk?")

    assert result["answer"] == "canned answer"
    assert result["provider"] == "google"
    system_msg = recording.messages[0]
    assert system_msg["role"] == "system"
    assert "DATA:" in system_msg["content"]
    assert "ROSTER" in system_msg["content"]
    assert recording.messages[-1] == {"role": "user", "content": "Who is at risk?"}
