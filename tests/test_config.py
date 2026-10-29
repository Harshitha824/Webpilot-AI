from webpilot.config import Settings
from webpilot.llm import make_llm
import pytest


def test_default_models_per_provider():
    assert Settings(provider="gemini").model_name() == "gemini-2.5-flash"
    assert Settings(provider="anthropic").model_name() == "claude-sonnet-5-5"
    assert Settings(provider="gemini", model="x").model_name() == "x"


def test_from_env(monkeypatch):
    monkeypatch.setenv("WEBPILOT_PROVIDER", "Anthropic")
    assert Settings.from_env().provider == "anthropic"


def test_unknown_provider_rejected():
    with pytest.raises(ValueError):
        make_llm(Settings(provider="nope"))
