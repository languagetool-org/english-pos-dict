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


def test_dual_tag_entry_not_flagged_as_disagreement(tmp_path):
    # theory=noun_UN is a correct dual entry; a one-sided 'countable'
    # suggestion must NOT be reported as disagreement (NN:UN expands).
    src = tmp_path / "s.txt"
    src.write_text("theory=noun_UN=all\n", encoding="utf-8")
    app = create_app({
        "TESTING": True,
        "SOURCE_FILES": [str(src)],
        "DB_PATH": str(tmp_path / "c.db"),
        "CORPUS_URL": "", "BCQL_URL": "",
    })
    def fake_gather(lemma, providers, cache):
        return [CountabilityEvidence("becl", "countable", "high",
                                     {"found": True}).to_dict()]
    with patch("editor.app.gather", side_effect=fake_gather):
        data = app.test_client().get("/api/evidence/theory").get_json()
    assert data["suggestion"] == "countable"
    assert data["disagreement"] is False


def test_both_suggestion_compatible_with_dual_tag(tmp_path):
    # BECL 'both' -> NN:UN must not disagree with a dual-tagged entry either
    src = tmp_path / "s.txt"
    src.write_text("analysis=noun_UN=all\n", encoding="utf-8")
    app = create_app({
        "TESTING": True,
        "SOURCE_FILES": [str(src)],
        "DB_PATH": str(tmp_path / "c.db"),
        "CORPUS_URL": "", "BCQL_URL": "",
    })
    def fake_gather(lemma, providers, cache):
        return [CountabilityEvidence("becl", "both", "high",
                                     {"found": True}).to_dict()]
    with patch("editor.app.gather", side_effect=fake_gather):
        data = app.test_client().get("/api/evidence/analysis").get_json()
    assert data["suggestion_tag" if "suggestion_tag" in data else "suggestion"]
    assert data["disagreement"] is False


def test_settings_default_off(client):
    r = client.get("/api/settings")
    data = r.get_json()
    assert data["corpus_url"] == "http://localhost:9"
    assert data["enabled"] is True
    assert data["default"] == "http://localhost:9"


def test_settings_bcql_url_roundtrip(client):
    r = client.post("/api/settings", json={"bcql_url": "http://localhost:8080"})
    assert r.status_code == 200
    assert r.get_json()["bcql_url"] == "http://localhost:8080"
    r2 = client.get("/api/settings")
    data = r2.get_json()
    assert data["bcql_url"] == "http://localhost:8080"
    # corpus_url untouched by a bcql-only save
    assert data["corpus_url"] == "http://localhost:9"
    # clearing bcql only
    r3 = client.post("/api/settings", json={"bcql_url": ""})
    assert r3.get_json()["bcql_url"] == ""


def test_settings_default_empty(tmp_path):
    src = tmp_path / "mini.txt"
    shutil.copy(FIX, src)
    app = create_app({
        "TESTING": True,
        "SOURCE_FILES": [str(src)],
        "DB_PATH": str(tmp_path / "c.db"),
    })
    r = app.test_client().get("/api/settings")
    data = r.get_json()
    assert data["enabled"] is False
    assert data["corpus_url"] == ""


def test_settings_save_and_persist(client):
    r = client.post("/api/settings", json={"corpus_url": "http://localhost:9999"})
    assert r.status_code == 200
    data = r.get_json()
    assert data["enabled"] is True
    assert data["corpus_url"] == "http://localhost:9999"
    r2 = client.get("/api/settings")
    assert r2.get_json()["corpus_url"] == "http://localhost:9999"


def test_settings_clear(client):
    client.post("/api/settings", json={"corpus_url": "http://localhost:9999"})
    r = client.post("/api/settings", json={"corpus_url": ""})
    assert r.get_json()["enabled"] is False


def test_corpus_url_setting_persists(client):
    r = client.post("/api/settings", json={"corpus_url": "http://c.example:9999"})
    assert r.status_code == 200
    body = r.get_json()
    assert body["corpus_url"] == "http://c.example:9999"
    assert body["enabled"] is True

    r = client.get("/api/settings")
    body = r.get_json()
    assert body["corpus_url"] == "http://c.example:9999"
    assert body["enabled"] is True

    r = client.post("/api/settings", json={"corpus_url": ""})
    assert r.get_json()["enabled"] is False
    r = client.get("/api/settings")
    assert r.get_json()["corpus_url"] == ""


def test_corpus_url_default_off_when_unset():
    src = Path("editor/tests/fixtures/mini.txt").resolve()
    app = create_app({
        "TESTING": True,
        "SOURCE_FILES": [str(src)],
        "DB_PATH": str(Path("/tmp/cdb_test_default.db")),
        "CORPUS_URL": "",   # default: no env var -> off
    })
    body = app.test_client().get("/api/settings").get_json()
    assert body["enabled"] is False
    assert body["corpus_url"] == ""


