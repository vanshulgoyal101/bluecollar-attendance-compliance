"""Tests for the offline/mock fallback logic of LLMComplianceClient.

These exercise the deterministic branch used when no API key is configured, so
they need neither network access nor the litellm dependency.
"""

import pytest

from src.llm_client import LLMComplianceClient, ExceptionAnalysis


@pytest.fixture
def offline_client(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    return LLMComplianceClient()


def test_empty_note_is_not_exempt(offline_client):
    result = offline_client.analyze_note("", "LT")
    assert isinstance(result, ExceptionAnalysis)
    assert result.is_exempt is False
    assert result.exception_type == "None"


def test_fmla_note_is_exempt(offline_client):
    result = offline_client.analyze_note("Employee is on FMLA leave.", "IANS")
    assert result.is_exempt is True
    assert result.exception_type == "FMLA"


def test_family_medical_leave_phrase_is_exempt(offline_client):
    result = offline_client.analyze_note("Approved family medical leave for surgery.", "IANS")
    assert result.is_exempt is True
    assert result.exception_type == "FMLA"


def test_supervisor_override_phrases_are_exempt(offline_client):
    for phrase in ("Let it slide this time", "This was approved", "Excused by manager"):
        result = offline_client.analyze_note(phrase, "LT")
        assert result.is_exempt is True, phrase
        assert result.exception_type == "Supervisor Override"


def test_protected_sick_period_is_exempt(offline_client):
    result = offline_client.analyze_note("Sick day is protected (SKPS window).", "skp")
    assert result.is_exempt is True
    assert result.exception_type == "Approved Sick Leave"


def test_unremarkable_note_is_not_exempt(offline_client):
    result = offline_client.analyze_note("Employee overslept, no valid reason.", "LT")
    assert result.is_exempt is False
    assert result.exception_type == "None"
