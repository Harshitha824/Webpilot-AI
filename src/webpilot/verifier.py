"""Postcondition checks. Every action is verified against observed page state."""
from __future__ import annotations

from .models import Observation, Verification


class Verifier:
    def after_click(self, before: Observation | None, after: Observation) -> Verification:
        if before is None:
            return Verification("click had an observable effect", True, f"page at {after.url}")
        changed = (
            before.url != after.url
            or before.text != after.text
            or [e.id + e.text for e in before.elements] != [e.id + e.text for e in after.elements]
        )
        evidence = f"page now at {after.url}" if changed else "page unchanged after click"
        return Verification("click had an observable effect", changed, evidence)

    def after_type(self, after: Observation, element_id: str, text: str) -> Verification:
        el = after.find(element_id)
        ok = el is not None and el.value == text
        got = el.value if el else "<element missing>"
        return Verification(f"input {element_id} holds the typed text", ok, f"value is {got!r}")

    def after_goto(self, after: Observation, url: str) -> Verification:
        host = url.split("//")[-1].split("/")[0]
        ok = host in after.url
        return Verification("navigation reached the target host", ok, f"url is {after.url}")
