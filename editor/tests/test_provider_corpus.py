"""Tests for the corpus provider (Lucene count service)."""

from unittest.mock import Mock, patch

from editor.providers.corpus import CorpusProvider, pluralize


def test_corpus_plural_rate():
    with patch("editor.providers.corpus.requests.get") as g:
        def fake_get(url, params=None, timeout=None):
            r = Mock()
            # advice: 1000 hits, advices: 80 hits → 8% plural rate → countable
            r.json.return_value = {"count": 80 if params["q"] == "advices" else 1000}
            return r
        g.side_effect = fake_get
        ev = CorpusProvider("http://localhost:8080").lookup("advice")
    assert ev.detail["plural_rate"] == 0.08
    assert ev.detail["available"] is True
    assert ev.verdict == "countable"
    assert ev.source == "corpus"


def test_corpus_low_rate_is_uncountable():
    with patch("editor.providers.corpus.requests.get") as g:
        def fake_get(url, params=None, timeout=None):
            r = Mock()
            # furniture: 1000, furnitures: 10 → 1% → uncountable
            r.json.return_value = {"count": 10 if params["q"] == "furnitures" else 1000}
            return r
        g.side_effect = fake_get
        ev = CorpusProvider("http://localhost:8080").lookup("furniture")
    assert ev.verdict == "uncountable"


def test_corpus_no_hits_is_unknown():
    with patch("editor.providers.corpus.requests.get") as g:
        def fake_get(url, params=None, timeout=None):
            r = Mock()
            r.json.return_value = {"count": 0}
            return r
        g.side_effect = fake_get
        ev = CorpusProvider().lookup("nonexistentword")
    assert ev.verdict == "unknown"


def test_corpus_server_down_is_graceful():
    with patch("editor.providers.corpus.requests.get", side_effect=ConnectionError("refused")):
        ev = CorpusProvider().lookup("advice")
    assert ev.verdict == "unknown"
    assert ev.detail["available"] is False


def test_pluralize():
    assert pluralize("bicycle") == "bicycles"
    assert pluralize("theory") == "theories"
    assert pluralize("box") == "boxes"
    assert pluralize("bus") == "buses"
    assert pluralize("day") == "days"
    assert pluralize("advice") == "advices"


def test_uses_curated_plural_form():
    responses = [{"count": 500}, {"count": 250}]
    def fake_get(url, params=None, timeout=None):
        r = Mock()
        r.json.return_value = responses.pop(0)
        return r
    with patch("editor.providers.corpus.requests.get", side_effect=fake_get) as g:
        # 'analysis' -> curated plural 'analyses' (not naive 'analysiss')
        ev = CorpusProvider("http://localhost:8080", plural_form="analyses").lookup("analysis")
    assert ev.verdict == "countable"
    qs = [call.kwargs["params"]["q"] for call in g.call_args_list]
    assert qs == ["analysis", "analyses"]
