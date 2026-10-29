"""The agent loop: plan -> act -> verify -> recover, driven by an LLM with tool use."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from .browser import Browser
from .config import Settings
from .llm import LLM, make_llm
from .recovery import RecoveryPolicy
from .tools import TOOL_SCHEMAS, ToolExecutor

SYSTEM_PROMPT = """You are WebPilot, a careful web automation agent.
1. Begin with `observe`. Use only element ids from the latest observation.
2. Every action returns a verification. If it FAILED, do not assume success: observe and adapt.
3. After a failure (overlay, missing element, server error), diagnose, change approach, and continue.
   Never repeat an identical failing action more than twice without re-observing.
4. Respect every constraint in the goal (price limits, required fields). Never invent data.
5. Always end by calling the `finish` tool with an honest summary. If the goal is impossible,
   call it with success=false."""

NUDGE = "Continue using the tools. When the task is complete or impossible, call `finish` with a summary."


@dataclass
class RunReport:
    success: bool
    summary: str
    steps: int
    failures: int
    recoveries: int
    trace: list[dict] = field(default_factory=list)


class Agent:
    def __init__(self, browser: Browser, settings: Settings | None = None, llm: LLM | None = None):
        self.browser = browser
        self.settings = settings or Settings.from_env()
        self.llm = llm or make_llm(self.settings)
        self.executor = ToolExecutor(
            browser, RecoveryPolicy(browser, self.settings.max_retries, self.settings.backoff_seconds))

    def run(self, goal: str, start_url: str | None = None) -> RunReport:
        if start_url:
            self.executor.execute("goto", {"url": start_url})  # open the start page right away
        self.llm.start(SYSTEM_PROMPT, TOOL_SCHEMAS, goal + (f"\nStart URL: {start_url}" if start_url else ""))
        trace, failures, recoveries, steps, nudges = [], 0, 0, 0, 0
        while steps < self.settings.max_steps and not self.executor.finished:
            calls = self.llm.next_calls()
            if not calls:
                if nudges < 2:  # model answered in plain text: remind it to use tools / finish
                    nudges += 1
                    self.llm.nudge(NUDGE)
                    continue
                break
            results = []
            for call in calls:
                steps += 1
                result = self.executor.execute(call.name, call.input)
                failures += 0 if result.ok else 1
                recoveries += 1 if result.recovered else 0
                trace.append({"step": steps, "tool": call.name, "input": call.input, "ok": result.ok,
                              "recovered": result.recovered, "message": result.message})
                results.append((call, result.to_text()))
            self.llm.submit(results)
        done = self.executor.finished or {"success": False, "summary": "Stopped before finishing (step limit)."}
        report = RunReport(done["success"], done["summary"], steps, failures, recoveries, trace)
        self._save(report)
        return report

    def _save(self, report: RunReport) -> None:
        out = Path(self.settings.runs_dir)
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"run-{int(time.time())}.json"
        path.write_text(json.dumps(report.__dict__, indent=2, default=str))
