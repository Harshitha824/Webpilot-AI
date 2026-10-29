"""Tool schemas exposed to the model and the executor that runs them."""
from __future__ import annotations

from .browser import Browser, BrowserError
from .models import ToolResult
from .recovery import Failure, RecoveryPolicy, classify
from .verifier import Verifier


def _schema(name, desc, props=None, required=None):
    return {"name": name, "description": desc,
            "input_schema": {"type": "object", "properties": props or {}, "required": required or []}}


_S = {"type": "string"}
TOOL_SCHEMAS = [
    _schema("observe", "Read the current page: elements with ids, and visible text."),
    _schema("goto", "Navigate to a URL.", {"url": _S}, ["url"]),
    _schema("click", "Click an element by id from the latest observation.", {"id": _S}, ["id"]),
    _schema("type", "Replace the text of an input element.", {"id": _S, "text": _S}, ["id", "text"]),
    _schema("finish", "End the task with an honest report.",
            {"success": {"type": "boolean"}, "summary": _S}, ["success", "summary"]),
]


class ToolExecutor:
    def __init__(self, browser: Browser, recovery: RecoveryPolicy, verifier: Verifier | None = None):
        self.browser, self.recovery = browser, recovery
        self.verifier = verifier or Verifier()
        self.finished: dict | None = None

    def execute(self, name: str, args: dict) -> ToolResult:
        handler = getattr(self, f"_do_{name}", None)
        if handler is None:
            return ToolResult(False, f"Unknown tool: {name}")
        try:
            return handler(**args)
        except TypeError as exc:
            return ToolResult(False, f"Bad arguments for {name}: {exc}")

    # -- tools -------------------------------------------------------------
    def _do_observe(self) -> ToolResult:
        try:
            return ToolResult(True, "Observed page.", observation=self.browser.observe())
        except BrowserError as exc:
            return ToolResult(False, str(exc))

    def _do_finish(self, success: bool, summary: str) -> ToolResult:
        self.finished = {"success": success, "summary": summary}
        return ToolResult(True, "Task closed.")

    def _do_goto(self, url: str) -> ToolResult:
        return self._with_recovery(
            lambda: self.browser.goto(url),
            lambda before, after: self.verifier.after_goto(after, url), "Navigated")

    def _do_click(self, id: str) -> ToolResult:
        return self._with_recovery(
            lambda: self.browser.click(id), self.verifier.after_click, f"Clicked {id}")

    def _do_type(self, id: str, text: str) -> ToolResult:
        return self._with_recovery(
            lambda: self.browser.type_text(id, text),
            lambda before, after: self.verifier.after_type(after, id, text), f"Typed into {id}")

    # -- act, verify, recover ------------------------------------------------
    def _with_recovery(self, act, verify, ok_msg: str) -> ToolResult:
        before = self._safe_observe()
        recovered, last_error = False, ""
        for attempt in range(self.recovery.max_retries + 1):
            try:
                act()
                after = self.browser.observe()
                v = verify(before, after)
                msg = ok_msg if v.passed else f"{ok_msg}, but verification failed"
                return ToolResult(v.passed, msg, recovered=recovered, verification=v, observation=after)
            except BrowserError as exc:
                last_error = str(exc)
                kind = classify(last_error)
                if kind in (Failure.MISSING, Failure.UNKNOWN) or attempt == self.recovery.max_retries:
                    break
                if not self.recovery.attempt(kind, attempt):
                    break
                recovered = True
        kind = classify(last_error).value
        return ToolResult(False, f"{last_error} [{kind}]. Observe and adapt.",
                          observation=self._safe_observe())

    def _safe_observe(self):
        try:
            return self.browser.observe()
        except BrowserError:
            return None
