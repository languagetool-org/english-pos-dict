"""BCQL evidence via the word-sketch (BlackLab) server.

Three-tier battery over the tagged academic corpus (Frontiers in Psychology):

1. **Anchored article test** — ``[word="an?"] [lemma="X"] [word="[.,;:!?]"]``
   ("a/an X" at a clause boundary, i.e. the noun heads its phrase).
   High precision: calibrated on 12 known words, countables scored >= 36 and
   uncountables <= 4. >= ANCHORED_MIN hits => countable, high confidence.
2. **Mass quantifier test** — ``[word="much|little"] [lemma="X"]``.
   Presence is strong mass evidence: information 542, evidence 812,
   knowledge 149, vs <= 16 for any countable tested.
   >= QUANT_MIN hits => uncountable, medium confidence.
3. **Fallback determiner rate** — bare ``a/an X`` bigram over total frequency,
   countable at rate >= COUNTABLE_RATE with >= MIN_DET_HITS (medium), else
   uncountable (low — silence is not proof).

Calibration (2026-08): analysis 53/321/5, theory 272/76/16, bicycle 36/0/0,
method 48/199/3, hypothesis 147/111/0 — anchored/every/much-little;
information 1/-/542, furniture 2/0/1, advice 2/1/4, equipment 0/0/5,
software 0/4/1, knowledge 2/24/149, evidence 4/5/812.

This is a different corpus from the plain /count service; both run as
independent evidence sources.
"""

import requests

from editor.providers.base import EvidenceProvider, CountabilityEvidence

# Tier 1: anchored article hits above this => countable (high confidence).
ANCHORED_MIN = 10
# Tier 2: much/little co-occurrences above this => uncountable (medium).
QUANT_MIN = 50
# Tier 3 fallback rates for the bare determiner bigram.
# 0.015 keeps every calibrated countable (analysis .0153 is the lowest)
# while excluding software (.0146, the highest uncountable).
COUNTABLE_RATE = 0.015
MIN_DET_HITS = 10


class BcqlProvider(EvidenceProvider):
    name = "bcql"

    def __init__(self, base_url="", timeout=60):
        self.base_url = base_url.rstrip("/") or ""
        self.timeout = timeout

    def _total(self, query):
        if not self.base_url:
            raise requests.RequestException("BCQL URL not configured")
        r = requests.post(f"{self.base_url}/api/bcql",
                          json={"query": query, "top": 1, "offset": 0},
                          timeout=self.timeout)
        r.raise_for_status()
        return int(r.json().get("total", 0))

    def lookup(self, lemma):
        esc = lemma.replace('"', "")
        try:
            tot = self._total(f'[lemma="{esc}"]')
            if tot == 0:
                return CountabilityEvidence(
                    "bcql", "unknown", "low",
                    {"error": f"'{esc}' absent from corpus", "available": True,
                     "noun_hits": 0, "source_url": self.base_url})
            anch = self._total(
                f'[word="an?"] [lemma="{esc}"] [word="[.,;:!?]"]')
            if anch >= ANCHORED_MIN:
                return CountabilityEvidence(
                    "bcql", "countable", "high",
                    {"anchored_hits": anch, "noun_hits": tot,
                     "test": "anchored-article",
                     "query": f'[word="an?"] [lemma="{esc}"] [word="[.,;:!?]"]',
                     "available": True, "source_url": self.base_url})
            ml = self._total(f'[word="much|little"] [lemma="{esc}"]')
            if ml >= QUANT_MIN:
                return CountabilityEvidence(
                    "bcql", "uncountable", "medium",
                    {"quantifier_hits": ml, "noun_hits": tot,
                     "test": "much-little",
                     "available": True, "source_url": self.base_url})
            det = self._total(f'[word="an?"] [lemma="{esc}"]')
        except (requests.RequestException, ConnectionError) as exc:
            return CountabilityEvidence(
                "bcql", "unknown", "low",
                {"error": str(exc), "available": False,
                 "source_url": self.base_url})

        rate = (det / tot) if tot else 0.0
        if rate >= COUNTABLE_RATE and det >= MIN_DET_HITS:
            verdict, conf = "countable", "medium"
        else:
            verdict, conf = "uncountable", "low"  # silence != proof

        return CountabilityEvidence(
            "bcql", verdict, conf,
            {"det_hits": det, "anchored_hits": anch, "quantifier_hits": ml,
             "noun_hits": tot, "det_rate": rate, "test": "det-rate",
             "available": True, "source_url": self.base_url})
