"""Corpus evidence via the local ConceptSketch BCQL endpoint.

Counts plural (NNS) vs all-noun (NN.*) hits for a lemma and derives a plural
rate. Because the clean academic corpus has recall gaps, corpus *silence* is
treated as weak evidence, never proof.
"""

import requests

from editor.providers.base import EvidenceProvider, CountabilityEvidence

# Plural-rate above this counts as evidence for countability.
COUNTABLE_THRESHOLD = 0.05


class CorpusProvider(EvidenceProvider):
    name = "corpus"

    def __init__(self, base_url="http://localhost:8080", timeout=10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _count(self, query):
        r = requests.post(f"{self.base_url}/api/bcql",
                          json={"query": query, "top": 0, "offset": 0},
                          timeout=self.timeout)
        r.raise_for_status()
        return r.json().get("total", 0)

    def _examples(self, query, top=5):
        r = requests.post(f"{self.base_url}/api/bcql",
                          json={"query": query, "top": top, "offset": 0},
                          timeout=self.timeout)
        r.raise_for_status()
        return r.json().get("results", [])

    def lookup(self, lemma):
        esc = lemma.replace('"', "")
        try:
            plural_q = f'[lemma="{esc}" & xpos="NNS"]'
            noun_q = f'[lemma="{esc}" & xpos="NN.*"]'
            plural = self._count(plural_q)
            allnoun = self._count(noun_q)
            examples = self._examples(plural_q) if plural else []
        except requests.RequestException as exc:
            return CountabilityEvidence(
                "corpus", "unknown", "low",
                {"error": str(exc), "available": False})

        rate = (plural / allnoun) if allnoun else 0.0
        if allnoun == 0:
            verdict, conf = "unknown", "low"
        elif rate >= COUNTABLE_THRESHOLD:
            verdict, conf = "countable", "medium"
        else:
            verdict, conf = "uncountable", "low"  # silence != proof

        return CountabilityEvidence(
            "corpus", verdict, conf,
            {"plural_rate": rate, "plural_hits": plural,
             "noun_hits": allnoun, "examples": examples, "available": True})
