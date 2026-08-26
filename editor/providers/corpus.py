"""Corpus evidence via a local Lucene count service.

Counts the lemma's plural form vs the singular form in the corpus and derives a
plural rate. The service is a plain Lucene term-count endpoint (GET /count?q=&field=en),
not a BCQL index. The plural form is taken from the dictionary's own inflected
entries when available (lexicographer-curated), falling back to a simple rule.

Because the corpus has recall gaps, corpus *silence* is treated as weak
evidence, never proof.
"""

import requests

from editor.providers.base import EvidenceProvider, CountabilityEvidence

# Plural-rate above this counts as evidence for countability.
COUNTABLE_THRESHOLD = 0.05


def pluralize(lemma):
    """Simple English pluralisation fallback (no lexicon available)."""
    low = lemma.lower()
    if low.endswith(("s", "x", "z", "ch", "sh")):
        return low + "es"
    if low.endswith("y") and len(low) > 1 and low[-2] not in "aeiou":
        return low[:-1] + "ies"
    return low + "s"


class CorpusProvider(EvidenceProvider):
    name = "corpus"

    def __init__(self, base_url="", plural_form=None, timeout=10):
        self.base_url = base_url.rstrip("/") or ""
        self.plural_form = plural_form
        self.timeout = timeout

    def _count(self, term):
        if not self.base_url:
            raise requests.RequestException("Corpus URL not configured")
        r = requests.get(f"{self.base_url}/count",
                         params={"q": term, "field": "en"},
                         timeout=self.timeout)
        r.raise_for_status()
        return int(r.json().get("count", 0))

    def lookup(self, lemma):
        esc = lemma.replace('"', "")
        if not self.base_url:
            return CountabilityEvidence(
                "corpus", "unknown", "low",
                {"error": "Corpus URL not configured", "available": False,
                 "source_url": self.base_url})
        try:
            plural_form = self.plural_form or pluralize(esc)
            singular = self._count(esc)
            plural = self._count(plural_form)
        except (requests.RequestException, ConnectionError) as exc:
            return CountabilityEvidence(
                "corpus", "unknown", "low",
                {"error": str(exc), "available": False, "source_url": self.base_url})

        rate = (plural / singular) if singular else 0.0
        if singular == 0:
            verdict, conf = "unknown", "low"
        elif rate >= COUNTABLE_THRESHOLD:
            verdict, conf = "countable", "medium"
        else:
            verdict, conf = "uncountable", "low"  # silence != proof

        return CountabilityEvidence(
            "corpus", verdict, conf,
            {"plural_rate": rate, "plural_hits": plural,
             "noun_hits": singular, "examples": [], "available": True,
             "source_url": self.base_url})
