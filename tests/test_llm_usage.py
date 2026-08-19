"""Tests for LLM usage metering (F-36).

Exercise the process-global usage tracker and the recording that
``RotatingLLMClient.complete`` performs, using an in-memory fake provider so no
network or keys are needed.
"""

import pytest

from src.llm import usage
from src.llm.env import LLMSettings
from src.llm.rotating_client import RotatingLLMClient


class FakeProvider:
    def __init__(self, name="google", text="hello there answer"):
        self.name = name
        self.model = f"{name}-model"
        self.text = text

    def complete(self, messages, api_key, temperature, json_mode=False, max_tokens=None):
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


@pytest.fixture(autouse=True)
def _reset_usage():
    usage.reset()
    yield
    usage.reset()


def test_snapshot_starts_empty():
    assert usage.usage_snapshot() == {
        "requests": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "by_provider": {},
    }


def test_record_accumulates_totals_and_per_provider():
    usage.record("google", 10, 5)
    usage.record("groq", 3, 7)
    usage.record("google", 2, 1)

    snap = usage.usage_snapshot()
    assert snap["requests"] == 3
    assert snap["prompt_tokens"] == 15
    assert snap["completion_tokens"] == 13
    assert snap["total_tokens"] == 28
    assert snap["by_provider"]["google"] == {
        "requests": 2,
        "prompt_tokens": 12,
        "completion_tokens": 6,
    }
    assert snap["by_provider"]["groq"] == {
        "requests": 1,
        "prompt_tokens": 3,
        "completion_tokens": 7,
    }


def test_complete_records_usage_per_provider():
    client = make_client([(FakeProvider("google"), ["k1"])])
    client.complete([{"role": "user", "content": "how is EMP101 doing?"}])

    snap = usage.usage_snapshot()
    assert snap["requests"] == 1
    assert snap["completion_tokens"] > 0
    assert snap["by_provider"]["google"]["requests"] == 1
    assert snap["total_tokens"] == snap["prompt_tokens"] + snap["completion_tokens"]


def test_snapshot_is_a_copy():
    usage.record("google", 1, 1)
    snap = usage.usage_snapshot()
    snap["by_provider"]["google"]["requests"] = 999
    assert usage.usage_snapshot()["by_provider"]["google"]["requests"] == 1


def test_negative_values_are_clamped():
    usage.record("google", -5, -3)
    snap = usage.usage_snapshot()
    assert snap["prompt_tokens"] == 0
    assert snap["completion_tokens"] == 0


def test_token_estimators():
    assert usage.estimate_tokens("") == 0
    assert usage.estimate_tokens("   ") == 0
    assert usage.estimate_tokens("a" * 8) >= 1
    assert usage.estimate_message_tokens([{"role": "user", "content": "x" * 40}]) >= 1
    assert usage.estimate_message_tokens([]) == 0
