# Dictionary Editor Web App Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** A single-user local Flask app to search/edit the English PoS dictionary source, flag inconsistencies (headline: uncountable `NN:U` nouns that carry an `NNS` plural), and show advisory countability evidence from BECL, the local ConceptSketch corpus (BCQL), and Wiktionary.

**Architecture:** Flask, server-rendered Jinja pages + small vanilla JS. The app imports the existing `src-dict/inflection.py` and `src-dict/check-syntax.py` as the single source of truth for expansion and validation (no re-implementation). The text source files stay authoritative; a git-ignored SQLite DB caches only derived data (issues snapshot, evidence lookups).

**Tech Stack:** Python 3.10, Flask 2.3, pytest 7.4, requests 2.31, stdlib `sqlite3`, `importlib` (to load the hyphen-named `check-syntax.py`).

**Design doc:** `docs/plans/2026-07-05-dict-editor-webapp-design.md`

---

## Conventions

- All new code lives under `editor/`. Tests under `editor/tests/`.
- Run tests from repo root: `cd /mnt/d/git/english-pos-dict && python3 -m pytest editor/tests -v`.
- Commit after every green step. Use `feat:`/`test:`/`refactor:` prefixes.
- Repo root is `/mnt/d/git/english-pos-dict`. `SRC_DICT = <root>/src-dict`.
- The `inflection` module and refactored `check-syntax` are reached by putting
  `src-dict` on `sys.path` and loading `check-syntax.py` via `importlib`.

---

## Phase 0 — Scaffolding & source-of-truth refactor

### Task 0.1: Package skeleton

**Files:**
- Create: `editor/__init__.py` (empty)
- Create: `editor/tests/__init__.py` (empty)
- Create: `editor/tests/conftest.py`
- Create: `editor/requirements.txt`
- Modify: `.gitignore`

**Step 1:** Create `editor/requirements.txt`:
```
flask>=2.3
requests>=2.31
pytest>=7.4
```

**Step 2:** Add to `.gitignore`:
```
editor/.editor-cache.db
editor/__pycache__/
editor/**/__pycache__/
```

**Step 3:** Create `editor/tests/conftest.py` that exposes repo paths and puts
`src-dict` on the path:
```python
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC_DICT = ROOT / "src-dict"
sys.path.insert(0, str(SRC_DICT))  # so `import inflection` works
```

**Step 4:** Commit.
```bash
git add editor/ .gitignore
git commit -m "chore: scaffold editor package"
```

### Task 0.2: Make `check-syntax.py` importable (behaviour-preserving)

**Why:** `check_line()` currently `print()`s errors and the module runs a file
loop at import time. We need it to (a) return structured problems and (b) not run
on import.

**Files:**
- Modify: `src-dict/check-syntax.py`
- Test: `editor/tests/test_check_syntax_refactor.py`

**Step 1: Write the failing test.**
```python
import importlib.util
from pathlib import Path
from conftest import SRC_DICT

def _load_checksyntax():
    spec = importlib.util.spec_from_file_location(
        "checksyntax", SRC_DICT / "check-syntax.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def test_check_line_returns_problems_list():
    cs = _load_checksyntax()
    # a clean line -> no problems
    assert cs.check_line("beautiful=JJ=all") == []
    # unknown tag -> one problem mentioning the tag
    problems = cs.check_line("beautiful=ZZ=all")
    assert any("unknown tag" in p for p in problems)

def test_importing_does_not_read_files():
    # loading the module must not raise even if cwd has no src files
    _load_checksyntax()  # would previously try to open ./src-dict/... at import
```

**Step 2: Run — expect FAIL** (module runs file loop on import / returns None).
Run: `python3 -m pytest editor/tests/test_check_syntax_refactor.py -v`

**Step 3: Refactor `check-syntax.py`.**
- Change every `print(msg)` inside `check_line` to append to a local
  `problems = []` list and `return problems` at the end. Keep the exact message
  strings (tests and humans rely on them).
- Replace the `exit(2)` early-exit with appending the message and `return problems`.
- Move the bottom file-reading loop into:
  ```python
  def _main():
      for file_path in ["./src-dict/src-clean.txt", "./src-dict/src-pending.txt"]:
          with open(file_path, "r", encoding="utf-8") as file:
              for line in file.readlines():
                  for p in check_line(line):
                      print(p)

  if __name__ == "__main__":
      _main()
  ```
  This preserves CLI output (still printed) while making import side-effect-free.
