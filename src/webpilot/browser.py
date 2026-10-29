"""Browser abstraction. The agent only depends on the `Browser` protocol."""
from __future__ import annotations

from typing import Protocol

from .models import Element, Observation

_OBSERVE_JS = """
() => {
  let n = 0; const out = [];
  document.querySelectorAll('a,button,input,select,textarea,[role=button]').forEach(el => {
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height || getComputedStyle(el).visibility === 'hidden') return;
    const id = 'e' + (++n); el.setAttribute('data-wp-id', id);
    const text = (el.innerText || el.placeholder || el.getAttribute('aria-label') || '').trim();
    out.push({id, role: el.tagName.toLowerCase(), text: text.slice(0, 80), value: el.value || ''});
  });
  const overlay = !!document.querySelector(
    '[role=dialog],[aria-modal=true],[id*=cookie i],[class*=cookie i],[class*=modal i]');
  return {elements: out, overlay, text: document.body.innerText.slice(0, 1500)};
}
"""


class BrowserError(Exception):
    """Raised for any failed browser interaction."""


class Browser(Protocol):
    def start(self) -> None: ...
    def close(self) -> None: ...
    def goto(self, url: str) -> None: ...
    def reload(self) -> None: ...
    def click(self, element_id: str) -> None: ...
    def type_text(self, element_id: str, text: str) -> None: ...
    def observe(self) -> Observation: ...


class PlaywrightBrowser:
    """Playwright-backed implementation (imported lazily so tests need no browser)."""

    def __init__(self, headless: bool = True, timeout_ms: int = 8000):
        self.headless, self.timeout_ms = headless, timeout_ms
        self._pw = self._browser = self._page = None

    def start(self) -> None:
        from playwright.sync_api import sync_playwright

        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=self.headless)
        self._page = self._browser.new_page()
        self._page.set_default_timeout(self.timeout_ms)

    def close(self) -> None:
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()

    def _guard(self, fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:  # Playwright raises many subclasses
            raise BrowserError(str(exc).splitlines()[0]) from exc

    def goto(self, url: str) -> None:
        resp = self._guard(self._page.goto, url)
        if resp is not None and resp.status >= 400:
            raise BrowserError(f"HTTP {resp.status} loading {url}")

    def reload(self) -> None:
        self._guard(self._page.reload)

    def click(self, element_id: str) -> None:
        self._guard(self._page.click, f'[data-wp-id="{element_id}"]')

    def type_text(self, element_id: str, text: str) -> None:
        self._guard(self._page.fill, f'[data-wp-id="{element_id}"]', text)

    def observe(self) -> Observation:
        data = self._guard(self._page.evaluate, _OBSERVE_JS)
        return Observation(
            url=self._page.url,
            title=self._page.title(),
            text=data["text"],
            elements=[Element(**e) for e in data["elements"]],
            overlay=data["overlay"],
        )
