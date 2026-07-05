from unittest.mock import patch

import requests

from editor.providers.wiktionary import WiktionaryProvider

UNCOUNTABLE_WIKITEXT = """
==English==
===Noun===
{{en-noun|-}}

# {{lb|en|uncountable}} Opinion given.
"""

COUNTABLE_WIKITEXT = """
==English==
===Noun===
{{en-noun}}

# A two-wheeled vehicle.
"""

BOTH_WIKITEXT = """
==English==
===Noun===
{{en-noun|s|-}}

# {{lb|en|countable}} A drink; {{lb|en|uncountable}} the substance.
"""


def _mock_get(wikitext):
    def _get(url, params, timeout, headers):
        class R:
            def raise_for_status(self):
                pass

            def json(self):
                return {"parse": {"wikitext": wikitext}}
        return R()
    return _get


def test_uncountable_marker():
    with patch("editor.providers.wiktionary.requests.get",
               side_effect=_mock_get(UNCOUNTABLE_WIKITEXT)):
        ev = WiktionaryProvider().lookup("advice")
    assert ev.verdict == "uncountable"
    assert ev.confidence == "low"


def test_countable_marker():
    with patch("editor.providers.wiktionary.requests.get",
               side_effect=_mock_get(COUNTABLE_WIKITEXT)):
        ev = WiktionaryProvider().lookup("bicycle")
    assert ev.verdict == "countable"


def test_both_marker():
    with patch("editor.providers.wiktionary.requests.get",
               side_effect=_mock_get(BOTH_WIKITEXT)):
        ev = WiktionaryProvider().lookup("water")
    assert ev.verdict == "both"


def test_network_error_is_graceful():
    def _boom(url, params, timeout, headers):
        raise requests.ConnectionError("no net")

    with patch("editor.providers.wiktionary.requests.get", side_effect=_boom):
        ev = WiktionaryProvider().lookup("advice")
    assert ev.verdict == "unknown"
    assert ev.detail["available"] is False
