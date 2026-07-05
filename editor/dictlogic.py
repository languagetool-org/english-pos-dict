"""Thin wrapper over the existing build logic (single source of truth).

Expansion uses inflection.getFormsFromLine (exactly what the build emits into
the tagger dictionary). Validation uses the refactored check_line. No dictionary
rules are re-implemented here.
"""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_DICT = ROOT / "src-dict"
if str(SRC_DICT) not in sys.path:
    sys.path.insert(0, str(SRC_DICT))

import inflection  # noqa: E402


def _load_checksyntax():
    spec = importlib.util.spec_from_file_location(
        "checksyntax", SRC_DICT / "check-syntax.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_checksyntax = _load_checksyntax()


def expand_line(line: str):
    """Return list of (form, lemma, tag, variants) as the build would emit."""
    rows = []
    for row in inflection.getFormsFromLine(line):
        if not row:
            continue
        form, lemma, tag, variants = row.split("\t")
        rows.append((form, lemma, tag, variants))
    return rows


def validate_line(line: str):
    """Return list of human-readable problem strings (empty == valid)."""
    return _checksyntax.check_line(line)
