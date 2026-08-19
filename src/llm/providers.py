"""LLM provider adapters.

Two request shapes cover every provider we use:
- ``GeminiProvider`` — Google Generative Language API (key as a query param,
  system prompt in ``systemInstruction``, turns in ``contents``).
- ``OpenAICompatibleProvider`` — the OpenAI Chat Completions shape, which also
  serves Groq, OpenRouter and Cerebras (bearer token, ``messages`` array).

Each provider exposes three surfaces:
- ``complete`` — blocking chat completion, returns the answer ``str``.
- ``stream`` — yields answer text chunks (F-33).
- ``complete_tools`` — tool/function-calling round, returns a
  :class:`ProviderResponse` carrying text, token usage and normalized
  ``tool_calls`` (F-40).
"""

import datetime
import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional

import requests

ChatMessage = Dict[str, Any]

REQUEST_TIMEOUT_S = 60

# Gemini passes the API key as a ``key=`` query param, so it can appear in URLs
# echoed by network exceptions. Redact it before it reaches any error/log string.
_KEY_QUERY_RE = re.compile(r"(key=)[^&\s]+")


def _redact_key(text: Any) -> str:
    return _KEY_QUERY_RE.sub(r"\1REDACTED", str(text))


@dataclass
class ProviderResponse:
    """A tool-calling completion result.

    ``tool_calls`` are normalized to ``{"id", "name", "arguments": dict}`` so the
    calling code is provider-agnostic. Plain ``complete`` still returns a ``str``;
    only ``complete_tools`` returns this richer shape.
    """

    text: str = ""
    usage: Dict[str, int] = field(default_factory=dict)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)


def _parse_maybe_json(value: Any) -> Any:
    """Best-effort parse of a tool-result payload into JSON, else pass through."""
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return value
    return value


def _openai_usage(data: Dict[str, Any]) -> Dict[str, int]:
    usage = data.get("usage") or {}
    return {
        "prompt_tokens": int(usage.get("prompt_tokens") or 0),
        "completion_tokens": int(usage.get("completion_tokens") or 0),
    }


def _gemini_usage(data: Dict[str, Any]) -> Dict[str, int]:
    usage = data.get("usageMetadata") or {}
    return {
        "prompt_tokens": int(usage.get("promptTokenCount") or 0),
        "completion_tokens": int(usage.get("candidatesTokenCount") or 0),
    }


def _duration_to_seconds(text: Any) -> Optional[float]:
    """Parse a duration like '35s', '1m30s', '500ms' or '12.5' into seconds."""
    s = str(text).strip().lower()
    if not s:
        return None
    if s.endswith("ms"):
        try:
            return max(0.0, float(s[:-2]) / 1000.0)
        except ValueError:
            return None
    total, matched = 0.0, False
    for value, unit in re.findall(r"([\d.]+)\s*([hms]?)", s):
        if not value:
            continue
        try:
            total += float(value) * {"h": 3600, "m": 60, "s": 1, "": 1}[unit]
            matched = True
        except ValueError:
            continue
    return total if matched else None


def retry_after_seconds(res: requests.Response) -> Optional[float]:
    """Best-effort seconds until a rate-limited key's quota resets.

    Reads the standard ``Retry-After`` header, common vendor reset headers, the
    Gemini ``RetryInfo.retryDelay`` in the JSON body, and "try again in Xs" text.
    Returns ``None`` when the response carries no usable hint.
    """
    headers = res.headers or {}
    header_val = headers.get("Retry-After")
    if header_val:
        secs = _duration_to_seconds(header_val)
        if secs is not None:
            return secs
        try:
            from email.utils import parsedate_to_datetime

            dt = parsedate_to_datetime(header_val)
            return max(0.0, (dt - datetime.datetime.now(dt.tzinfo)).total_seconds())
        except (TypeError, ValueError):
            pass
    for name in ("retry-after-ms", "x-ratelimit-reset-after-ms"):
        if headers.get(name):
            try:
                return max(0.0, float(headers[name]) / 1000.0)
            except ValueError:
                pass
    for name in ("x-ratelimit-reset-tokens", "x-ratelimit-reset-requests"):
        secs = _duration_to_seconds(headers.get(name, ""))
        if secs is not None:
            return secs
    try:
        body = res.text or ""
        data = json.loads(body) if body.strip() else {}
    except (ValueError, TypeError):
        body, data = "", {}
    for detail in (data.get("error") or {}).get("details") or []:
        if str(detail.get("@type", "")).endswith("RetryInfo") and detail.get(
            "retryDelay"
        ):
            secs = _duration_to_seconds(detail["retryDelay"])
            if secs is not None:
                return secs
    match = re.search(r"try again in\s+([\d.]+)\s*(ms|s|m)?", body, re.I)
    if match:
        return _duration_to_seconds(match.group(1) + (match.group(2) or "s"))
    return None


