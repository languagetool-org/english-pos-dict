# Dictionary Editor Web App — Design

Date: 2026-07-05
Status: Approved design (brainstormed with maintainer)

## Purpose

A small, single-user local web app that makes maintaining the English PoS
dictionary source (`src-dict/src-clean.txt` and `src-dict/src-pending.txt`)
easier than editing the raw text file:

1. **Search + structured editor** for individual entries, with live validation
   and an expansion preview.
2. **Issue queue** that surfaces inconsistencies — headline case: an uncountable
   noun (`NN:U`) that also carries an `NNS` plural.
3. **Countability evidence pipeline** combining the Bochum English Countability
   Lexicon (BECL), the local ConceptSketch/BlackLab corpus (via BCQL), and
   Wiktionary as a soft fallback — advisory only, never auto-applied.

## Scope decisions

| Question | Decision |
|----------|----------|
| Core workflow | Both: search/edit view **and** issue queue |
| Corpus scope | Design the full evidence pipeline now |
| Corpus source | Local ConceptSketch (`/mnt/d/git/word-sketch-lucene`), REST `POST /api/bcql` |
| BECL | Available, not yet integrated → ingestion step required |
| Wiktionary | Live MediaWiki API, cached locally |
| Stack | Python + Flask (reuses existing `inflection.py` / `check-syntax.py`) |
| Editable files | `src-clean.txt` **and** `src-pending.txt` |

## The golden rule — one source of truth, one code path

The app never re-implements dictionary logic. It imports the existing
`src-dict/inflection.py` and `src-dict/check-syntax.py`, so entries are validated
and expanded with byte-identical logic to the build.

Required refactor (behaviour-preserving):
- `check_line()` currently `print()`s errors and the module runs a file loop at
  import time. Change it to **return a list of structured problems** and guard
  the CLI loop under `if __name__ == "__main__":`. The existing CLI behaviour is
  preserved; the function becomes importable and testable.

Key reused API:
- `inflection.getFormsFromLine(line)` → list of `"form\tlemma\ttag\tvariants"`
  rows — the canonical expansion the build emits into the tagger dictionary.
- `inflection.getLemmaAndExtra(lemma)` — parse lemma + bracket extra.
- `check_line(line)` (refactored) — validation identical to the build.

## Architecture

- **Flask**, server-rendered (Jinja) pages + small vanilla JS for the live
  validation/preview panel. No SPA build step. Run with `flask run`.
- **In-memory model:** on startup, parse each source file into an ordered list of
  `Entry` objects: `{raw_line, lemma(s), tags, variants, comment, file, line_no,
  byte_span}`. The file's exact byte layout (comments, `#`-suppressed lines,
  order, whitespace) is preserved; only edited lines are rewritten so `git diff`
  stays minimal.
- **SQLite cache** (`.editor-cache.db`, git-ignored) holds only *derived* data:
  BECL import, Wiktionary lookups, corpus results (with TTL), and the last
  issue-scan snapshot. The dictionary text files remain authoritative — the
  dictionary itself is never stored in the DB.

## Entry editor & validation

- **Search** over lemmas and inflected forms (indexed via `getFormsFromLine`).
- **Editor** edits the raw source line; a debounced `POST /validate` returns:
  1. **Expansion preview** — exact `form → lemma → tag` rows the shorthand will
     generate, shown before saving.
  2. **Validation** — structured problems from the refactored `check_line()`.
- **Suppress** toggle prepends `#` (existing disable convention) instead of
  deleting.
- A save persists only if validation passes — the app cannot write a line the
  build would reject.

## Inconsistency / issue engine

Rules are small pure functions `(Entry, expanded_forms) -> Issue | None`, so new
rules are cheap to add. Launch rules:

- **Uncountable-with-plural (headline):** a lemma with an `NN:U` form *and* an
  `NNS` form → flag. `NN:UN` + `NNS` is **allowed** (the "sometimes countable"
  tag) and is not flagged.
