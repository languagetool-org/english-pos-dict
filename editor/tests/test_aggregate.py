from editor.providers.aggregate import adjudicate, gather
from editor.providers.base import CountabilityEvidence, EvidenceProvider
from editor.cache import Cache


def ev(source, verdict, confidence, detail=None):
    return CountabilityEvidence(source, verdict, confidence, detail or {}).to_dict()


def test_disagreement_flag():
    result = adjudicate([
        ev("becl", "countable", "high"),
        ev("corpus", "countable", "medium", {"plural_hits": 40, "plural_rate": 0.2}),
    ], current_tags={"NN:U"})
    assert result["disagreement"] is True
    assert result["suggestion_tag"] == "NN"


def test_agreement_no_flag():
    result = adjudicate([ev("becl", "uncountable", "high")], current_tags={"NN:U"})
    assert result["disagreement"] is False
    assert result["suggestion"] == "uncountable"


def test_corpus_used_only_when_plurals_found():
    # corpus verdict uncountable with zero plural hits -> not authoritative
    result = adjudicate([
        ev("corpus", "uncountable", "low", {"plural_hits": 0}),
    ], current_tags={"NN"})
    assert result["suggestion"] == "unknown"
    assert result["disagreement"] is False


def test_becl_beats_corpus():
    result = adjudicate([
        ev("becl", "uncountable", "high"),
        ev("corpus", "countable", "medium", {"plural_hits": 10}),
    ], current_tags={"NN"})
    assert result["suggestion"] == "uncountable"
    assert result["confidence"] == "high"


class _StubProvider(EvidenceProvider):
    def __init__(self, name, verdict):
        self.name = name
        self._verdict = verdict
        self.calls = 0

    def lookup(self, lemma):
        self.calls += 1
        return CountabilityEvidence(self.name, self._verdict, "high", {})


def test_gather_uses_cache(tmp_path):
    cache = Cache(tmp_path / "c.db")
    prov = _StubProvider("becl", "uncountable")
    gather("advice", [prov], cache)
    gather("advice", [prov], cache)  # second call should hit cache
    assert prov.calls == 1