- `parseVerbalForms` currently `print`s from inside `inflection`; leave those —
  they are deeper and out of scope. `check_line` only needs to collect its own
  messages.

**Step 4: Run — expect PASS.**

**Step 5: Verify the CLI still works** (regression guard):
Run: `cd /mnt/d/git/english-pos-dict && python3 src-dict/check-syntax.py | head`
Expected: same style of output as before (error lines printed), no traceback.

**Step 6: Commit.**
```bash
git add src-dict/check-syntax.py editor/tests/test_check_syntax_refactor.py
git commit -m "refactor: make check_line return problems and importable"
```

---

## Phase 1 — Dictionary model (parse + byte-precise safe write)

### Task 1.1: Parse a source file into Entry objects

**Files:**
- Create: `editor/dictmodel.py`
- Test: `editor/tests/test_dictmodel_parse.py`
- Create fixture: `editor/tests/fixtures/mini.txt`

**Fixture `editor/tests/fixtures/mini.txt`** (exact bytes, trailing newline):
```
beautiful=JJ=all
bicycle=noun=all
bidding=noun_U=all
#advertizable=JJ=all # unusual
bind=noun_UN=all
```

**Step 1: Write failing test.**
```python
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
    assert sup.lemma_field == "advertizable"   # '#' stripped for display
    assert sup.comment == "# unusual"

def test_raw_line_roundtrip_preserved():
    entries = load_entries(FIX)
    # concatenating raw_line of every entry reproduces the file exactly
    assert "".join(e.raw_line for e in entries) == FIX.read_text(encoding="utf-8")
```

**Step 2: Run — expect FAIL.**

**Step 3: Implement `editor/dictmodel.py`.**
```python
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

@dataclass
class Entry:
    raw_line: str        # exact original text INCLUDING newline
    file: str            # basename, e.g. "src-clean.txt"
    line_no: int         # 1-based
    suppressed: bool     # line begins with '#'
    lemma_field: str     # part before first '=' (leading '#' stripped)
    tags: str            # part between the two '='
    variants: str        # part after second '=' (comment stripped)
    comment: str         # trailing '# ...' including the '#', or ''

def _split_comment(body: str):
    # comment is '#' that is NOT the leading suppression marker
    if "#" in body:
        idx = body.index("#")
        return body[:idx].rstrip(), body[idx:].strip()
    return body.rstrip(), ""

def parse_line(raw_line: str, file: str, line_no: int) -> Entry:
    text = raw_line.rstrip("\n")
    suppressed = text.lstrip().startswith("#") and "=" in text
    work = text.lstrip()
    if suppressed:
        work = work[1:].lstrip()  # drop leading '#'
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
    # keepends so raw_line concatenation reproduces the file byte-for-byte
    return [parse_line(line, path.name, i + 1)
            for i, line in enumerate(text.splitlines(keepends=True))]
```
> Note: a comment-only line (`# ...` with no `=`) is treated as a non-entry
> (`suppressed=False`, empty fields) — that is fine; the issue engine ignores
> entries with empty `tags`.

**Step 4: Run — expect PASS.**

**Step 5: Commit.**
```bash
git add editor/dictmodel.py editor/tests/test_dictmodel_parse.py editor/tests/fixtures/mini.txt
git commit -m "feat: parse dictionary source into Entry objects"
```

### Task 1.2: Atomic, guarded, line-precise save

**Files:**
- Modify: `editor/dictmodel.py`
- Test: `editor/tests/test_dictmodel_save.py`

**Step 1: Write failing tests.**
```python
import shutil, hashlib
from pathlib import Path
from editor.dictmodel import DictFile

def _copy_fixture(tmp_path):
    src = Path(__file__).parent / "fixtures" / "mini.txt"
    dst = tmp_path / "mini.txt"
    shutil.copy(src, dst)
    return dst

def test_replace_line_is_byte_precise(tmp_path):
    p = _copy_fixture(tmp_path)
    df = DictFile(p)
    df.replace_line(2, "bicycle=noun=gb")   # only line 2 changes
    after = p.read_text(encoding="utf-8").splitlines()
    assert after[1] == "bicycle=noun=gb"
    assert after[0] == "beautiful=JJ=all"   # neighbours untouched
    assert after[4] == "bind=noun_UN=all"

def test_save_rejects_stale_write(tmp_path):
    p = _copy_fixture(tmp_path)
    df = DictFile(p)
    # simulate external edit after load
    p.write_text(p.read_text(encoding="utf-8") + "extra=JJ=all\n", encoding="utf-8")
    import pytest
    with pytest.raises(StaleFileError):
        df.replace_line(2, "bicycle=noun=gb")

def test_trailing_newline_preserved(tmp_path):
    p = _copy_fixture(tmp_path)
    df = DictFile(p)
    df.replace_line(1, "beautiful=JJ=gb")
    assert p.read_text(encoding="utf-8").endswith("\n")
```

