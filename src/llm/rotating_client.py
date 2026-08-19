"""Rotating, failover LLM client.

Ported from the adbrain TypeScript orchestrator. It rotates across providers
(in ``LLM_PROVIDER_ORDER``) and across each provider's key pool using a
round-robin cursor so load spreads evenly. Keys that hit a 429 are parked for a
short cooldown so we stop hammering them. ``complete`` throws only when every
provider/key combination has failed.
"""

import datetime
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional, Tuple

from . import usage
from .env import LLMSettings, load_llm_settings
from .providers import (
    GeminiProvider,
    LLMError,
    OpenAICompatibleProvider,
    ProviderResponse,
)

ChatMessage = Dict[str, Any]

logger = logging.getLogger(__name__)

# Fallback cooldown for a 429'd key when the provider gives no retry hint.
COOLDOWN_S = 60.0


class NoLLMKeysError(Exception):
    """Raised when no provider has any keys configured."""

    def __init__(self) -> None:
        super().__init__(
            "No LLM API keys configured. Add at least one key to .env "
            "(GOOGLE_AI_API_KEYS, GROQ_API_KEYS, OPENROUTER_API_KEYS, or "
            "CEREBRAS_API_KEYS)."
        )


class AllProvidersFailedError(Exception):
    """Raised when every configured provider/key combination has failed."""


@dataclass
class CompletionResult:
    text: str
    provider: str
    model: str


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class ToolCompletion:
    """Result of a tool-enabled completion round (F-40).

    ``tool_calls`` is non-empty when the model wants to call ComplianceService
    tools; otherwise ``text`` holds the final answer.
    """

    text: str
    provider: str
    model: str
    tool_calls: List[ToolCall] = field(default_factory=list)


# A registered provider is the adapter plus its key pool.
RegisteredProvider = Tuple[object, List[str]]