def test_corpus_status_off_shows_unknown(client):
    # no URL set -> provider returns unknown/not-available
    r = client.get("/api/evidence/bicycle")
    assert r.status_code == 200
    corpus = [v for v in r.get_json()["verdicts"] if v["source"] == "corpus"]
    assert corpus, "expected corpus evidence in verdicts"
    assert corpus[0]["detail"]["available"] is False


def test_move_entry_between_files(tmp_path):
    src = tmp_path / "a.txt"
    src.write_text("beautiful=JJ=all\nbicycle=noun=all\nbidding=noun_U=all\n",
                   encoding="utf-8")
    dst = tmp_path / "b.txt"
    dst.write_text("", encoding="utf-8")
    app = create_app({
        "TESTING": True,
        "SOURCE_FILES": [str(src), str(dst)],
        "DB_PATH": str(tmp_path / "c.db"),
    })
    c = app.test_client()
    # move line 2 (bicycle) from a.txt to b.txt
    r = c.post("/api/move", json={"file": "a.txt", "line_no": 2, "dest": "b.txt"})
    assert r.status_code == 200
    body = r.get_json()
    assert body["ok"] is True
    assert body["from"] == "a.txt" and body["to"] == "b.txt"
    # source no longer has bicycle, destination does
    assert "bicycle" not in src.read_text()
    assert "bicycle=noun=all" in dst.read_text()


def test_move_entry_keeps_suppress_and_comment(tmp_path):
    src = tmp_path / "a.txt"
    src.write_text("#advertizable=JJ=all # unusual\n", encoding="utf-8")
    dst = tmp_path / "b.txt"
    dst.write_text("", encoding="utf-8")
    app = create_app({
        "TESTING": True,
        "SOURCE_FILES": [str(src), str(dst)],
        "DB_PATH": str(tmp_path / "c.db"),
    })
    c = app.test_client()
    r = c.post("/api/move", json={"file": "a.txt", "line_no": 1, "dest": "b.txt"})
    assert r.status_code == 200
    content = dst.read_text()
    assert content.startswith("#advertizable=JJ=all # unusual")


def test_move_entry_rejects_same_file(tmp_path):
    src = tmp_path / "a.txt"
    src.write_text("beautiful=JJ=all\n", encoding="utf-8")
    app = create_app({
        "TESTING": True,
        "SOURCE_FILES": [str(src)],
        "DB_PATH": str(tmp_path / "c.db"),
    })
    c = app.test_client()
    r = c.post("/api/move", json={"file": "a.txt", "line_no": 1, "dest": "a.txt"})
    assert r.status_code == 400


def test_move_entry_rejects_invalid_line(tmp_path):
    src = tmp_path / "a.txt"
    src.write_text("beautiful=ZZ=all\n", encoding="utf-8")
    dst = tmp_path / "b.txt"
    dst.write_text("", encoding="utf-8")
    app = create_app({
        "TESTING": True,
        "SOURCE_FILES": [str(src), str(dst)],
        "DB_PATH": str(tmp_path / "c.db"),
    })
    c = app.test_client()
    r = c.post("/api/move", json={"file": "a.txt", "line_no": 1, "dest": "b.txt"})
    assert r.status_code == 400


def test_api_stats(client):
    r = client.get("/api/stats")
    assert r.status_code == 200
    data = r.get_json()
    assert "mini.txt" in data
    assert "total" in data["mini.txt"]
    assert "active" in data["mini.txt"]


def test_api_validate_all(client):
    r = client.post("/api/validate-all")
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    assert isinstance(data["count"], int)
    assert isinstance(data["results"], list)


def test_api_git_status(client):
    r = client.get("/api/git/status")
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    assert isinstance(data["files"], list)


def test_files_page(client):
    r = client.get("/files")
    assert r.status_code == 200
    assert b"mini.txt" in r.data


def test_file_view_page(client):
    r = client.get("/files/mini.txt")
    assert r.status_code == 200
    assert b"mini.txt" in r.data


def test_entry_navigation(client):
    r = client.get("/entry/mini.txt/1")
    assert r.status_code == 200
    assert b"Prev" not in r.data  # first entry, no prev
    assert b"Next" in r.data
    r2 = client.get("/entry/mini.txt/2")
    assert r2.status_code == 200
    assert b"Prev" in r2.data


def test_home_redirects(client):
    r = client.get("/")
    assert r.status_code == 302
    assert "/search" in r.headers["Location"]
