import shutil
from pathlib import Path

import pytest

from editor.dictmodel import DictFile, StaleFileError

FIX = Path(__file__).parent / "fixtures" / "mini.txt"


def _copy_fixture(tmp_path):
    dst = tmp_path / "mini.txt"
    shutil.copy(FIX, dst)
    return dst


def test_replace_line_is_byte_precise(tmp_path):
    p = _copy_fixture(tmp_path)
    df = DictFile(p)
    df.replace_line(2, "bicycle=noun=gb")
    after = p.read_text(encoding="utf-8").splitlines()
    assert after[1] == "bicycle=noun=gb"
    assert after[0] == "beautiful=JJ=all"
    assert after[4] == "bind=noun_UN=all"


def test_save_rejects_stale_write(tmp_path):
    p = _copy_fixture(tmp_path)
    df = DictFile(p)
    p.write_text(p.read_text(encoding="utf-8") + "extra=JJ=all\n", encoding="utf-8")
    with pytest.raises(StaleFileError):
        df.replace_line(2, "bicycle=noun=gb")


def test_trailing_newline_preserved(tmp_path):
    p = _copy_fixture(tmp_path)
    df = DictFile(p)
    df.replace_line(1, "beautiful=JJ=gb")
    assert p.read_text(encoding="utf-8").endswith("\n")


def test_noop_replace_is_byte_identical(tmp_path):
    p = _copy_fixture(tmp_path)
    original = p.read_bytes()
    df = DictFile(p)
    for e in df.entries():
        df.replace_line(e.line_no, e.raw_line.rstrip("\n"))
    assert p.read_bytes() == original
