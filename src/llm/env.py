"""Environment parsing for the rotating LLM client.

Mirrors the adbrain convention: each provider gets a comma-separated *pool* of
API keys (empty disables the provider), and ``LLM_PROVIDER_ORDER`` controls
failover order. Values are read from the process environment; a local ``.env``
is loaded automatically when python-dotenv is installed.
"""

import os
from dataclasses import dataclass
from typing import List, Optional

try:  # optional dependency — the module still works if it is absent
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover - only hit when python-dotenv missing
    pass


def _comma_list(raw: Optional[str]) -> List[str]:
    """Split a comma-separated env value into a trimmed, non-empty list."""
    return [item.strip() for item in (raw or "").split(",") if item.strip()]


@dataclass
class LLMSettings:
    google_keys: List[str]
    groq_keys: List[str]
    openrouter_keys: List[str]
    cerebras_keys: List[str]
    provider_order: List[str]
    gemini_model: str
    groq_model: str
    openrouter_model: str
    cerebras_model: str
    temperature: float


def load_llm_settings() -> LLMSettings:
    """Read and validate LLM configuration from the environment."""
    return LLMSettings(
        google_keys=_comma_list(os.getenv("GOOGLE_AI_API_KEYS")),
        groq_keys=_comma_list(os.getenv("GROQ_API_KEYS")),
        openrouter_keys=_comma_list(os.getenv("OPENROUTER_API_KEYS")),
        cerebras_keys=_comma_list(os.getenv("CEREBRAS_API_KEYS")),
        provider_order=_comma_list(
            os.getenv("LLM_PROVIDER_ORDER") or "google,groq,openrouter,cerebras"
        ),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
        groq_model=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
        openrouter_model=os.getenv(
            "OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free"
        ),
        cerebras_model=os.getenv("CEREBRAS_MODEL", "llama-3.3-70b"),
        temperature=float(os.getenv("CHAT_MODEL_TEMPERATURE", "0.2")),
    )
