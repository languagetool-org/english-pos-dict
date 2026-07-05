from pathlib import Path
from editor.dictmodel import load_entries, Entry

FIX = Path(__file__).parent / "fixtures" / "mini.txt"


def test_load_entries_basic():
    entries = load_entries(FIX)
    assert len(entries) == 5
    e = entries[0]
    assert isinstance(e, Entry)
    assert e.lemma_field == "beautiful"
    assert e.tags == "JJ"
    assert e.variants == "all"
    assert e.line_no == 1
    assert e.suppressed is False


def test_suppressed_and_comment():
    entries = load_entries(FIX)
    sup = entries[3]  # #advertizable...
    assert sup.suppressed is True
    assert sup.lemma_field == "advertizable"
    assert sup.comment == "# unusual"


def test_raw_line_roundtrip_preserved():
    entries = load_entries(FIX)
    assert "".join(e.raw_line for e in entries) == FIX.read_text(encoding="utf-8")
