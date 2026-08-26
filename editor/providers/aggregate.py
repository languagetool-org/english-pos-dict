"""Gather evidence from all providers and adjudicate a suggestion.

The app never auto-edits: adjudication produces an advisory suggestion and flags
disagreement with the entry's current tags. BECL is authoritative; corpus
confirms; Wiktionary is a soft fallback.
"""

from editor.providers.becl import VERDICT_TO_TAG

# Cache TTLs (seconds): BECL is local/stable, the corpus sources refresh
# sometimes, Wiktionary rarely changes.
TTL = {"becl": None, "corpus": 7 * 24 * 3600, "bcql": 7 * 24 * 3600,
       "wiktionary": 30 * 24 * 3600}


def gather(lemma, providers, cache):
    """Return list of evidence dicts, using the cache first per source."""
    evidences = []
    for provider in providers:
        cached = cache.get_evidence(lemma, provider.name)
        if cached is not None:
            evidences.append(cached)
            continue
        ev = provider.lookup(lemma).to_dict()
        cache.put_evidence(lemma, provider.name, ev, TTL.get(provider.name))
        evidences.append(ev)
    return evidences


def _pick(evidences, source):
    for ev in evidences:
        if ev["source"] == source and ev["verdict"] != "unknown":
            return ev
    return None


def adjudicate(evidences, current_tags):
    """Combine evidence into a suggestion and flag disagreement.

    Priority: BECL (high) > corpus sources that found evidence (medium) >
    Wiktionary (low). The two corpus sources (plain counts, BCQL article test)
    run over different corpora and are independent voices.
    """
    evidences = [e.to_dict() if hasattr(e, "to_dict") else e for e in evidences]
    current_tags = set(current_tags)

    suggestion = "unknown"
    confidence = "low"

    becl = _pick(evidences, "becl")
    corpus = _pick(evidences, "corpus")
    bcql = _pick(evidences, "bcql")
    wik = _pick(evidences, "wiktionary")

    if becl:
        suggestion, confidence = becl["verdict"], "high"
    elif corpus and corpus["detail"].get("plural_hits", 0) > 0:
        suggestion, confidence = corpus["verdict"], "medium"
    elif bcql and any(bcql["detail"].get(k, 0) >= m
                      for k, m in (("anchored_hits", 10), ("quantifier_hits", 50),
                                   ("det_hits", 10))):
        suggestion, confidence = bcql["verdict"], (
            "high" if bcql["confidence"] == "high" else "medium")
    elif wik:
        suggestion, confidence = wik["verdict"], "low"

    suggestion_tag = VERDICT_TO_TAG.get(suggestion)

    def _expand(tags):
        """NN:UN ('countable AND uncountable') matches either component."""
        out = set()
        for t in tags:
            out |= {"NN", "NN:U"} if t == "NN:UN" else {t}
        return out

    if suggestion_tag:
        disagreement = not (_expand({suggestion_tag}) & _expand(current_tags))
    else:
        disagreement = False

    return {
        "verdicts": evidences,
        "suggestion": suggestion,
        "suggestion_tag": suggestion_tag,
        "confidence": confidence,
        "disagreement": disagreement,
    }
