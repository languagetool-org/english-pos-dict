import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from editor.app import create_app
from editor.providers.base import CountabilityEvidence

FIX = Path(__file__).parent / "fixtures" / "mini.txt"


@pytest.fixture
def client(tmp_path):
    src = tmp_path / "mini.txt"
    shutil.copy(FIX, src)
    app = create_app({
        "TESTING": True,
        "SOURCE_FILES": [str(src)],
        "DB_PATH": str(tmp_path / "c.db"),
        "CORPUS_URL": "http://localhost:9",
    })
    return app.test_client()


def test_search_returns_matching_entry(client):
    r = client.get("/search?q=bicycle")
    assert r.status_code == 200
    assert b"bicycle" in r.data


def test_search_by_inflected_form(client):
    r = client.get("/search?q=bicycles")  # plural form, via expansion index
    assert r.status_code == 200
    assert b"bicycle" in r.data


def test_entry_page(client):
    r = client.get("/entry/mini.txt/2")
    assert r.status_code == 200
    assert b"bicycle=noun=all" in r.data


def test_validate_endpoint(client):
    r = client.post("/api/validate", json={"line": "beautiful=ZZ=all"})
    data = r.get_json()
    assert any("unknown tag" in p for p in data["problems"])
    assert "expansion" in data


def test_save_valid_line(client):
    r = client.post("/api/save",
                    json={"file": "mini.txt", "line_no": 2, "line": "bicycle=noun=gb"})
    assert r.status_code == 200


def test_save_rejects_invalid(client):
    r = client.post("/api/save",
                    json={"file": "mini.txt", "line_no": 2, "line": "bicycle=ZZ=all"})
    assert r.status_code == 400
    assert "problems" in r.get_json()


def test_issues_page_lists_seeded_case(tmp_path):
    src = tmp_path / "s.txt"
    src.write_text("advice=advice/NN:U,advices/NNS=all\n", encoding="utf-8")
    app = create_app({"SOURCE_FILES": [str(src)], "DB_PATH": str(tmp_path / "c.db")})
    c = app.test_client()
    r = c.get("/issues")
    assert r.status_code == 200
    assert b"uncountable-with-plural" in r.data
    assert b"advice" in r.data


def test_rescan_endpoint(client):
    r = client.post("/api/rescan", json={})
    assert r.status_code == 200
    assert "count" in r.get_json()


def test_evidence_endpoint_mocked(client):
    def fake_gather(lemma, providers, cache):
        return [
            CountabilityEvidence("becl", "countable", "high", {"found": True}).to_dict(),
            CountabilityEvidence("corpus", "countable", "medium",
                                 {"plural_hits": 40, "available": True}).to_dict(),
        ]
    with patch("editor.app.gather", side_effect=fake_gather):
        r = client.get("/api/evidence/advice")
    data = r.get_json()
    assert "verdicts" in data and "suggestion" in data