- **Shorthand check:** `noun_U` entries whose expansion still yields `NNS`.
- **Orphan plural:** an `NNS` form with no singular `NN*`.
- **Duplicate lemma / conflicting tags** across lines.
- **Validation failures** from `check_line` surface here too.

Each issue links to the editor for that entry and, on demand, to the evidence
panel.

## Countability evidence pipeline

A single `EvidenceProvider` interface:
`lookup(lemma) -> CountabilityEvidence{verdict, confidence, detail, source_url}`
with `verdict ∈ {countable, uncountable, both, unknown}`. Providers run in
parallel and results are cached per-lemma in SQLite with timestamps.

1. **BECL (Bochum) — authority, `confidence: high`.**
   One-time ingestion maps BECL countability classes onto our tagset
   (roughly: countable → `NN`, uncountable → `NN:U`, both/plural-only → `NN:UN`).
   Store the raw BECL class alongside the mapping so it is auditable/revisable.

2. **Corpus (ConceptSketch / BCQL) — empirical check.**
   Two `POST /api/bcql` queries per lemma:
   - plural: `[lemma="X" & xpos="NNS"]`
   - all-noun: `[lemma="X" & xpos="NN.*"]`
   Use each response's `total` to compute a **plural rate**. High rate ⇒ evidence
   for countable (`confidence: medium`); near-zero ⇒ weak evidence for uncountable
   (`confidence: low`, because the clean academic corpus has recall gaps —
   *silence is not proof*). KWIC rows shown for eyeballing.

   BCQL contract (`/mnt/d/git/word-sketch-lucene`):
   - Request: `POST /api/bcql` body `{"query": "...", "top": 20, "offset": 0}`
   - Response: `{status, query, total, offset, pageSize, results:[{sentence,
     leftText, matchText, rightText, collocateLemma, frequency, logDice, ...}]}`
   - Default corpus server: `http://localhost:8080`.

3. **Wiktionary — soft fallback, `confidence: low`.**
   Live MediaWiki API, parse `uncountable`/`countable` labels, cache locally.
   Used mainly when BECL is silent.

**Adjudication:** the app never auto-edits. It shows all three verdicts side by
side with a combined suggestion (BECL-weighted, corpus-confirmed) and highlights
**disagreements** (e.g. entry says `NN:U`, BECL says countable, corpus shows a
healthy plural rate → strong "reconsider" prompt). The maintainer decides; one
click applies the tag change through the same validated save path.

## Safe writes, storage & git

- **Line-precise edits:** keep each entry's original byte span; saving rewrites
  only its line(s). A one-word change → a one-line `git diff`.
- **Atomic + guarded:** write temp file then `os.replace()`. Before writing,
  re-check the file mtime/hash against what was loaded; if it changed externally,
  refuse and reload (prevents silent clobbering).
- **Re-validate before disk:** a save persists only if `check_line()` returns no
  errors.
- **Git:** default is hands-off — the app only touches the source file; the
  maintainer reviews `git diff` and commits normally. No auto-commit.

## Testing & verification

- **Golden test:** app expansion equals `getFormsFromLine`; load → save-unchanged
  → file byte-identical (round-trip safety) over a fixture.
- **Rule tests:** fixtures per issue rule (`NN:U`+`NNS` flags; `NN:UN`+`NNS`
  does not; orphan plural; duplicates).
- **Provider tests:** BCQL/Wiktionary against recorded/mocked responses (offline);
  a live smoke test hits `/health` and skips if the corpus server is down.
- **Write-safety test:** concurrent-modification guard + atomic replace.

## Out of scope (YAGNI for v1)

- Multi-user / auth (single-user local tool).
- Tagging the 74B-sentence corpus (separate effort in `word-sketch-lucene`).
- Editing the compiled binary dictionaries (`*.dict`) — always rebuild from source.
