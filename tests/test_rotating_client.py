"""Tests for the rotating LLM client's key-rotation, cooldown and failover.

These use in-memory fake providers, so they need no network or API keys.
"""

import pytest

from src.llm.env import LLMSettings
from src.llm.providers import LLMError
from src.llm.rotating_client import (
    AllProvidersFailedError,
    NoLLMKeysError,
    RotatingLLMClient,
)


class FakeProvider:
    def __init__(self, name, keys_behavior):
        self.name = name
        self.model = f"{name}-model"
        self.calls = []
        # maps api_key -> "ok" | 429 | "error"
        self.behavior = keys_behavior

    def complete(self, messages, api_key, temperature, json_mode=False, max_tokens=None):
        self.calls.append(api_key)
        outcome = self.behavior.get(api_key, "ok")
        if outcome == "ok":
            return f"ok:{self.name}:{api_key}"
        if outcome == 429:
            raise LLMError("rate limited", provider=self.name, status=429, retryable=True)
        raise LLMError("server error", provider=self.name, status=500, retryable=True)


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


def test_round_robin_spreads_across_keys():
    provider = FakeProvider("google", {"k1": "ok", "k2": "ok", "k3": "ok"})
    client = make_client([(provider, ["k1", "k2", "k3"])])

    for _ in range(4):
        client.complete([{"role": "user", "content": "hi"}])

    # 4 calls rotate k1, k2, k3, then back to k1.
    assert provider.calls == ["k1", "k2", "k3", "k1"]


def test_failover_to_next_key_within_provider():
    provider = FakeProvider("google", {"k1": "error", "k2": "ok"})
    client = make_client([(provider, ["k1", "k2"])])

    result = client.complete([{"role": "user", "content": "hi"}])

    assert result.text == "ok:google:k2"
    assert provider.calls == ["k1", "k2"]


def test_429_key_is_parked_and_skipped_on_next_call():
    a = FakeProvider("google", {"ka": 429})
    b = FakeProvider("groq", {"kb": "ok"})
    client = make_client([(a, ["ka"]), (b, ["kb"])])

    first = client.complete([{"role": "user", "content": "hi"}])
    second = client.complete([{"role": "user", "content": "hi"}])

    assert first.provider == "groq"
    assert second.provider == "groq"
    # ka hit a 429 once and is cooled down, so it is not retried on the 2nd call.
    assert a.calls == ["ka"]


def test_failover_across_providers_in_order():
    a = FakeProvider("google", {"ka": "error"})
    b = FakeProvider("groq", {"kb": "ok"})
    client = make_client([(a, ["ka"]), (b, ["kb"])])

    result = client.complete([{"role": "user", "content": "hi"}])

    assert result.provider == "groq"
    assert a.calls == ["ka"]
    assert b.calls == ["kb"]


def test_all_providers_failing_raises():
    a = FakeProvider("google", {"ka": "error"})
    b = FakeProvider("groq", {"kb": "error"})
    client = make_client([(a, ["ka"]), (b, ["kb"])])

    with pytest.raises(AllProvidersFailedError):
        client.complete([{"role": "user", "content": "hi"}])


def test_no_keys_configured_raises():
    client = make_client([])
    assert client.is_configured() is False
    with pytest.raises(NoLLMKeysError):
        client.complete([{"role": "user", "content": "hi"}])


def test_provider_status_reports_key_counts():
    a = FakeProvider("google", {"k1": "ok", "k2": "ok"})
    client = make_client([(a, ["k1", "k2"])])
    assert client.provider_status() == [{"name": "google", "key_count": 2}]


def test_llm_error_redacts_api_key():
    from src.llm.providers import LLMError

    err = LLMError(
        "gemini: network error — url ...generateContent?key=SECRET123 (Caused by)",
        provider="google",
    )
    assert "SECRET123" not in str(err)
    assert "key=REDACTED" in str(err)