**Step 2: Run — expect FAIL.**

**Step 3: Implement `DictFile` in `editor/dictmodel.py`.**
```python
import hashlib, os, tempfile

class StaleFileError(Exception):
    pass

class DictFile:
    def __init__(self, path):
        self.path = Path(path)
        self._lines = self.path.read_text(encoding="utf-8").splitlines(keepends=True)
        self._loaded_hash = self._hash_on_disk()

    def _hash_on_disk(self):
        return hashlib.sha256(self.path.read_bytes()).hexdigest()

    def entries(self):
        from editor.dictmodel import parse_line
        return [parse_line(l, self.path.name, i + 1)
                for i, l in enumerate(self._lines)]

    def replace_line(self, line_no: int, new_text: str):
        if self._hash_on_disk() != self._loaded_hash:
            raise StaleFileError(f"{self.path} changed on disk since load")
        # preserve the existing line's newline style
        old = self._lines[line_no - 1]
        nl = "\n" if old.endswith("\n") else ""
        self._lines[line_no - 1] = new_text.rstrip("\n") + nl
        self._atomic_write()

    def _atomic_write(self):
        data = "".join(self._lines)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
                f.write(data)
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
        self._loaded_hash = self._hash_on_disk()
```

**Step 4: Run — expect PASS.**

**Step 5: Commit.**
```bash
git add editor/dictmodel.py editor/tests/test_dictmodel_save.py
git commit -m "feat: atomic guarded line-precise save (DictFile)"
```

---

## Phase 2 — Validation & expansion wrapper

### Task 2.1: Thin wrapper around inflection + check-syntax

**Files:**
- Create: `editor/dictlogic.py`
- Test: `editor/tests/test_dictlogic.py`

**Step 1: Write failing tests.**
```python
from editor.dictlogic import expand_line, validate_line

def test_expand_noun_shorthand():
    rows = expand_line("bicycle=noun=all")
    # form, lemma, tag, variants tuples
    assert ("bicycle", "bicycle", "NN", "all") in rows
    assert ("bicycles", "bicycle", "NNS", "all") in rows

def test_expand_uncountable_still_generates_plural():
    # documents the legacy behaviour the issue engine will catch
    rows = expand_line("bidding=noun_U=all")
    tags = {t for _, _, t, _ in rows}
    assert "NN:U" in tags

def test_validate_clean_line():
    assert validate_line("beautiful=JJ=all") == []

def test_validate_unknown_tag():
    problems = validate_line("beautiful=ZZ=all")
    assert any("unknown tag" in p for p in problems)
```

**Step 2: Run — expect FAIL.**

**Step 3: Implement `editor/dictlogic.py`.**
```python
import importlib.util, sys
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
```

**Step 4: Run — expect PASS.**

**Step 5: Golden round-trip test** — add to same file:
```python
def test_expansion_matches_inflection_directly():
    import inflection
    line = "bind=noun_UN=all"
    direct = [r for r in inflection.getFormsFromLine(line) if r]
    wrapped = ["\t".join(t) for t in expand_line(line)]
    assert wrapped == direct
```
Run and expect PASS.

**Step 6: Commit.**
```bash
git add editor/dictlogic.py editor/tests/test_dictlogic.py
git commit -m "feat: expansion + validation wrapper over inflection/check-syntax"
```

---

## Phase 3 — Issue engine

### Task 3.1: Rule framework + uncountable-with-plural rule

**Files:**
- Create: `editor/issues.py`
- Test: `editor/tests/test_issues.py`

