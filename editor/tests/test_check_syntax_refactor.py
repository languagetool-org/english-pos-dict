import importlib.util
from conftest import SRC_DICT


def _load_checksyntax():
    spec = importlib.util.spec_from_file_location(
        "checksyntax", SRC_DICT / "check-syntax.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_check_line_returns_problems_list():
    cs = _load_checksyntax()
    assert cs.check_line("beautiful=JJ=all") == []
    problems = cs.check_line("beautiful=ZZ=all")
    assert any("unknown tag" in p for p in problems)


def test_importing_does_not_read_files():
    # loading the module must not raise even though it previously read files at import
    _load_checksyntax()
