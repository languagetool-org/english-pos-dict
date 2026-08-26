"""BECL (Bochum English Countability Lexicon) provider.

Reads the normalised ``becl`` table (populated by editor.ingest_becl) from the
cache DB. This is the strongest signal (confidence "high"). The provider is
decoupled from the raw BECL file format: it only knows the normalised table.
"""

from editor.providers.base import EvidenceProvider, CountabilityEvidence

# Map raw BECL countability classes onto our tagset verdicts.
# Keys are lower-cased BECL class tokens; extend as the real classes are known.
BECL_CLASS_TO_VERDICT = {
    "countable": "countable",
    "count": "countable",
    "regular_count": "countable",
    "uncountable": "uncountable",
    "uncount": "uncountable",
    "mass": "uncountable",
    "regular_mass": "uncountable",
    "both": "both",
    "dual": "both",
    "plural": "both",
    "plural_only": "both",
    "collective": "both",
    "both_mass_count": "both",
}

VERDICT_TO_TAG = {
    "countable": "NN",
    "uncountable": "NN:U",
    "both": "NN:UN",
}


def classify(becl_class: str) -> str:
    """Map a raw BECL class string to a verdict, or 'unknown'."""
    if not becl_class:
        return "unknown"
    return BECL_CLASS_TO_VERDICT.get(becl_class.strip().lower(), "unknown")


class BeclProvider(EvidenceProvider):
    name = "becl"

    def __init__(self, cache):
        self.cache = cache

    def lookup(self, lemma):
        url = "https://becl.rub.de/"
        row = self.cache.get_becl(lemma)
        if row is None:
            return CountabilityEvidence(
                "becl", "unknown", "high", {"found": False}, url)
        return CountabilityEvidence(
            "becl", row["verdict"], "high",
            {"found": True, "becl_class": row["becl_class"]}, url)