**Step 1: Write failing tests.**
```python
from editor.dictmodel import parse_line
from editor.issues import scan_entry, Issue

def _entry(text):
    return parse_line(text + "\n", "mini.txt", 1)

def test_uncountable_with_plural_flags_NNU():
    issues = scan_entry(_entry("advice=advice/NN:U,advices/NNS=all"))
    assert any(i.rule == "uncountable-with-plural" for i in issues)

def test_NNUN_with_plural_is_ok():
    issues = scan_entry(_entry("bind=noun_UN=all"))
    assert all(i.rule != "uncountable-with-plural" for i in issues)

def test_orphan_plural_flagged():
    issues = scan_entry(_entry("scissors=NNS=all"))
    assert any(i.rule == "orphan-plural" for i in issues)

def test_validation_failure_surfaces_as_issue():
    issues = scan_entry(_entry("beautiful=ZZ=all"))
    assert any(i.rule == "validation" for i in issues)
```

**Step 2: Run — expect FAIL.**

**Step 3: Implement `editor/issues.py`.**
```python
from dataclasses import dataclass
from editor.dictlogic import expand_line, validate_line

@dataclass
class Issue:
    rule: str
    severity: str        # "error" | "warning"
    message: str
    lemma: str
    file: str
    line_no: int

def _tags(entry):
    try:
        rows = expand_line(_reconstruct(entry))
    except Exception:
        return set(), []
    return {t for _, _, t, _ in rows}, rows

def _reconstruct(entry):
    # rebuild the logical source line (no leading '#', no comment)
    return f"{entry.lemma_field}={entry.tags}={entry.variants}"

def rule_uncountable_with_plural(entry, tags, rows):
    if "NN:U" in tags and "NNS" in tags:
        return Issue("uncountable-with-plural", "warning",
                     "NN:U noun also has an NNS plural form",
                     entry.lemma_field, entry.file, entry.line_no)

def rule_orphan_plural(entry, tags, rows):
    if "NNS" in tags and not any(t.startswith("NN") and t != "NNS"
                                 and not t.startswith("NNP") for t in tags):
        return Issue("orphan-plural", "warning",
                     "NNS plural with no singular NN form",
                     entry.lemma_field, entry.file, entry.line_no)

RULES = [rule_uncountable_with_plural, rule_orphan_plural]

def scan_entry(entry):
    if entry.suppressed or not entry.tags:
        return []
    issues = []
    line = _reconstruct(entry)
    for p in validate_line(line):
        issues.append(Issue("validation", "error", p,
                             entry.lemma_field, entry.file, entry.line_no))
    tags, rows = _tags(entry)
    for rule in RULES:
        issue = rule(entry, tags, rows)
        if issue:
            issues.append(issue)
    return issues
```
> Note: `_tags` expands the line so shorthands like `noun_U` (which generate
> `NNS`) are caught by `rule_uncountable_with_plural` too — matching the design's
> "shorthand check".

**Step 4: Run — expect PASS.**

**Step 5:** Add `scan_entries(entries)` returning all issues, plus a test that a
mixed fixture yields the expected counts. Commit.
```bash
git add editor/issues.py editor/tests/test_issues.py
git commit -m "feat: issue rule engine with uncountable-with-plural rule"
```

---

## Phase 4 — SQLite cache

### Task 4.1: Cache layer for evidence + issue snapshot

**Files:**
- Create: `editor/cache.py`
- Test: `editor/tests/test_cache.py`

**Step 1: Write failing tests.**
```python
from editor.cache import Cache

def test_evidence_roundtrip(tmp_path):
    c = Cache(tmp_path / "c.db")
    c.put_evidence("advice", "becl", {"verdict": "uncountable", "confidence": "high"})
    got = c.get_evidence("advice", "becl")
    assert got["verdict"] == "uncountable"

def test_missing_returns_none(tmp_path):
    c = Cache(tmp_path / "c.db")
    assert c.get_evidence("nope", "becl") is None

def test_ttl_expiry(tmp_path):
    c = Cache(tmp_path / "c.db")
    c.put_evidence("x", "corpus", {"v": 1}, ttl_seconds=0)
    assert c.get_evidence("x", "corpus") is None  # already expired
```

**Step 2: Run — expect FAIL.**

