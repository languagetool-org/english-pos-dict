"""Tests for the ESDB integration (plurale tantum + attestation)."""

import sqlite3

import pytest

from editor.esdb import Esdb


@pytest.fixture
def esdb(tmp_path):
    """Minimal scowl-like DB mirroring the real schema and the
    aftershave/gallows cases."""
    p = tmp_path / "scowl.db"
    conn = sqlite3.connect(p)
    conn.executescript("""
        CREATE TABLE words (
            word_id INTEGER PRIMARY KEY, group_id INTEGER,
            lemma_id INTEGER, word TEXT, pos TEXT);
    """)
    rows = [
        # (word_id, group_id, lemma_id, word, pos)
        (1, 1, 1, "aftershave", "n0"),
        (2, 1, 1, "aftershaves", "ns"),
        (3, 2, 3, "advice", "n0"),
        (4, 2, 3, "advices", "ns"),      # mechanical plural of a mass noun
        (10, 5, 10, "gallows", "n0"),    # plural-only lemma: own headword
        (11, 5, 10, "galluses", "ns"),
        # 'gallow' deliberately absent — not a noun headword at all
        (20, 7, 20, "bicycle", "n0"),
        (21, 7, 20, "bicycles", "ms"),   # noun/verb plural
        (30, 8, 30, "theory", "n0"),
        (31, 8, 30, "theories", "ns"),   # y->ies
    ]
    conn.executemany("INSERT INTO words VALUES (?,?,?,?,?)", rows)
    conn.commit()
    conn.close()
    return Esdb(str(p))


def test_legitimate_singular_is_a_noun_headword(esdb):
    assert esdb.is_noun_headword("aftershave")
    assert not esdb.singular_is_incorrect("aftershave")


def test_attested_plural_found(esdb):
    assert esdb.attested_plural("aftershave") == "aftershaves"
    assert esdb.attested_plural("bicycle") == "bicycles"
    assert esdb.attested_plural("theory") == "theories"


def test_mechanical_plurals_of_mass_nouns_also_listed(esdb):
    # documents WHY attestation must not be read as countability evidence:
    # ESDB lists 'advices' just like 'aftershaves'
    assert esdb.attested_plural("advice") == "advices"


def test_incorrect_singular_detected(esdb):
    assert esdb.singular_is_incorrect("gallow")
    assert not esdb.is_noun_headword("gallow")


def test_plural_only_lemma_is_its_own_headword(esdb):
    assert esdb.is_noun_headword("gallows")
    assert esdb.is_plural_only_lemma("gallows")
