from webpilot.recovery import Failure, classify


def test_classify_overlay():
    assert classify("<div> intercepts pointer events") is Failure.OVERLAY


def test_classify_transient():
    assert classify("HTTP 503 loading /pay") is Failure.TRANSIENT


def test_classify_missing():
    assert classify("waiting for locator('#x')") is Failure.MISSING


def test_classify_unknown():
    assert classify("something odd") is Failure.UNKNOWN
