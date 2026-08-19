"""Rotating multi-provider LLM client with per-key failover and cooldown."""

from .env import LLMSettings, load_llm_settings
from .providers import (
    GeminiProvider,
    LLMError,
    OpenAICompatibleProvider,
    ProviderResponse,
)
from .rotating_client import (
    AllProvidersFailedError,
    CompletionResult,
    NoLLMKeysError,
    RotatingLLMClient,
    ToolCall,
    ToolCompletion,
)
from .tools import (
    ComplianceToolset,
    StubComplianceService,
    ToolError,
)
from .usage import record as record_usage
from .usage import reset as reset_usage
from .usage import usage_snapshot

__all__ = [
    "LLMSettings",
    "load_llm_settings",
    "GeminiProvider",
    "OpenAICompatibleProvider",
    "ProviderResponse",
    "LLMError",
    "RotatingLLMClient",
    "CompletionResult",
    "ToolCall",
    "ToolCompletion",
    "NoLLMKeysError",
    "AllProvidersFailedError",
    "ComplianceToolset",
    "StubComplianceService",
    "ToolError",
    "usage_snapshot",
    "record_usage",
    "reset_usage",
]
