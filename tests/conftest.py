import pytest

from webpilot.browser import BrowserError
from webpilot.llm import ToolCall
from webpilot.models import Element, Observation


class FakeBrowser:
    """Scriptable in-memory browser: an overlay blocks clicks until dismissed; one 503 on 'pay'."""

    def __init__(self, overlay=True, flaky=True):
        self.overlay, self.flaky, self.page, self.value = overlay, flaky, "home", ""
        self.reloads = 0

    def start(self): ...
    def close(self): ...
    def goto(self, url): self.page, self.visited = "home", getattr(self, "visited", []) + [url]
    def reload(self): self.reloads += 1

    def click(self, eid):
        if self.overlay and eid != "e0":
            raise BrowserError("<div> intercepts pointer events")
        if eid == "e0":
            self.overlay = False
        elif eid == "pay":
            if self.flaky:
                self.flaky = False
                raise BrowserError("HTTP 503 loading /pay")
            self.page = "done"
        elif eid == "go":
            self.page = "checkout"
        else:
            raise BrowserError(f"waiting for locator {eid}")

    def type_text(self, eid, text): self.value = text

    def observe(self):
        els = [Element("e0", "button", "Accept cookies")] if self.overlay else []
        els += [Element("go", "button", "Go"), Element("pay", "button", "Pay"),
                Element("name", "input", "Name", self.value)]
        return Observation(f"https://shop.test/{self.page}", "Shop", f"page {self.page}", els, self.overlay)


@pytest.fixture
def browser():
    return FakeBrowser()


class ScriptedLLM:
    """Stands in for a real model: replays tool calls. A None item means 'answered in plain text'."""

    def __init__(self, calls):
        self.calls, self.i, self.nudges, self.last = list(calls), 0, 0, None

    def start(self, system, tools, goal): self.goal = goal

    def next_calls(self):
        if self.i >= len(self.calls):
            return []
        item = self.calls[self.i]
        self.i += 1
        return [] if item is None else [ToolCall(f"t{self.i}", item[0], item[1])]

    def submit(self, results): self.last = results

    def nudge(self, text): self.nudges += 1