class RotatingLLMClient:
    def __init__(self, settings: Optional[LLMSettings] = None):
        self.settings = settings or load_llm_settings()
        self._cooldown_until: Dict[str, float] = {}
        self._rr_cursor: Dict[str, int] = {}
        self._registry = self._build_registry()
        # Provider/model that served the most recent successful call (for logging).
        self.last_provider: Optional[str] = None
        self.last_model: Optional[str] = None

    def _build_registry(self) -> List[RegisteredProvider]:
        s = self.settings
        available: Dict[str, RegisteredProvider] = {
            "google": (GeminiProvider(s.gemini_model), s.google_keys),
            "groq": (
                OpenAICompatibleProvider(
                    "groq",
                    "https://api.groq.com/openai/v1/chat/completions",
                    s.groq_model,
                ),
                s.groq_keys,
            ),
            "openrouter": (
                OpenAICompatibleProvider(
                    "openrouter",
                    "https://openrouter.ai/api/v1/chat/completions",
                    s.openrouter_model,
                    {"X-Title": "AttendanceBot"},
                ),
                s.openrouter_keys,
            ),
            "cerebras": (
                OpenAICompatibleProvider(
                    "cerebras",
                    "https://api.cerebras.ai/v1/chat/completions",
                    s.cerebras_model,
                ),
                s.cerebras_keys,
            ),
        }

        registry: List[RegisteredProvider] = []
        for name in s.provider_order:
            entry = available.get(name)
            if entry and entry[1]:  # provider exists and has at least one key
                registry.append(entry)
        return registry

    def is_configured(self) -> bool:
        return len(self._registry) > 0

    def provider_status(self) -> List[Dict[str, object]]:
        """Configured providers and their key counts, for diagnostics."""
        return [
            {"name": provider.name, "key_count": len(keys)}
            for provider, keys in self._registry
        ]

    def _next_key_start(self, provider_name: str, key_count: int) -> int:
        cur = self._rr_cursor.get(provider_name, 0)
        self._rr_cursor[provider_name] = (cur + 1) % key_count
        return cur % key_count

    def _park_key(self, cool_key: str, retry_after: Optional[float]) -> None:
        """Cool down a rate-limited key and log when its quota should refresh."""
        cooldown = retry_after if (retry_after and retry_after > 0) else COOLDOWN_S
        self._cooldown_until[cool_key] = time.monotonic() + cooldown
        refresh_at = datetime.datetime.now() + datetime.timedelta(seconds=cooldown)
        logger.warning(
            "LLM key [%s] hit its quota (429). Quota refreshes ~%s (in %ss).",
            cool_key,
            refresh_at.strftime("%Y-%m-%d %H:%M:%S"),
            round(cooldown),
        )
        if self._all_parked():
            logger.warning(
                "All LLM keys are rate-limited. Quota refresh schedule:\n%s",
                self._quota_report(),
            )

    def _all_parked(self) -> bool:
        now = time.monotonic()
        return all(
            self._cooldown_until.get(f"{provider.name}:{idx}", 0.0) > now
            for provider, keys in self._registry
            for idx in range(len(keys))
        )

    def _quota_report(self) -> str:
        lines = []
        for row in self.quota_status():
            if row["available"]:
                lines.append(f"  {row['key']}: available now")
            else:
                lines.append(
                    f"  {row['key']}: refreshes ~{row['refresh_at']} "
                    f"(in {round(row['seconds_until_refresh'])}s)"
                )
        return "\n".join(lines)

    def quota_status(self) -> List[Dict[str, Any]]:
        """Per-key rate-limit state, including when each quota refreshes."""
        now = time.monotonic()
        wall = datetime.datetime.now()
        rows: List[Dict[str, Any]] = []
        for provider, keys in self._registry:
            for idx in range(len(keys)):
                cool_key = f"{provider.name}:{idx}"
                remaining = max(0.0, self._cooldown_until.get(cool_key, 0.0) - now)
                refresh_at = (
                    (wall + datetime.timedelta(seconds=remaining)).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    if remaining > 0
                    else None
                )
                rows.append(
                    {
                        "key": cool_key,
                        "provider": provider.name,
                        "available": remaining <= 0,
                        "seconds_until_refresh": round(remaining, 1),
                        "refresh_at": refresh_at,
                    }
                )
        return rows

    def complete(
        self,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        json_mode: bool = False,
        max_tokens: Optional[int] = None,
    ) -> CompletionResult:
        """Run a chat completion, rotating providers/keys until one succeeds."""
        if not self._registry:
            raise NoLLMKeysError()

        temp = self.settings.temperature if temperature is None else temperature
        errors: List[str] = []

        for provider, keys in self._registry:
            start = self._next_key_start(provider.name, len(keys))
            for i in range(len(keys)):
                idx = (start + i) % len(keys)
                cool_key = f"{provider.name}:{idx}"
                if self._cooldown_until.get(cool_key, 0.0) > time.monotonic():
                    continue

                try:
                    text = provider.complete(
                        messages, keys[idx], temp, json_mode, max_tokens
                    )
                    self._mark_used(provider)
                    usage.record(
                        provider.name,
                        usage.estimate_message_tokens(messages),
                        usage.estimate_tokens(text),
                    )
                    return CompletionResult(
                        text=text, provider=provider.name, model=provider.model
                    )
                except LLMError as err:
                    errors.append(f"{provider.name}[key {idx}]: {err}")
                    if err.status == 429:
                        self._park_key(cool_key, getattr(err, "retry_after", None))
                except Exception as err:  # defensive: never let one key abort the loop
                    errors.append(f"{provider.name}[key {idx}]: {err}")

        raise AllProvidersFailedError(
            f"All LLM providers failed ({len(self._registry)} tried):\n"
            + "\n".join(errors)
        )

    def _mark_used(self, provider) -> None:
        self.last_provider = provider.name
        self.last_model = provider.model

    def stream(
        self,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        json_mode: bool = False,
        max_tokens: Optional[int] = None,
    ) -> Iterator[str]:
        """Stream a chat completion as text chunks (F-33).

        Rotation/cooldown/failover mirror :meth:`complete`: we fail over to the
        next key/provider only *before* the first chunk is produced (a clean
        establishment error). Providers without a ``stream`` method fall back to
        a blocking ``complete`` whose full answer is yielded as one chunk.
        """
        if not self._registry:
            raise NoLLMKeysError()

        temp = self.settings.temperature if temperature is None else temperature
        errors: List[str] = []

        for provider, keys in self._registry:
            start = self._next_key_start(provider.name, len(keys))
            for i in range(len(keys)):
                idx = (start + i) % len(keys)
                cool_key = f"{provider.name}:{idx}"
                if self._cooldown_until.get(cool_key, 0.0) > time.monotonic():
                    continue

                generator = self._stream_one(
                    provider, keys[idx], messages, temp, json_mode, max_tokens
                )
                try:
                    first = next(generator)
                except StopIteration:
                    # Empty but successful stream.
                    self._mark_used(provider)
                    return
                except LLMError as err:
                    errors.append(f"{provider.name}[key {idx}]: {err}")
                    if err.status == 429:
                        self._park_key(cool_key, getattr(err, "retry_after", None))
                    continue
                except Exception as err:  # defensive: try the next key/provider
                    errors.append(f"{provider.name}[key {idx}]: {err}")
                    continue

                # Committed to this provider: deliver the first chunk then the rest.
                self._mark_used(provider)
                yield first
                yield from generator
                return

        raise AllProvidersFailedError(
            f"All LLM providers failed to stream ({len(self._registry)} tried):\n"
            + "\n".join(errors)
        )

    def _stream_one(
        self,
        provider,
        key: str,
        messages: List[ChatMessage],
        temperature: float,
        json_mode: bool,
        max_tokens: Optional[int],
    ) -> Iterator[str]:
        """Yield chunks from one provider/key, recording usage when it finishes.

        If the provider can't stream, fall back to ``complete`` and yield the
        whole answer as a single chunk.
        """
        stream_fn = getattr(provider, "stream", None)
        if stream_fn is None:
            text = provider.complete(
                messages, key, temperature, json_mode, max_tokens
            )
            usage.record(
                provider.name,
                usage.estimate_message_tokens(messages),
                usage.estimate_tokens(text),
            )
            if text:
                yield text
            return

        parts: List[str] = []
        for chunk in stream_fn(messages, key, temperature, json_mode, max_tokens):
            parts.append(chunk)
            yield chunk
        usage.record(
            provider.name,
            usage.estimate_message_tokens(messages),
            usage.estimate_tokens("".join(parts)),
        )

    def complete_tools(
        self,
        messages: List[ChatMessage],
        tools: List[Dict[str, Any]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> ToolCompletion:
        """One tool-enabled completion round, rotating providers/keys (F-40).

        Returns a :class:`ToolCompletion`; when ``tool_calls`` is non-empty the
        caller should execute them and call again with the results appended.
        Providers that can't do function-calling degrade to a plain completion.
        """
        if not self._registry:
            raise NoLLMKeysError()

        temp = self.settings.temperature if temperature is None else temperature
        errors: List[str] = []

        for provider, keys in self._registry:
            start = self._next_key_start(provider.name, len(keys))
            for i in range(len(keys)):
                idx = (start + i) % len(keys)
                cool_key = f"{provider.name}:{idx}"
                if self._cooldown_until.get(cool_key, 0.0) > time.monotonic():
                    continue

                tools_fn = getattr(provider, "complete_tools", None)
                try:
                    if tools_fn is None:
                        text = provider.complete(
                            messages, keys[idx], temp, False, max_tokens
                        )
                        response = ProviderResponse(text=text)
                    else:
                        response = tools_fn(
                            messages, keys[idx], temp, tools, False, max_tokens
                        )
                    self._mark_used(provider)
                    usage.record(
                        provider.name,
                        response.usage.get("prompt_tokens")
                        or usage.estimate_message_tokens(messages),
                        response.usage.get("completion_tokens")
                        or usage.estimate_tokens(response.text),
                    )
                    return ToolCompletion(
                        text=response.text,
                        provider=provider.name,
                        model=provider.model,
                        tool_calls=[
                            ToolCall(
                                id=tc.get("id") or f"call_{n}",
                                name=tc.get("name"),
                                arguments=tc.get("arguments") or {},
                            )
                            for n, tc in enumerate(response.tool_calls)
                        ],
                    )
                except LLMError as err:
                    errors.append(f"{provider.name}[key {idx}]: {err}")
                    if err.status == 429:
                        self._park_key(cool_key, getattr(err, "retry_after", None))
                except Exception as err:  # defensive: never let one key abort the loop
                    errors.append(f"{provider.name}[key {idx}]: {err}")

        raise AllProvidersFailedError(
            f"All LLM providers failed ({len(self._registry)} tried):\n"
            + "\n".join(errors)
        )
