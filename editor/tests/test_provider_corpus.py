from unittest.mock import patch

import requests

from editor.providers.corpus import CorpusProvider


def _fake_post(url, json, timeout):
    q = json["query"]

    class R:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            total = 120 if "NNS" in q else 1000  # plural vs all-noun
            results = [{"sentence": "many advices given", "matchText": "advices"}] \
                if (json.get("top", 0) and "NNS" in q) else []
            return {"status": "ok", "query": q, "total": total,
                    "offset": 0, "pageSize": len(results), "results": results}

    return R()


def test_corpus_plural_rate():
    with patch("editor.providers.corpus.requests.post", side_effect=_fake_post):
        ev = CorpusProvider("http://localhost:8080").lookup("advice")
    assert ev.detail["plural_rate"] == 120 / 1000
    assert ev.detail["available"] is True
    assert ev.verdict == "countable"
    assert ev.source == "corpus"


def test_corpus_no_hits_is_unknown():
    def _zero_post(url, json, timeout):
        class R:
            def raise_for_status(self):
                pass

            def json(self):
                return {"total": 0, "results": []}
        return R()

    with patch("editor.providers.corpus.requests.post", side_effect=_zero_post):
        ev = CorpusProvider().lookup("nonexistentword")
    assert ev.verdict == "unknown"


def test_corpus_server_down_is_graceful():
    def _boom(url, json, timeout):
        raise requests.ConnectionError("refused")

    with patch("editor.providers.corpus.requests.post", side_effect=_boom):
        ev = CorpusProvider().lookup("advice")
    assert ev.verdict == "unknown"
    assert ev.detail["available"] is False