**Step 3: Implement `editor/cache.py`** using stdlib `sqlite3`, one table
`evidence(lemma TEXT, source TEXT, json TEXT, fetched_at REAL, ttl REAL, PRIMARY
KEY(lemma, source))`; store JSON via `json.dumps`; `get_evidence` returns `None`
when the row is missing or `time.time() > fetched_at + ttl` (ttl `None`/0 rules).
Add `put_issues_snapshot(list)` / `get_issues_snapshot()` storing a single JSON blob.

**Step 4: Run — expect PASS. Commit.**
```bash
git add editor/cache.py editor/tests/test_cache.py
git commit -m "feat: sqlite cache for evidence and issue snapshot"
```

---

## Phase 5 — Evidence providers

### Task 5.1: Provider interface + corpus (BCQL) provider

**Files:**
- Create: `editor/providers/__init__.py`
- Create: `editor/providers/base.py`
- Create: `editor/providers/corpus.py`
- Test: `editor/tests/test_provider_corpus.py`

**Step 1: Write failing test (mock HTTP).**
```python
from unittest.mock import patch
from editor.providers.corpus import CorpusProvider

def _fake_post(url, json, timeout):
    class R:
        status_code = 200
        def raise_for_status(self): pass
        def json(self):
            q = json["query"]
            total = 120 if 'NNS' in q else 1000  # plural vs all-noun
            return {"status": "ok", "query": q, "total": total,
                    "offset": 0, "pageSize": 0, "results": []}
    return R()

def test_corpus_plural_rate():
    with patch("editor.providers.corpus.requests.post", side_effect=_fake_post):
        ev = CorpusProvider("http://localhost:8080").lookup("advice")
    assert ev.detail["plural_rate"] == 120 / 1000
    assert ev.verdict in {"countable", "both", "uncountable", "unknown"}
    assert ev.source == "corpus"
```

**Step 2: Run — expect FAIL.**

**Step 3: Implement `base.py`.**
```python
from dataclasses import dataclass, field

@dataclass
class CountabilityEvidence:
    source: str                 # "becl" | "corpus" | "wiktionary"
    verdict: str                # countable|uncountable|both|unknown
    confidence: str             # high|medium|low
    detail: dict = field(default_factory=dict)
    source_url: str = ""

class EvidenceProvider:
    name = "base"
    def lookup(self, lemma: str) -> CountabilityEvidence:
        raise NotImplementedError
```

**Step 3b: Implement `corpus.py`.**
```python
import requests
from editor.providers.base import EvidenceProvider, CountabilityEvidence

class CorpusProvider(EvidenceProvider):
    name = "corpus"
    def __init__(self, base_url="http://localhost:8080", timeout=10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _count(self, query):
        r = requests.post(f"{self.base_url}/api/bcql",
                          json={"query": query, "top": 0, "offset": 0},
                          timeout=self.timeout)
        r.raise_for_status()
        return r.json().get("total", 0)

    def lookup(self, lemma):
        esc = lemma.replace('"', '')
        plural = self._count(f'[lemma="{esc}" & xpos="NNS"]')
        allnoun = self._count(f'[lemma="{esc}" & xpos="NN.*"]')
        rate = (plural / allnoun) if allnoun else 0.0
        if allnoun == 0:
            verdict, conf = "unknown", "low"
        elif rate >= 0.05:
            verdict, conf = "countable", "medium"
        else:
            verdict, conf = "uncountable", "low"  # silence != proof
        return CountabilityEvidence(
            "corpus", verdict, conf,
            {"plural_rate": rate, "plural_hits": plural, "noun_hits": allnoun})
```
> Thresholds (0.05) are a starting point; expose as constants for later tuning.

**Step 4: Run — expect PASS. Commit.**
```bash
git add editor/providers editor/tests/test_provider_corpus.py
git commit -m "feat: corpus BCQL evidence provider"
```

### Task 5.2: Wiktionary provider (live API, cached)

**Files:**
- Create: `editor/providers/wiktionary.py`
- Test: `editor/tests/test_provider_wiktionary.py`

**Step 1: Write failing test** with a recorded wikitext snippet containing
`{{en-noun|-}}` (the standard uncountable marker) and `{{lb|en|uncountable}}`;
assert verdict `uncountable`. Add a second fixture with `{{en-noun}}` → verdict
`countable`. Mock `requests.get`.

**Step 3: Implement** `WiktionaryProvider.lookup(lemma)`:
- GET `https://en.wiktionary.org/w/api.php` with
  `action=parse&page=<lemma>&prop=wikitext&format=json`.