class LLMError(Exception):
    """Raised by a provider on an HTTP/transport failure."""

    def __init__(
        self,
        message: str,
        provider: str,
        status: Optional[int] = None,
        retryable: bool = False,
        retry_after: Optional[float] = None,
    ):
        # Redact any API key so it never reaches logs, tracebacks or the client.
        super().__init__(_redact_key(message))
        self.provider = provider
        self.status = status
        self.retryable = retryable
        # Seconds until this key's quota resets, when the provider tells us.
        self.retry_after = retry_after


class GeminiProvider:
    name = "google"

    def __init__(self, model: str):
        self.model = model

    def complete(
        self,
        messages: List[ChatMessage],
        api_key: str,
        temperature: float,
        json_mode: bool = False,
        max_tokens: Optional[int] = None,
    ) -> str:
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        contents = [
            {
                "role": "model" if m["role"] == "assistant" else "user",
                "parts": [{"text": m["content"]}],
            }
            for m in messages
            if m["role"] != "system"
        ]

        generation_config: Dict[str, object] = {"temperature": temperature}
        if json_mode:
            generation_config["responseMimeType"] = "application/json"
        if max_tokens:
            generation_config["maxOutputTokens"] = max_tokens

        body: Dict[str, object] = {
            "contents": contents,
            "generationConfig": generation_config,
        }
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={api_key}"
        )

        try:
            res = requests.post(url, json=body, timeout=REQUEST_TIMEOUT_S)
        except requests.RequestException as err:
            raise LLMError(
                f"gemini: network error — {err}", provider="google", retryable=True
            )

        if not res.ok:
            raise LLMError(
                f"gemini HTTP {res.status_code}: {res.text[:200]}",
                provider="google",
                status=res.status_code,
                retryable=res.status_code == 429
                or res.status_code >= 500
                or res.status_code == 403,
                retry_after=retry_after_seconds(res),
            )

        data = res.json()
        try:
            parts = data["candidates"][0]["content"]["parts"]
            content = "".join(p.get("text", "") for p in parts)
        except (KeyError, IndexError, TypeError):
            content = ""
        if not content:
            raise LLMError("gemini: empty response", provider="google", retryable=True)
        return content

    # -- shared payload helpers -------------------------------------------- #

    def _generation_config(
        self, temperature: float, json_mode: bool, max_tokens: Optional[int]
    ) -> Dict[str, Any]:
        config: Dict[str, Any] = {"temperature": temperature}
        if json_mode:
            config["responseMimeType"] = "application/json"
        if max_tokens:
            config["maxOutputTokens"] = max_tokens
        return config

    def _system_text(self, messages: List[ChatMessage]) -> str:
        return "\n\n".join(
            m["content"]
            for m in messages
            if m.get("role") == "system" and m.get("content")
        )

    def _text_contents(self, messages: List[ChatMessage]) -> List[Dict[str, Any]]:
        return [
            {
                "role": "model" if m["role"] == "assistant" else "user",
                "parts": [{"text": m.get("content", "")}],
            }
            for m in messages
            if m.get("role") != "system"
        ]

    def _tool_contents(self, messages: List[ChatMessage]) -> List[Dict[str, Any]]:
        """Translate normalized messages (incl. tool calls/results) to contents."""
        contents: List[Dict[str, Any]] = []
        for m in messages:
            role = m.get("role")
            if role == "system":
                continue
            if role == "tool":
                contents.append(
                    {
                        "role": "user",
                        "parts": [
                            {
                                "functionResponse": {
                                    "name": m.get("name", "tool"),
                                    "response": {
                                        "result": _parse_maybe_json(m.get("content"))
                                    },
                                }
                            }
                        ],
                    }
                )
            elif role == "assistant" and m.get("tool_calls"):
                contents.append(
                    {
                        "role": "model",
                        "parts": [
                            {
                                "functionCall": {
                                    "name": tc.get("name"),
                                    "args": tc.get("arguments") or {},
                                }
                            }
                            for tc in m["tool_calls"]
                        ],
                    }
                )
            else:
                contents.append(
                    {
                        "role": "model" if role == "assistant" else "user",
                        "parts": [{"text": m.get("content", "")}],
                    }
                )
        return contents

    def stream(
        self,
        messages: List[ChatMessage],
        api_key: str,
        temperature: float,
        json_mode: bool = False,
        max_tokens: Optional[int] = None,
    ) -> Iterator[str]:
        body: Dict[str, Any] = {
            "contents": self._text_contents(messages),
            "generationConfig": self._generation_config(
                temperature, json_mode, max_tokens
            ),
        }
        system = self._system_text(messages)
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:streamGenerateContent?alt=sse&key={api_key}"
        )

        try:
            res = requests.post(url, json=body, stream=True, timeout=REQUEST_TIMEOUT_S)
        except requests.RequestException as err:
            raise LLMError(
                f"gemini: network error — {err}", provider="google", retryable=True
            )
        if not res.ok:
            raise LLMError(
                f"gemini HTTP {res.status_code}: {res.text[:200]}",
                provider="google",
                status=res.status_code,
                retryable=res.status_code == 429
                or res.status_code >= 500
                or res.status_code == 403,
                retry_after=retry_after_seconds(res),
            )

        res.encoding = "utf-8"  # SSE bodies have no charset; requests would use latin-1
        for line in res.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            payload = line[len("data:") :].strip()
            if not payload:
                continue
            try:
                obj = json.loads(payload)
            except json.JSONDecodeError:
                continue
            try:
                parts = obj["candidates"][0]["content"]["parts"]
                text = "".join(p.get("text", "") for p in parts)
            except (KeyError, IndexError, TypeError):
                text = ""
            if text:
                yield text

    def complete_tools(
        self,
        messages: List[ChatMessage],
        api_key: str,
        temperature: float,
        tools: Optional[List[Dict[str, Any]]] = None,
        json_mode: bool = False,
        max_tokens: Optional[int] = None,
    ) -> ProviderResponse:
        body: Dict[str, Any] = {
            "contents": self._tool_contents(messages),
            "generationConfig": self._generation_config(
                temperature, json_mode, max_tokens
            ),
        }
        system = self._system_text(messages)
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        if tools:
            body["tools"] = [{"functionDeclarations": tools}]

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={api_key}"
        )

        try:
            res = requests.post(url, json=body, timeout=REQUEST_TIMEOUT_S)
        except requests.RequestException as err:
            raise LLMError(
                f"gemini: network error — {err}", provider="google", retryable=True
            )
        if not res.ok:
            raise LLMError(
                f"gemini HTTP {res.status_code}: {res.text[:200]}",
                provider="google",
                status=res.status_code,
                retryable=res.status_code == 429
                or res.status_code >= 500
                or res.status_code == 403,
                retry_after=retry_after_seconds(res),
            )

        data = res.json()
        text_parts: List[str] = []
        tool_calls: List[Dict[str, Any]] = []
        try:
            parts = data["candidates"][0]["content"]["parts"]
        except (KeyError, IndexError, TypeError):
            parts = []
        for i, part in enumerate(parts):
            if "functionCall" in part:
                call = part["functionCall"]
                tool_calls.append(
                    {
                        "id": f"call_{i}",
                        "name": call.get("name"),
                        "arguments": call.get("args") or {},
                    }
                )
            elif "text" in part:
                text_parts.append(part["text"])

        return ProviderResponse(
            text="".join(text_parts),
            usage=_gemini_usage(data),
            tool_calls=tool_calls,
        )


