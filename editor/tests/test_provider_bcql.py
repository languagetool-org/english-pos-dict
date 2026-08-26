"""Tests for the BCQL provider (word-sketch article/quantifier battery)."""

from unittest.mock import Mock, patch

from editor.providers.bcql import (BcqlProvider, ANCHORED_MIN, QUANT_MIN,
                                   COUNTABLE_RATE, MIN_DET_HITS)


def _mock_post(tot, anch, ml, det):
    """Mock keyed on which query arrives (call order: tot, anch[, ml[, det]])."""
    def fake_post(url, json=None, timeout=None):
        r = Mock()
        q = json["query"]
        if "[.,;:!?]" in q:
            r.json.return_value = {"total": anch}
        elif "much|little" in q:
            r.json.return_value = {"total": ml}
        elif "an?" in q:
            r.json.return_value = {"total": det}
        else:
            r.json.return_value = {"total": tot}
        return r
    return fake_post


def test_anchored_article_test_gives_countable_high():
    # theory: 272 a/an+punct hits → countable at HIGH confidence
    with patch("editor.providers.bcql.requests.post",
               side_effect=_mock_post(132258, 272, 0, 0)):
        ev = BcqlProvider("http://localhost:8080").lookup("theory")
    assert ev.source == "bcql"
    assert ev.verdict == "countable"
    assert ev.confidence == "high"
    assert ev.detail["test"] == "anchored-article"
    assert ev.detail["anchored_hits"] == 272
    assert "an?" in ev.detail["query"] and "[.,;:!?]" in ev.detail["query"]


def test_much_little_gives_uncountable_medium():
    # evidence: anchored below threshold but much/little = 812 → uncountable
    with patch("editor.providers.bcql.requests.post",
               side_effect=_mock_post(121650, 4, 812, 736)):
        ev = BcqlProvider("http://localhost:8080").lookup("evidence")
    assert ev.verdict == "uncountable"
    assert ev.confidence == "medium"
    assert ev.detail["test"] == "much-little"


def test_det_rate_fallback_countable():
    # no strong tier-1/tier-2 signal; rate above threshold with enough hits
    tot, det = 10000, 200          # rate .02 >= threshold
    assert det / tot >= COUNTABLE_RATE and det >= MIN_DET_HITS
    with patch("editor.providers.bcql.requests.post",
               side_effect=_mock_post(tot, 5, 20, det)):
        ev = BcqlProvider("http://localhost:8080").lookup("someword")
    assert ev.verdict == "countable"
    assert ev.detail["test"] == "det-rate"


def test_all_tiers_below_threshold_is_uncountable_low():
    # furniture-like: anch 2 < 10, much/little 1 < 50, rate .01 < threshold
    with patch("editor.providers.bcql.requests.post",
               side_effect=_mock_post(624, 2, 1, 7)):
        ev = BcqlProvider("http://localhost:8080").lookup("furniture")
    assert ev.verdict == "uncountable"
    assert ev.detail["test"] == "det-rate"


def test_high_rate_but_few_hits_is_uncountable():
    assert 3 / 100 >= COUNTABLE_RATE and 3 < MIN_DET_HITS
    with patch("editor.providers.bcql.requests.post",
               side_effect=_mock_post(100, 0, 0, 3)):
        ev = BcqlProvider("http://localhost:8080").lookup("rareword")
    assert ev.verdict == "uncountable"


def test_unknown_when_lemma_absent():
    with patch("editor.providers.bcql.requests.post",
               side_effect=_mock_post(0, 0, 0, 0)):
        ev = BcqlProvider("http://localhost:8080").lookup("nonexistentword")
    assert ev.verdict == "unknown"
    assert ev.detail["noun_hits"] == 0


def test_bcql_server_down_is_graceful():
    with patch("editor.providers.bcql.requests.post",
               side_effect=ConnectionError("refused")):
        ev = BcqlProvider().lookup("advice")
    assert ev.verdict == "unknown"
    assert ev.detail["available"] is False


def test_bcql_no_url_reports_unavailable():
    ev = BcqlProvider("").lookup("advice")
    assert ev.verdict == "unknown"
    assert ev.detail["available"] is False


def test_calibration_thresholds_consistent():
    # thresholds used by aggregate.py must match the provider's constants
    assert ANCHORED_MIN == 10 and QUANT_MIN == 50 and MIN_DET_HITS == 10
