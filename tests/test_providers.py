"""Tests for the LLM provider adapters (offline; ``requests`` is faked)."""

import json

import pytest

from src.llm import providers
from src.llm.providers import (
    GeminiProvider,
    LLMError,
    OpenAICompatibleProvider,
)


class FakeResp:
    def __init__(self, status=200, json_data=None, text="", lines=None):
        self.status_code = status
        self.ok = 200 <= status < 300
        self._json = json_data if json_data is not None else {}
        self.text = text
        self._lines = lines or []

    def json(self):
        return self._json

    def iter_lines(self, decode_unicode=True):
        for line in self._lines:
            yield line


@pytest.fixture
def capture_post(monkeypatch):
    """Patch providers.requests.post; capture the call and return a set response."""
    calls = {}

    def _factory(resp):
        def _post(url, json=None, headers=None, timeout=None, stream=False):
            calls["url"] = url
            calls["json"] = json
            calls["headers"] = headers
            calls["stream"] = stream
            return resp

        monkeypatch.setattr(providers.requests, "post", _post)
        return calls

    return _factory


# --- Gemini ------------------------------------------------------------- #


def test_gemini_complete_parses_text_and_builds_body(capture_post):
    resp = FakeResp(json_data={"candidates": [{"content": {"parts": [{"text": "hello "}, {"text": "world"}]}}]})
    calls = capture_post(resp)
    out = GeminiProvider("gemini-x").complete(
        [{"role": "system", "content": "SYS"}, {"role": "user", "content": "hi"}],
        api_key="K",
        temperature=0.2,
    )
    assert out == "hello world"
    assert calls["json"]["systemInstruction"]["parts"][0]["text"] == "SYS"
    assert calls["json"]["contents"][0]["parts"][0]["text"] == "hi"
    assert "generateContent?key=K" in calls["url"]


def test_gemini_http_error_is_retryable_and_key_redacted(capture_post):
    capture_post(FakeResp(status=429, text="rate limited"))
    with pytest.raises(LLMError) as exc:
        GeminiProvider("m").complete([{"role": "user", "content": "hi"}], "SECRET", 0.2)
    assert exc.value.status == 429
    assert exc.value.retryable is True


def test_gemini_empty_response_raises(capture_post):
    capture_post(FakeResp(json_data={"candidates": []}))
    with pytest.raises(LLMError):
        GeminiProvider("m").complete([{"role": "user", "content": "hi"}], "K", 0.2)


def test_gemini_stream_yields_text_chunks(capture_post):
    lines = [
        'data: {"candidates":[{"content":{"parts":[{"text":"a"}]}}]}',
        "",
        'data: {"candidates":[{"content":{"parts":[{"text":"b"}]}}]}',
    ]
    capture_post(FakeResp(lines=lines))
    chunks = list(GeminiProvider("m").stream([{"role": "user", "content": "hi"}], "K", 0.2))
    assert chunks == ["a", "b"]


def test_gemini_complete_tools_extracts_function_call(capture_post):
    data = {
        "candidates": [
            {"content": {"parts": [{"functionCall": {"name": "roster", "args": {}}}]}}
        ],
        "usageMetadata": {"promptTokenCount": 5, "candidatesTokenCount": 2},
    }
    capture_post(FakeResp(json_data=data))
    resp = GeminiProvider("m").complete_tools(
        [{"role": "user", "content": "list"}], "K", 0.2, tools=[{"name": "roster"}]
    )
    assert resp.tool_calls[0]["name"] == "roster"
    assert resp.usage["prompt_tokens"] == 5


# --- OpenAI-compatible -------------------------------------------------- #


def test_openai_complete_parses_and_sets_bearer(capture_post):
    resp = FakeResp(json_data={"choices": [{"message": {"content": "hi there"}}]})
    calls = capture_post(resp)
    provider = OpenAICompatibleProvider("groq", "https://x/v1/chat", "m", {"X-Title": "T"})
    out = provider.complete([{"role": "user", "content": "hi"}], "K", 0.3)
    assert out == "hi there"
    assert calls["headers"]["Authorization"] == "Bearer K"
    assert calls["headers"]["X-Title"] == "T"


def test_openai_stream_parses_deltas_and_done(capture_post):
    lines = [
        'data: {"choices":[{"delta":{"content":"foo"}}]}',
        'data: {"choices":[{"delta":{"content":"bar"}}]}',
        "data: [DONE]",
        'data: {"choices":[{"delta":{"content":"ignored"}}]}',
    ]
    capture_post(FakeResp(lines=lines))
    provider = OpenAICompatibleProvider("groq", "https://x", "m")
    chunks = list(provider.stream([{"role": "user", "content": "hi"}], "K", 0.2))
    assert chunks == ["foo", "bar"]


def test_openai_complete_tools_parses_json_arguments(capture_post):
    data = {
        "choices": [
            {
                "message": {
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "function": {
                                "name": "infractions",
                                "arguments": '{"emp_id": "EMP101", "year": 2025}',
                            },
                        }
                    ],
                }
            }
        ],
        "usage": {"prompt_tokens": 9, "completion_tokens": 3},
    }
    capture_post(FakeResp(json_data=data))
    provider = OpenAICompatibleProvider("groq", "https://x", "m")
    resp = provider.complete_tools([{"role": "user", "content": "x"}], "K", 0.2, tools=[{}])
    call = resp.tool_calls[0]
    assert call["name"] == "infractions"
    assert call["arguments"] == {"emp_id": "EMP101", "year": 2025}
    assert resp.usage["completion_tokens"] == 3


def test_openai_network_error_is_retryable(monkeypatch):
    def _boom(*a, **k):
        raise providers.requests.RequestException("boom")

    monkeypatch.setattr(providers.requests, "post", _boom)
    provider = OpenAICompatibleProvider("groq", "https://x", "m")
    with pytest.raises(LLMError) as exc:
        provider.complete([{"role": "user", "content": "hi"}], "K", 0.2)
    assert exc.value.retryable is True


def test_llmerror_redacts_key_in_message():
    err = LLMError("failed for key=SUPERSECRET&foo", provider="google")
    assert "SUPERSECRET" not in str(err)
    assert "key=REDACTED" in str(err)
