"""English Speller Database (ESDB) integration.

ESDB (github.com/en-wl/wordlist, ``scowl.db``) is the modern rework of SCOWL:
a SQLite database of English words with POS and inflection info. We use it for
one targeted signal: *plurale tantum* nouns.

A *plurale tantum* noun (scissors, trousers, gallows, pyrotechnics) is plural
in form and lexically plural-only: its plural-looking surface is its own lemma
(``n0``) in ESDB, and the naive singular (scissor, trouser, gallow,
pyrotechnic) is not recorded as a noun headword at all.

The dictionary occasionally lists such naive singulars as common nouns (e.g.
``gallow=noun``). ESDB lets us flag those as incorrect singulars.
"""

import sqlite3
from pathlib import Path

_DEFAULT_DB = Path(__file__).resolve().parent / "scowl.db"

# POS that make a headword noun-capable. ESDB uses:
#   n0 = noun (headword), ns = noun plural, nss = noun plural of plural,
#   m0 = noun/verb (headword), ms = noun/verb plural
_NOUN_POS = ("n0", "ns", "nss", "m0", "ms")


class EsdbError(Exception):
    pass


class Esdb:
    """Read-only ESDB queries. Loads plural-only and noun-capable headwords
    into memory so lookups are O(1).

    The ``words`` table has an index on ``word`` (case-sensitive) but not on
    ``lower(word)``, so per-query ``lower(word)=?`` would full-scan. We instead
    scan once at init into python sets; all lookups are then O(1).
    """

    def __init__(self, db_path=_DEFAULT_DB):
        db_path = Path(db_path) if db_path else _DEFAULT_DB
        if not db_path.exists():
            raise EsdbError(f"ESDB database not found: {db_path}")
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        except sqlite3.Error as exc:
            raise EsdbError(f"cannot open ESDB database: {exc}") from exc
        try:
            # noun-capable headwords (singular lemmas, incl. noun/verb m0)
            self._noun_headwords = {
                _lower(r[0]) for r in conn.execute(
                    "SELECT word FROM words WHERE lemma_id=word_id "
                    "AND pos IN %s" % _in(_NOUN_POS))
            }
            # headwords that are their OWN singular noun (n0) — includes
            # plural-only lemmas like 'gallows', 'scissors', 'corps'
            self._singular_noun = {
                _lower(r[0]) for r in conn.execute(
                    "SELECT word FROM words WHERE lemma_id=word_id "
                    "AND pos='n0'")
            }
            # plural surfaces (inflected rows). NOTE: ESDB lists these
            # mechanically for every noun, including mass nouns ('advices',
            # 'furnitures'), so membership is spelling attestation only —
            # never countability evidence.
            self._plurals = {
                _lower(r[0]) for r in conn.execute(
                    "SELECT word FROM words WHERE pos IN ('ns','ms','nss')")
            }
        finally:
            conn.close()
        self._noun_headwords.discard("")
        self._singular_noun.discard("")
        self._plurals.discard("")

    # -- public -------------------------------------------------------------
    def is_noun_headword(self, word):
        return _lower(word) in self._noun_headwords

    def is_plural_only_lemma(self, word):
        return _lower(word) in self._singular_noun

    @staticmethod
    def plural_surface(lemma):
        l = lemma.lower()
        if l.endswith(("s", "x", "z", "ch", "sh")):
            return l + "es"
        if l.endswith("y") and len(l) > 1 and l[-2] not in "aeiou":
            return l[:-1] + "ies"
        return l + "s"

    def singular_is_incorrect(self, singular):
        """True if *singular* is a likely INCORRECT singular of a plurale
        tantum noun.

        Condition: the naive plural surface of *singular* is an ESDB plural-
        only lemma (e.g. 'gallows'), while *singular* itself is NOT a noun
        headword ('gallow').
        """
        s = singular.lower()
        plur = self.plural_surface(s)
        return self.is_plural_only_lemma(plur) and not self.is_noun_headword(s)

    def attested_plural(self, lemma):
        """Return *lemma*'s plural surface if ESDB records one, else None.

        Spelling attestation only: ESDB lists regular plurals mechanically,
        even for mass nouns ('advices', 'furnitures'), so this must not be
        read as countability evidence.
        """
        l = _lower(lemma)
        candidates = [l + "s", l + "es"]
        if l.endswith("y") and len(l) > 1 and l[-2] not in "aeiou":
            candidates.append(l[:-1] + "ies")
        for cand in candidates:
            if cand in self._plurals:
                return cand
        return None


def _in(pos_tuple):
    return "(" + ",".join("'%s'" % p for p in pos_tuple) + ")"


def _lower(x):
    return x.lower() if isinstance(x, str) else x
