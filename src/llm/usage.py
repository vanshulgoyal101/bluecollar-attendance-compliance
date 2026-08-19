"""LLM usage metering (F-36).

A tiny, process-global, thread-safe tracker for request counts and token usage
per provider. ``RotatingLLMClient`` records into it after each successful
completion/stream so the app can expose a lightweight usage snapshot
(contract 3.4) — e.g. from ``/api/usage`` or ``/api/health`` — without any
external metering service.

No API keys, prompts or response text are ever stored here; only counters.
"""

import threading
from typing import Dict

_lock = threading.Lock()

_totals: Dict[str, int] = {"requests": 0, "prompt_tokens": 0, "completion_tokens": 0}
_by_provider: Dict[str, Dict[str, int]] = {}


def _empty_bucket() -> Dict[str, int]:
    return {"requests": 0, "prompt_tokens": 0, "completion_tokens": 0}


def record(provider: str, prompt_tokens: int = 0, completion_tokens: int = 0) -> None:
    """Record one completion's token usage against ``provider``."""
    prompt_tokens = max(0, int(prompt_tokens or 0))
    completion_tokens = max(0, int(completion_tokens or 0))
    with _lock:
        _totals["requests"] += 1
        _totals["prompt_tokens"] += prompt_tokens
        _totals["completion_tokens"] += completion_tokens
        bucket = _by_provider.setdefault(provider, _empty_bucket())
        bucket["requests"] += 1
        bucket["prompt_tokens"] += prompt_tokens
        bucket["completion_tokens"] += completion_tokens


def usage_snapshot() -> dict:
    """Return a copy of the running usage totals (contract 3.4)."""
    with _lock:
        return {
            "requests": _totals["requests"],
            "prompt_tokens": _totals["prompt_tokens"],
            "completion_tokens": _totals["completion_tokens"],
            "total_tokens": _totals["prompt_tokens"] + _totals["completion_tokens"],
            "by_provider": {
                name: dict(stats) for name, stats in _by_provider.items()
            },
        }


def reset() -> None:
    """Clear all counters. Intended for tests."""
    with _lock:
        _totals["requests"] = 0
        _totals["prompt_tokens"] = 0
        _totals["completion_tokens"] = 0
        _by_provider.clear()


def estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars/token) for providers that omit usage."""
    text = text or ""
    if not text.strip():
        return 0
    return max(1, len(text) // 4)


def estimate_message_tokens(messages) -> int:
    """Rough prompt-token estimate from a list of chat messages."""
    joined = "".join(str(m.get("content", "")) for m in (messages or []))
    return estimate_tokens(joined)
