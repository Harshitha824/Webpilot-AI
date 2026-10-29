from webpilot.models import Element, Observation
from webpilot.verifier import Verifier

V = Verifier()


def obs(url="https://a.test/1", text="t", value=""):
    return Observation(url, "T", text, [Element("e1", "input", "n", value)])


def test_click_detects_change():
    assert V.after_click(obs(), obs(url="https://a.test/2")).passed


def test_click_detects_no_effect():
    assert not V.after_click(obs(), obs()).passed


def test_type_checks_value():
    assert V.after_type(obs(value="Ada"), "e1", "Ada").passed
    assert not V.after_type(obs(value=""), "e1", "Ada").passed


def test_goto_checks_host():
    assert V.after_goto(obs(), "https://a.test/x").passed
    assert not V.after_goto(obs(), "https://b.test/").passed
