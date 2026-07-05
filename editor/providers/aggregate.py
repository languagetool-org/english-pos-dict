"""Gather evidence from all providers and adjudicate a suggestion.

The app never auto-edits: adjudication produces an advisory suggestion and flags
disagreement with the entry's current tags. BECL is authoritative; corpus
confirms; Wiktionary is a soft fallback.
"""

from editor.providers.becl import VERDICT_TO_TAG

# Cache TTLs (seconds): BECL is local/stable, corpus/Wiktionary refresh sometimes.
TTL = {"becl": None, "corpus": 7 * 24 * 3600, "wiktionary": 30 * 24 * 3600}


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

    Priority: BECL (high) > corpus that found plurals (medium) > Wiktionary (low).
    """
    evidences = [e.to_dict() if hasattr(e, "to_dict") else e for e in evidences]
    current_tags = set(current_tags)

    suggestion = "unknown"
    confidence = "low"

    becl = _pick(evidences, "becl")
    corpus = _pick(evidences, "corpus")
    wik = _pick(evidences, "wiktionary")

    if becl:
        suggestion, confidence = becl["verdict"], "high"
    elif corpus and corpus["detail"].get("plural_hits", 0) > 0:
        suggestion, confidence = corpus["verdict"], "medium"
    elif wik:
        suggestion, confidence = wik["verdict"], "low"

    suggestion_tag = VERDICT_TO_TAG.get(suggestion)
    disagreement = bool(suggestion_tag) and suggestion_tag not in current_tags

    return {
        "verdicts": evidences,
        "suggestion": suggestion,
        "suggestion_tag": suggestion_tag,
        "confidence": confidence,
        "disagreement": disagreement,
    }