- If the English noun section contains `{{en-noun|-}}` or `{{lb|en|...uncountable...}}`
  → `uncountable`; if it contains a plain `{{en-noun}}` or an explicit plural →
  `countable`; if both signals → `both`; else `unknown`. `confidence: low`.
- On HTTP error / missing page → `unknown` (never raise to caller).

**Step 4–5:** Run, commit.

### Task 5.3: BECL provider + ingestion

**Files:**
- Create: `editor/providers/becl.py`
- Create: `editor/ingest_becl.py` (CLI: `python -m editor.ingest_becl <path> --db ...`)
- Test: `editor/tests/test_provider_becl.py`
- Fixture: `editor/tests/fixtures/becl_sample.*` (2–3 rows once real format known)

**Note:** BECL is "available, not yet integrated" — its exact file format is TBD.
Implement against a **normalised interstitial table** so the provider does not
depend on the raw format:
- `ingest_becl.py` reads the raw BECL file and writes rows
  `becl(lemma TEXT PRIMARY KEY, becl_class TEXT, verdict TEXT)` into the cache DB,
  applying the class→tagset map: `countable→NN/countable`,
  `uncountable→NN:U/uncountable`, `both|plural|collective→NN:UN/both`. Keep
  `becl_class` raw for auditability.
- `BeclProvider.lookup(lemma)` reads that table → `CountabilityEvidence(source=
  "becl", confidence="high")`, or `verdict="unknown"` when absent.
- Test the provider against a hand-written `becl` table (insert rows directly),
  independent of the raw parser. Add a separate small test for `ingest_becl` once
  the real format is confirmed.

**Commit** after green.

### Task 5.4: Aggregator + adjudication

**Files:**
- Create: `editor/providers/aggregate.py`
- Test: `editor/tests/test_aggregate.py`

**Step 1: Write failing tests** for `adjudicate(evidences, current_tags)`:
```python
def test_disagreement_flag():
    # entry marked NN:U, BECL says countable, corpus shows plurals
    result = adjudicate([
        ev("becl","countable","high"),
        ev("corpus","countable","medium",{"plural_rate":0.2}),
    ], current_tags={"NN:U"})
    assert result["disagreement"] is True
    assert result["suggestion"] in {"NN", "NN:UN"}

def test_agreement_no_flag():
    result = adjudicate([ev("becl","uncountable","high")], current_tags={"NN:U"})
    assert result["disagreement"] is False
```

**Step 3: Implement** `adjudicate`:
- Combined suggestion = BECL verdict if present (weight high), else corpus if it
  found plurals (medium), else Wiktionary (low), else `unknown`.
- Map suggested verdict → tag: `countable→NN`, `uncountable→NN:U`, `both→NN:UN`.
- `disagreement = suggestion_tag not in current_tags` (only when suggestion is not
  `unknown`).
- Return `{verdicts: [...], suggestion, suggestion_tag, disagreement, confidence}`.
- Add `gather(lemma, providers, cache)` that pulls each provider (cache-first,
  writes results with per-source TTL) and returns the evidence list.

**Commit** after green.

---

## Phase 6 — Flask app & UI

### Task 6.1: App factory + config + search/editor routes

**Files:**
- Create: `editor/app.py`
- Create: `editor/config.py` (paths, corpus URL from env `CORPUS_URL`, db path)
- Create: `editor/templates/base.html`, `search.html`, `entry.html`
- Create: `editor/static/app.js`, `editor/static/style.css`
- Test: `editor/tests/test_app_routes.py`

**Step 1: Write failing tests** using Flask test client:
```python
from editor.app import create_app

def _client(tmp_path):
    app = create_app({"TESTING": True,
                      "SOURCE_FILES": [str(FIXTURE_COPY)],
                      "DB_PATH": str(tmp_path/"c.db")})
    return app.test_client()

def test_search_returns_matching_entry(tmp_path):
    c = _client(tmp_path)
    r = c.get("/search?q=bicycle")
    assert r.status_code == 200 and b"bicycle" in r.data

def test_validate_endpoint(tmp_path):
    c = _client(tmp_path)
    r = c.post("/api/validate", json={"line": "beautiful=ZZ=all"})
    data = r.get_json()
    assert any("unknown tag" in p for p in data["problems"])
    assert "expansion" in data

def test_save_rejects_invalid(tmp_path):
    c = _client(tmp_path)
    r = c.post("/api/save", json={"file": "mini.txt", "line_no": 1,
                                  "line": "beautiful=ZZ=all"})
    assert r.status_code == 400  # validation blocks the write
```

