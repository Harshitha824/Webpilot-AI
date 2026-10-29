"""LLM provider adapters. The agent talks to the `LLM` interface only."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol

from .config import Settings


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    input: dict


class LLM(Protocol):
    def start(self, system: str, tools: list[dict], goal: str) -> None: ...
    def next_calls(self) -> list[ToolCall]: ...
    def submit(self, results: list[tuple[ToolCall, str]]) -> None: ...
    def nudge(self, text: str) -> None: ...


class AnthropicLLM:
    """Claude via the Anthropic Messages API (paid; needs ANTHROPIC_API_KEY)."""

    def __init__(self, model: str, client=None):
        if client is None:
            import anthropic
            client = anthropic.Anthropic()
        self.client, self.model = client, model

    def start(self, system, tools, goal):
        self.system, self.tools = system, tools
        self.messages = [{"role": "user", "content": goal}]

    def next_calls(self):
        resp = self.client.messages.create(
            model=self.model, max_tokens=2048, system=self.system,
            tools=self.tools, messages=self.messages)
        self.messages.append({"role": "assistant", "content": resp.content})
        return [ToolCall(b.id, b.name, dict(b.input)) for b in resp.content if b.type == "tool_use"]

    def submit(self, results):
        self.messages.append({"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": c.id, "content": text} for c, text in results]})

    def nudge(self, text):
        self.messages.append({"role": "user", "content": text})


class GeminiLLM:
    """Google Gemini via the google-genai SDK (free tier; needs GEMINI_API_KEY)."""

    RETRY_CODES = (429, 500, 503)

    def __init__(self, model: str, client=None):
        from google import genai
        from google.genai import types
        self.types = types
        self.client = client or genai.Client()  # reads GEMINI_API_KEY from the environment
        self.model = model

    def start(self, system, tools, goal):
        t = self.types
        decls = []
        for tool in tools:
            schema = tool["input_schema"]
            props = schema.get("properties") or {}
            params = None
            if props:  # Gemini rejects object schemas with no properties
                params = {"type": "object", "properties": props}
                if schema.get("required"):
                    params["required"] = schema["required"]
            decls.append(t.FunctionDeclaration(
                name=tool["name"], description=tool["description"], parameters=params))
        self.config = t.GenerateContentConfig(system_instruction=system, tools=[t.Tool(function_declarations=decls)])
        self.contents = [t.Content(role="user", parts=[t.Part(text=goal)])]

    def _generate(self):
        for attempt in range(5):  # free tier is rate limited: back off and retry
            try:
                return self.client.models.generate_content(
                    model=self.model, contents=self.contents, config=self.config)
            except Exception as exc:
                if getattr(exc, "code", None) in self.RETRY_CODES and attempt < 4:
                    time.sleep(min(60, 5 * 2 ** attempt))
                    continue
                raise

    def next_calls(self):
        resp = self._generate()
        candidates = getattr(resp, "candidates", None) or []
        content = candidates[0].content if candidates else None
        if content is None or not content.parts:
            return []
        self.contents.append(content)  # keep the model turn intact (includes any thought signatures)
        calls = []
        for i, part in enumerate(content.parts):
            fc = getattr(part, "function_call", None)
            if fc:
                calls.append(ToolCall(f"g{len(self.contents)}-{i}", fc.name, dict(fc.args or {})))
        return calls

    def submit(self, results):
        t = self.types
        parts = [t.Part.from_function_response(name=c.name, response={"result": text}) for c, text in results]
        self.contents.append(t.Content(role="user", parts=parts))

    def nudge(self, text):
        t = self.types
        self.contents.append(t.Content(role="user", parts=[t.Part(text=text)]))


def make_llm(settings: Settings) -> LLM:
    if settings.provider == "gemini":
        return GeminiLLM(settings.model_name())
    if settings.provider == "anthropic":
        return AnthropicLLM(settings.model_name())
    raise ValueError(f"Unknown provider: {settings.provider!r} (use 'gemini' or 'anthropic')")
