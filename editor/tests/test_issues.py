from editor.dictmodel import parse_line
from editor.issues import scan_entry, scan_entries


def _entry(text):
    return parse_line(text + "\n", "mini.txt", 1)


def test_uncountable_with_plural_flags_NNU():
    issues = scan_entry(_entry("advice=advice/NN:U,advices/NNS=all"))
    assert any(i.rule == "uncountable-with-plural" for i in issues)


def test_NNUN_with_plural_is_ok():
    issues = scan_entry(_entry("bind=noun_UN=all"))
    assert all(i.rule != "uncountable-with-plural" for i in issues)


def test_plain_uncountable_shorthand_is_ok():
    # noun_U now expands to NN:U only (no NNS) -> not flagged
    issues = scan_entry(_entry("bidding=noun_U=all"))
    assert all(i.rule != "uncountable-with-plural" for i in issues)


def test_orphan_plural_flagged():
    issues = scan_entry(_entry("scissors=NNS=all"))
    assert any(i.rule == "orphan-plural" for i in issues)


def test_validation_failure_surfaces_as_issue():
    issues = scan_entry(_entry("beautiful=ZZ=all"))
    assert any(i.rule == "validation" for i in issues)


def test_suppressed_entry_not_scanned():
    issues = scan_entry(_entry("#advice=advice/NN:U,advices/NNS=all"))
    assert issues == []


def test_scan_entries_aggregates():
    entries = [
        _entry("beautiful=JJ=all"),
        _entry("advice=advice/NN:U,advices/NNS=all"),
        _entry("scissors=NNS=all"),
    ]
    issues = scan_entries(entries)
    rules = {i.rule for i in issues}
    assert "uncountable-with-plural" in rules
    assert "orphan-plural" in rules
