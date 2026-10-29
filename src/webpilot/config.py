"""Runtime configuration, loaded from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_MODELS = {"gemini": "gemini-2.5-flash", "anthropic": "claude-sonnet-5-5"}


@dataclass(frozen=True)
class Settings:
    provider: str = "gemini"      # "gemini" (free tier) or "anthropic" (paid)
    model: str = ""               # empty = provider default
    max_steps: int = 40
    max_retries: int = 2
    headless: bool = True
    backoff_seconds: float = 1.0
    runs_dir: str = "runs"

    def model_name(self) -> str:
        return self.model or DEFAULT_MODELS.get(self.provider, "")

    @classmethod
    def from_env(cls) -> "Settings":
        env = os.environ
        return cls(
            provider=env.get("WEBPILOT_PROVIDER", cls.provider).lower(),
            model=env.get("WEBPILOT_MODEL", ""),
            max_steps=int(env.get("WEBPILOT_MAX_STEPS", cls.max_steps)),
            max_retries=int(env.get("WEBPILOT_MAX_RETRIES", cls.max_retries)),
            headless=env.get("WEBPILOT_HEADLESS", "true").lower() != "false",
        )
