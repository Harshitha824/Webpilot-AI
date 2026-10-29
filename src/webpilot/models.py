"""Plain data types shared across the agent."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Element:
    id: str          # stable handle assigned during observation, e.g. "e3"
    role: str        # tag name: a, button, input...
    text: str
    value: str = ""


@dataclass
class Observation:
    url: str
    title: str
    text: str                                  # visible page text (truncated)
    elements: list[Element] = field(default_factory=list)
    overlay: bool = False                      # modal / cookie banner detected

    def find(self, element_id: str) -> Element | None:
        return next((e for e in self.elements if e.id == element_id), None)

    def render(self) -> str:
        lines = [f"URL: {self.url}", f"Title: {self.title}"]
        if self.overlay:
            lines.append("WARNING: an overlay or dialog may be blocking the page.")
        lines.append("Elements:")
        for e in self.elements:
            val = f" value={e.value!r}" if e.value else ""
            lines.append(f"  [{e.id}] <{e.role}> {e.text}{val}")
        lines.append(f"Text: {self.text}")
        return "\n".join(lines)


@dataclass(frozen=True)
class Verification:
    claim: str
    passed: bool
    evidence: str


@dataclass
class ToolResult:
    ok: bool
    message: str
    recovered: bool = False
    verification: Verification | None = None
    observation: Observation | None = None

    def to_text(self) -> str:
        parts = [("OK: " if self.ok else "FAILED: ") + self.message]
        if self.recovered:
            parts.append("(recovered automatically after a failure)")
        if self.verification:
            v = self.verification
            parts.append(f"Verification {'PASSED' if v.passed else 'FAILED'}: {v.evidence}")
        if self.observation:
            parts.append(self.observation.render())
        return "\n".join(parts)