class OpenAICompatibleProvider:
    def __init__(
        self,
        name: str,
        base_url: str,
        model: str,
        extra_headers: Optional[Dict[str, str]] = None,
    ):
        self.name = name
        self.base_url = base_url
        self.model = model
        self.extra_headers = extra_headers or {}

    def complete(
        self,
        messages: List[ChatMessage],
        api_key: str,
        temperature: float,
        json_mode: bool = False,
        max_tokens: Optional[int] = None,
    ) -> str:
        body: Dict[str, object] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        if max_tokens:
            body["max_tokens"] = max_tokens

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            **self.extra_headers,
        }

        try:
            res = requests.post(
                self.base_url, json=body, headers=headers, timeout=REQUEST_TIMEOUT_S
            )
        except requests.RequestException as err:
            raise LLMError(
                f"{self.name}: network error — {err}",
                provider=self.name,
                retryable=True,
            )

        if not res.ok:
            raise LLMError(
                f"{self.name} HTTP {res.status_code}: {res.text[:200]}",
                provider=self.name,
                status=res.status_code,
                retryable=res.status_code == 429
                or res.status_code >= 500
                or res.status_code in (401, 403),
                retry_after=retry_after_seconds(res),
            )

        data = res.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            content = ""
        if not content:
            raise LLMError(
                f"{self.name}: empty response", provider=self.name, retryable=True
            )
        return content

    def _headers(self, api_key: str) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            **self.extra_headers,
        }

    def _to_openai_messages(
        self, messages: List[ChatMessage]
    ) -> List[Dict[str, Any]]:
        """Translate normalized messages (incl. tool calls/results) to OpenAI."""
        out: List[Dict[str, Any]] = []
        for m in messages:
            role = m.get("role")
            if role == "assistant" and m.get("tool_calls"):
                out.append(
                    {
                        "role": "assistant",
                        "content": m.get("content") or "",
                        "tool_calls": [
                            {
                                "id": tc.get("id"),
                                "type": "function",
                                "function": {
                                    "name": tc.get("name"),
                                    "arguments": json.dumps(tc.get("arguments") or {}),
                                },
                            }
                            for tc in m["tool_calls"]
                        ],
                    }
                )
            elif role == "tool":
                out.append(
                    {
                        "role": "tool",
                        "tool_call_id": m.get("tool_call_id"),
                        "content": m.get("content") or "",
                    }
                )
            else:
                out.append({"role": role, "content": m.get("content") or ""})
        return out

    def stream(
        self,
        messages: List[ChatMessage],
        api_key: str,
        temperature: float,
        json_mode: bool = False,
        max_tokens: Optional[int] = None,
    ) -> Iterator[str]:
        body: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        if max_tokens:
            body["max_tokens"] = max_tokens

        try:
            res = requests.post(
                self.base_url,
                json=body,
                headers=self._headers(api_key),
                stream=True,
                timeout=REQUEST_TIMEOUT_S,
            )
        except requests.RequestException as err:
            raise LLMError(
                f"{self.name}: network error — {err}",
                provider=self.name,
                retryable=True,
            )
        if not res.ok:
            raise LLMError(
                f"{self.name} HTTP {res.status_code}: {res.text[:200]}",
                provider=self.name,
                status=res.status_code,
                retryable=res.status_code == 429
                or res.status_code >= 500
                or res.status_code in (401, 403),
                retry_after=retry_after_seconds(res),
            )

        res.encoding = "utf-8"  # SSE bodies have no charset; requests would use latin-1
        for line in res.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            payload = line[len("data:") :].strip()
            if not payload or payload == "[DONE]":
                if payload == "[DONE]":
                    break
                continue
            try:
                obj = json.loads(payload)
            except json.JSONDecodeError:
                continue
            try:
                delta = obj["choices"][0]["delta"].get("content")
            except (KeyError, IndexError, TypeError):
                delta = None
            if delta:
                yield delta

    def complete_tools(
        self,
        messages: List[ChatMessage],
        api_key: str,
        temperature: float,
        tools: Optional[List[Dict[str, Any]]] = None,
        json_mode: bool = False,
        max_tokens: Optional[int] = None,
    ) -> ProviderResponse:
        body: Dict[str, Any] = {
            "model": self.model,
            "messages": self._to_openai_messages(messages),
            "temperature": temperature,
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        if max_tokens:
            body["max_tokens"] = max_tokens

        try:
            res = requests.post(
                self.base_url,
                json=body,
                headers=self._headers(api_key),
                timeout=REQUEST_TIMEOUT_S,
            )
        except requests.RequestException as err:
            raise LLMError(
                f"{self.name}: network error — {err}",
                provider=self.name,
                retryable=True,
            )
        if not res.ok:
            raise LLMError(
                f"{self.name} HTTP {res.status_code}: {res.text[:200]}",
                provider=self.name,
                status=res.status_code,
                retryable=res.status_code == 429
                or res.status_code >= 500
                or res.status_code in (401, 403),
                retry_after=retry_after_seconds(res),
            )

        data = res.json()
        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError):
            message = {}

        tool_calls: List[Dict[str, Any]] = []
        for tc in message.get("tool_calls") or []:
            fn = tc.get("function", {})
            raw_args = fn.get("arguments")
            if isinstance(raw_args, str) and raw_args.strip():
                try:
                    arguments = json.loads(raw_args)
                except json.JSONDecodeError:
                    arguments = {}
            elif isinstance(raw_args, dict):
                arguments = raw_args
            else:
                arguments = {}
            tool_calls.append(
                {"id": tc.get("id"), "name": fn.get("name"), "arguments": arguments}
            )

        return ProviderResponse(
            text=message.get("content") or "",
            usage=_openai_usage(data),
            tool_calls=tool_calls,
        )
