from dataclasses import replace

from conftest import ScriptedLLM
from webpilot.agent import Agent
from webpilot.config import Settings


def cfg(tmp_path, **kw):
    return replace(Settings(), runs_dir=str(tmp_path), backoff_seconds=0, **kw)


def test_agent_completes_and_reports_recovery(browser, tmp_path):
    llm = ScriptedLLM([("observe", {}), ("click", {"id": "go"}), ("click", {"id": "pay"}),
                       ("finish", {"success": True, "summary": "Order placed"})])
    report = Agent(browser, cfg(tmp_path), llm).run("buy it")
    assert report.success and report.recoveries == 2 and report.steps == 4
    assert list(tmp_path.glob("run-*.json"))


def test_agent_stops_at_step_limit(browser, tmp_path):
    report = Agent(browser, cfg(tmp_path, max_steps=3), ScriptedLLM([("observe", {})] * 10)).run("loop")
    assert not report.success and report.steps == 3


def test_agent_nudges_when_model_replies_in_plain_text(browser, tmp_path):
    llm = ScriptedLLM([None, ("finish", {"success": True, "summary": "done"})])
    report = Agent(browser, cfg(tmp_path), llm).run("task")
    assert report.success and llm.nudges == 1


def test_agent_opens_start_url_first(browser, tmp_path):
    llm = ScriptedLLM([("finish", {"success": True, "summary": "ok"})])
    Agent(browser, cfg(tmp_path), llm).run("task", "https://shop.test")
    assert browser.visited == ["https://shop.test"]
