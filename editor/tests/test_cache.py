from editor.cache import Cache


def test_evidence_roundtrip(tmp_path):
    c = Cache(tmp_path / "c.db")
    c.put_evidence("advice", "becl", {"verdict": "uncountable", "confidence": "high"})
    got = c.get_evidence("advice", "becl")
    assert got["verdict"] == "uncountable"


def test_missing_returns_none(tmp_path):
    c = Cache(tmp_path / "c.db")
    assert c.get_evidence("nope", "becl") is None


def test_ttl_expiry(tmp_path):
    c = Cache(tmp_path / "c.db")
    c.put_evidence("x", "corpus", {"v": 1}, ttl_seconds=0)
    assert c.get_evidence("x", "corpus") is None


def test_becl_roundtrip(tmp_path):
    c = Cache(tmp_path / "c.db")
    c.put_becl("advice", "uncountable", "uncountable")
    assert c.get_becl("advice") == {"becl_class": "uncountable", "verdict": "uncountable"}
    assert c.get_becl("missing") is None


def test_issues_snapshot(tmp_path):
    c = Cache(tmp_path / "c.db")
    assert c.get_issues_snapshot() is None
    c.put_issues_snapshot([{"rule": "orphan-plural", "lemma": "scissors"}])
    snap = c.get_issues_snapshot()
    assert snap[0]["lemma"] == "scissors"
