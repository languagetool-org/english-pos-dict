"""Golden guarantee: a no-op edit never perturbs the source file's bytes, and
expansion output is unchanged across a round trip."""

import shutil
from pathlib import Path

from editor.dictmodel import DictFile, load_entries
from editor.dictlogic import expand_line

FIX = Path(__file__).parent / "fixtures" / "mini.txt"


def test_noop_roundtrip_byte_identical(tmp_path):
    p = tmp_path / "mini.txt"
    shutil.copy(FIX, p)
    original = p.read_bytes()
    df = DictFile(p)
    for e in df.entries():
        df.replace_line(e.line_no, e.raw_line.rstrip("\n"))
    assert p.read_bytes() == original


def test_expansion_stable_across_roundtrip(tmp_path):
    p = tmp_path / "mini.txt"
    shutil.copy(FIX, p)

    def all_rows(path):
        rows = []
        for e in load_entries(path):
            if e.suppressed or not e.tags:
                continue
            rows.extend(expand_line(e.logical_line))
        return rows

    before = all_rows(p)
    df = DictFile(p)
    for e in df.entries():
        df.replace_line(e.line_no, e.raw_line.rstrip("\n"))
    after = all_rows(p)
    assert before == after
