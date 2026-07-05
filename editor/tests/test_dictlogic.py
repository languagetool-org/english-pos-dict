from editor.dictlogic import expand_line, validate_line


def test_expand_noun_shorthand():
    rows = expand_line("bicycle=noun=all")
    assert ("bicycle", "bicycle", "NN", "all") in rows
    assert ("bicycles", "bicycle", "NNS", "all") in rows


def test_expand_uncountable_generates_tag():
    rows = expand_line("bidding=noun_U=all")
    tags = {t for _, _, t, _ in rows}
    assert "NN:U" in tags


def test_validate_clean_line():
    assert validate_line("beautiful=JJ=all") == []


def test_validate_unknown_tag():
    problems = validate_line("beautiful=ZZ=all")
    assert any("unknown tag" in p for p in problems)


def test_expansion_matches_inflection_directly():
    import inflection
    line = "bind=noun_UN=all"
    direct = [r for r in inflection.getFormsFromLine(line) if r]
    wrapped = ["\t".join(t) for t in expand_line(line)]
    assert wrapped == direct
