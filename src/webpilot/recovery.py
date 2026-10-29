"""Failure classification and recovery strategies."""
from __future__ import annotations

import re
import time
from enum import Enum

from .browser import Browser, BrowserError

DISMISS = re.compile(r"\b(accept|agree|got it|allow|close|dismiss|ok|no thanks)\b", re.I)


class Failure(str, Enum):
    OVERLAY = "overlay"      # something intercepts clicks
    TRANSIENT = "transient"  # 5xx, timeouts, network blips
    MISSING = "missing"      # element gone or renamed
    UNKNOWN = "unknown"


def classify(message: str) -> Failure:
    m = message.lower()
    if "intercepts pointer events" in m or "overlay" in m or "obscured" in m:
        return Failure.OVERLAY
    if re.search(r"http 5\d\d|net::|503|502|temporar", m):
        return Failure.TRANSIENT
    if "waiting for locator" in m or "not found" in m or "no element" in m:
        return Failure.MISSING
    if "timeout" in m:
        return Failure.TRANSIENT
    return Failure.UNKNOWN


class RecoveryPolicy:
    """Applies a best-effort fix for a classified failure. Returns True if a fix was tried."""

    def __init__(self, browser: Browser, max_retries: int = 2, backoff: float = 1.0):
        self.browser, self.max_retries, self.backoff = browser, max_retries, backoff

    def attempt(self, kind: Failure, attempt: int) -> bool:
        if kind is Failure.OVERLAY:
            return self._dismiss_overlay()
        if kind is Failure.TRANSIENT:
            time.sleep(self.backoff * (2 ** attempt))
            try:
                self.browser.reload()
            except BrowserError:
                pass
            return True
        return False  # MISSING / UNKNOWN: the model must re-observe and re-plan

    def _dismiss_overlay(self) -> bool:
        for el in self.browser.observe().elements:
            if el.role in {"button", "a"} and DISMISS.search(el.text):
                try:
                    self.browser.click(el.id)
                    return True
                except BrowserError:
                    continue
        return False