**Step 2: Run — expect FAIL.**

**Step 3: Implement `create_app(config)`** with routes:
- `GET /` → redirect to `/search`.
- `GET /search?q=` → search entries (lemma + expanded forms) via an index built
  at startup; render `search.html`.
- `GET /entry/<file>/<line_no>` → render `entry.html` editor.
- `POST /api/validate` `{line}` → `{problems: [...], expansion: [[form,lemma,tag,var]...]}`.
- `POST /api/save` `{file, line_no, line}` → validate first; if problems, HTTP 400
  with them; else `DictFile.replace_line(...)` and return 200. Handle
  `StaleFileError` → HTTP 409.
- Hold one `DictFile` per source file in app context; rebuild the search index
  after a successful save.

**Step 4: Run — expect PASS.**

**Step 5:** `app.js` wires the editor textbox to `/api/validate` (debounced) and
renders problems + expansion; save button posts to `/api/save`. `style.css`
minimal. Commit.
```bash
git add editor/app.py editor/config.py editor/templates editor/static editor/tests/test_app_routes.py
git commit -m "feat: Flask app with search/editor and validate/save endpoints"
```

### Task 6.2: Issue queue route

**Files:**
- Modify: `editor/app.py`
- Create: `editor/templates/issues.html`
- Test: extend `editor/tests/test_app_routes.py`

**Step 1: Failing test** — `GET /issues` returns 200 and lists the seeded
`uncountable-with-plural` case; `POST /api/rescan` rebuilds and caches the
snapshot.

**Step 3: Implement** `GET /issues` (read snapshot from cache or scan on first
run) rendering a table grouped by rule; each row links to
`/entry/<file>/<line_no>` and to `/entry/...?evidence=1`. `POST /api/rescan`
runs `scan_entries` over all `DictFile.entries()`, stores via
`cache.put_issues_snapshot`.

**Step 4–5:** Run, commit.

### Task 6.3: Evidence panel route + UI

**Files:**
- Modify: `editor/app.py`, `editor/templates/entry.html`
- Test: extend `editor/tests/test_app_routes.py` (mock providers)

**Step 1: Failing test** — `GET /api/evidence/<lemma>` returns JSON with the three
source verdicts and an `adjudication` block; provider calls are mocked/patched so
the test is offline. Assert a disagreement case sets `disagreement: true`.

**Step 3: Implement** `/api/evidence/<lemma>`:
- Build providers from config (BECL from DB, Corpus from `CORPUS_URL`,
  Wiktionary), call `aggregate.gather(...)` + `adjudicate(...)` using the current
  entry's tags. Return verdicts + adjudication + KWIC rows from corpus.
- `entry.html`: an "Evidence" button (or auto-load when `?evidence=1`) shows the
  three verdicts side by side, the combined suggestion, a disagreement banner, and
  a one-click "apply suggested tag" that fills the editor line (still saved through
  the validated `/api/save` path — never auto-applied silently).

**Step 4–5:** Run, commit.

### Task 6.4: Round-trip safety golden test + README

**Files:**
- Test: `editor/tests/test_roundtrip_golden.py`
- Create: `editor/README.md`

**Step 1: Golden test** — load a fixture, `replace_line` with the identical text
for every line, assert the file is byte-identical to the original (proves saves
don't perturb layout). Also assert building the tagger rows via `expand_line` over
the fixture is unchanged before/after a no-op round trip.

**Step 3:** `editor/README.md`: how to run
(`CORPUS_URL=http://localhost:8080 flask --app editor.app run`), env vars, how to
ingest BECL, and the "source files are authoritative; review `git diff` before
committing" note.

**Step 4–5:** Run full suite `python3 -m pytest editor/tests -v`, commit.

---

## Definition of done

- `python3 -m pytest editor/tests -v` all green.
- `python3 src-dict/check-syntax.py` still runs (CLI regression intact).
- `flask --app editor.app run` serves search, editor, issue queue, and evidence
  panel locally.
- A no-op edit through the UI produces an empty `git diff` on the source file.
- Evidence panel degrades gracefully when the corpus server is down (corpus
  verdict `unknown`, others still shown).
