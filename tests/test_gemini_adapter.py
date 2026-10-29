from types import SimpleNamespace

import pytest

pytest.importorskip("google.genai")
from google.genai import types  # noqa: E402

from webpilot.llm import GeminiLLM, ToolCall  # noqa: E402
from webpilot.tools import TOOL_SCHEMAS  # noqa: E402


class FakeModels:
    def __init__(self, replies): self.replies, self.calls = replies, 0

    def generate_content(self, **kw):
        r = self.replies[self.calls]
        self.calls += 1
        return r


def reply(*parts):
    return SimpleNamespace(candidates=[SimpleNamespace(content=types.Content(role="model", parts=list(parts)))])


def make(replies):
    llm = GeminiLLM("gemini-test", client=SimpleNamespace(models=FakeModels(replies)))
    llm.start("system", TOOL_SCHEMAS, "goal")
    return llm


def test_tool_schemas_convert_to_gemini_declarations():
    llm = make([])
    names = [d.name for d in llm.config.tools[0].function_declarations]
    assert names == ["observe", "goto", "click", "type", "finish"]


def test_function_call_is_parsed():
    llm = make([reply(types.Part(function_call=types.FunctionCall(name="click", args={"id": "e1"})))])
    calls = llm.next_calls()
    assert [(c.name, c.input) for c in calls] == [("click", {"id": "e1"})]


def test_plain_text_reply_means_no_calls():
    assert make([reply(types.Part(text="all done"))]).next_calls() == []


def test_results_are_sent_back_as_function_responses():
    llm = make([])
    llm.submit([(ToolCall("x", "observe", {}), "OK: page")])
    part = llm.contents[-1].parts[0]
    assert part.function_response.name == "observe"
