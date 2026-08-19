"""Tests for streaming completions (F-33).

Cover the rotating client's ``stream`` (chunking, fall-back to ``complete``,
failover before the first chunk, usage recording) and the chatbot's ``stream``
(LLM path, offline path, empty question) with in-memory fakes — no network.
"""

from src.chatbot import AttendanceChatbot
from src.llm import usage
from src.llm.env import LLMSettings
from src.llm.providers import LLMError
from src.llm.rotating_client import RotatingLLMClient


class StreamingProvider:
    def __init__(self, name, chunks, fail_status=None):
        self.name = name
        self.model = f"{name}-model"
        self.chunks = chunks
        self.fail_status = fail_status
        self.calls = []

    def stream(self, messages, api_key, temperature, json_mode=False, max_tokens=None):
        self.calls.append(api_key)
        if self.fail_status is not None:
            raise LLMError("boom", provider=self.name, status=self.fail_status)
        for chunk in self.chunks:
            yield chunk


class NonStreamingProvider:
    """Only implements ``complete`` — the client must fall back to it."""

    def __init__(self, name, text):
        self.name = name
        self.model = f"{name}-model"
        self.text = text
        self.completed = 0

    def complete(self, messages, api_key, temperature, json_mode=False, max_tokens=None):
        self.completed += 1
        return self.text


def make_client(registry):
    settings = LLMSettings(
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
    client = RotatingLLMClient(settings=settings)
    client._registry = registry
    return client


class FakeStreamClient:
    def __init__(self, chunks, configured=True):
        self.chunks = chunks
        self._configured = configured
        self.last_provider = "google"
        self.last_model = "gemini-2.0-flash"

    def is_configured(self):
        return self._configured

    def stream(self, messages, **kwargs):
        for chunk in self.chunks:
            yield chunk


# --- client.stream ------------------------------------------------------- #


def test_stream_yields_provider_chunks():
    provider = StreamingProvider("google", ["Hel", "lo ", "world"])
    client = make_client([(provider, ["k1"])])

    out = list(client.stream([{"role": "user", "content": "hi"}]))

    assert out == ["Hel", "lo ", "world"]
    assert "".join(out) == "Hello world"


def test_stream_falls_back_to_complete_when_provider_cannot_stream():
    provider = NonStreamingProvider("groq", "the full answer")
    client = make_client([(provider, ["k1"])])

    out = list(client.stream([{"role": "user", "content": "hi"}]))

    assert out == ["the full answer"]
    assert provider.completed == 1


def test_stream_fails_over_before_first_chunk():
    a = StreamingProvider("google", [], fail_status=429)
    b = StreamingProvider("groq", ["ok"])
    client = make_client([(a, ["ka"]), (b, ["kb"])])

    out = list(client.stream([{"role": "user", "content": "hi"}]))

    assert out == ["ok"]
    assert a.calls == ["ka"]
    assert b.calls == ["kb"]


def test_stream_records_usage():
    usage.reset()
    provider = StreamingProvider("google", ["abcd", "efgh"])
    client = make_client([(provider, ["k1"])])

    list(client.stream([{"role": "user", "content": "hi"}]))

    snap = usage.usage_snapshot()
    assert snap["requests"] == 1
    assert snap["by_provider"]["google"]["completion_tokens"] >= 1
    usage.reset()


# --- chatbot.stream ------------------------------------------------------ #


def test_chatbot_stream_yields_chunks():
    bot = AttendanceChatbot(client=FakeStreamClient(["Hello ", "EMP101"]))
    out = list(bot.stream("Tell me about EMP101"))
    assert "".join(out) == "Hello EMP101"


def test_chatbot_stream_offline_yields_single_answer():
    bot = AttendanceChatbot(client=FakeStreamClient([], configured=False))
    out = list(bot.stream("Who has the lowest points?"))
    assert len(out) == 1
    assert "pts" in out[0]


def test_chatbot_stream_empty_question():
    bot = AttendanceChatbot(client=FakeStreamClient([], configured=True))
    out = list(bot.stream("   "))
    assert out == ["Ask me anything about employee attendance or compliance."]
