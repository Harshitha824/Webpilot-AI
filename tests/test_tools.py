from webpilot.recovery import RecoveryPolicy
from webpilot.tools import ToolExecutor


def make(browser):
    return ToolExecutor(browser, RecoveryPolicy(browser, max_retries=2, backoff=0))


def test_overlay_is_dismissed_then_click_succeeds(browser):
    r = make(browser).execute("click", {"id": "go"})
    assert r.ok and r.recovered and browser.page == "checkout"


def test_transient_error_retried_with_reload(browser):
    ex = make(browser)
    ex.execute("click", {"id": "go"})
    r = ex.execute("click", {"id": "pay"})
    assert r.ok and r.recovered and browser.reloads == 1 and browser.page == "done"


def test_missing_element_is_not_blindly_retried(browser):
    browser.overlay = False
    r = make(browser).execute("click", {"id": "ghost"})
    assert not r.ok and "missing" in r.message


def test_type_is_verified(browser):
    browser.overlay = False
    r = make(browser).execute("type", {"id": "name", "text": "Ada"})
    assert r.ok and r.verification.passed


def test_unknown_tool(browser):
    assert not make(browser).execute("explode", {}).ok
