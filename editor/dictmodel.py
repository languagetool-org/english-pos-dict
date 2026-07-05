"""In-memory model of a dictionary source file and byte-precise safe writes.

The text source files (src-clean.txt, src-pending.txt) remain authoritative.
Parsing preserves the exact bytes of every line so the file can be reproduced,
and edits rewrite only the touched line(s) to keep `git diff` minimal.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Entry:
    raw_line: str        # exact original text INCLUDING newline
    file: str            # basename, e.g. "src-clean.txt"
    line_no: int         # 1-based
    suppressed: bool     # logical entry disabled with a leading '#'
    lemma_field: str     # part before first '=' (leading '#' stripped)
    tags: str            # part between the two '='
    variants: str        # part after second '=' (comment stripped)
    comment: str         # trailing '# ...' including the '#', or ''

    @property
    def logical_line(self) -> str:
        """The active source line, without leading '#' or trailing comment."""
        return f"{self.lemma_field}={self.tags}={self.variants}"


def _split_comment(body: str):
    if "#" in body:
        idx = body.index("#")
        return body[:idx].rstrip(), body[idx:].strip()
    return body.rstrip(), ""


def parse_line(raw_line: str, file: str, line_no: int) -> Entry:
    text = raw_line.rstrip("\n")
    stripped = text.lstrip()
    # A suppressed entry is a '#'-prefixed line that still holds an entry ('=').
    suppressed = stripped.startswith("#") and "=" in stripped
    work = stripped
    if suppressed:
        work = work[1:].lstrip()  # drop the leading '#'
    body, comment = _split_comment(work)
    parts = body.split("=")
    lemma_field = parts[0].strip() if len(parts) > 0 else ""
    tags = parts[1].strip() if len(parts) > 1 else ""
    variants = parts[2].strip() if len(parts) > 2 else ""
    return Entry(raw_line, file, line_no, suppressed,
                 lemma_field, tags, variants, comment)


def load_entries(path) -> list[Entry]:
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    return [parse_line(line, path.name, i + 1)
            for i, line in enumerate(text.splitlines(keepends=True))]


class StaleFileError(Exception):
    """Raised when the file changed on disk since it was loaded."""


class DictFile:
    """Holds the lines of one source file and writes edits atomically."""

    def __init__(self, path):
        self.path = Path(path)
        self._lines = self.path.read_text(
            encoding="utf-8").splitlines(keepends=True)
        self._loaded_hash = self._hash_on_disk()

    def _hash_on_disk(self) -> str:
        return hashlib.sha256(self.path.read_bytes()).hexdigest()

    def entries(self) -> list[Entry]:
        return [parse_line(line, self.path.name, i + 1)
                for i, line in enumerate(self._lines)]

    def replace_line(self, line_no: int, new_text: str):
        if self._hash_on_disk() != self._loaded_hash:
            raise StaleFileError(f"{self.path} changed on disk since load")
        old = self._lines[line_no - 1]
        nl = "\n" if old.endswith("\n") else ""
        self._lines[line_no - 1] = new_text.rstrip("\n") + nl
        self._atomic_write()

    def _atomic_write(self):
        data = "".join(self._lines)
        fd, tmp = tempfile.mkstemp(dir=str(self.path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
                f.write(data)
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
        self._loaded_hash = self._hash_on_disk()
