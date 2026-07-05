"""Evidence provider interface and the shared evidence record."""

from dataclasses import dataclass, field, asdict


@dataclass
class CountabilityEvidence:
    source: str                 # "becl" | "corpus" | "wiktionary"
    verdict: str                # "countable" | "uncountable" | "both" | "unknown"
    confidence: str             # "high" | "medium" | "low"
    detail: dict = field(default_factory=dict)
    source_url: str = ""

    def to_dict(self):
        return asdict(self)


class EvidenceProvider:
    name = "base"

    def lookup(self, lemma: str) -> CountabilityEvidence:
        raise NotImplementedError
