"""Wiktionary soft-fallback countability signal (live MediaWiki API).

Parses the English section wikitext for the standard countability markers.
Low confidence by design; used mainly when BECL is silent. Never raises to the
caller (network/parse failures degrade to verdict "unknown").
"""

import re

import requests

from editor.providers.base import EvidenceProvider, CountabilityEvidence

API = "https://en.wiktionary.org/w/api.php"

# {{en-noun|-}} and {{en-noun|!}} mark uncountable / no-plural; {{lb|en|uncountable}}
_UNCOUNTABLE = re.compile(r"\{\{en-noun\|[-!~]\}\}|\{\{lb\|en\|[^}]*uncountable")
# a plain {{en-noun}} or {{en-noun|s}} / {{en-noun|es}} implies a countable use
_COUNTABLE = re.compile(r"\{\{en-noun(\}\}|\|(?![-!~])[^}]*\}\})")


class WiktionaryProvider(EvidenceProvider):
    name = "wiktionary"

    def __init__(self, timeout=10):
        self.timeout = timeout

    def _wikitext(self, lemma):
        r = requests.get(API, params={
            "action": "parse", "page": lemma, "prop": "wikitext",
            "format": "json", "formatversion": "2",
        }, timeout=self.timeout, headers={"User-Agent": "english-pos-dict-editor"})
        r.raise_for_status()
        data = r.json()
        if "error" in data:
            return None
        return data.get("parse", {}).get("wikitext", "")

    def lookup(self, lemma):
        url = f"https://en.wiktionary.org/wiki/{lemma}"
        try:
            text = self._wikitext(lemma)
        except requests.RequestException as exc:
            return CountabilityEvidence(
                "wiktionary", "unknown", "low",
                {"error": str(exc), "available": False}, url)
        if not text:
            return CountabilityEvidence(
                "wiktionary", "unknown", "low",
                {"available": True, "found": False}, url)

        uncountable = bool(_UNCOUNTABLE.search(text))
        countable = bool(_COUNTABLE.search(text))
        if uncountable and countable:
            verdict = "both"
        elif uncountable:
            verdict = "uncountable"
        elif countable:
            verdict = "countable"
        else:
            verdict = "unknown"
        return CountabilityEvidence(
            "wiktionary", verdict, "low",
            {"available": True, "found": True,
             "uncountable_marker": uncountable, "countable_marker": countable},
            url)
