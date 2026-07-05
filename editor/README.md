# Dictionary Editor

A small single-user local web app for maintaining the English PoS dictionary
source (`src-dict/src-clean.txt`, `src-dict/src-pending.txt`).

Features:
- **Search + structured editor** with live validation and an expansion preview.
- **Issue queue** flagging inconsistencies (headline: `NN:U` uncountable nouns
  that also carry an `NNS` plural; also orphan plurals and validation errors).
- **Countability evidence** per entry from BECL, the local ConceptSketch corpus
  (BCQL), and Wiktionary — advisory only, never auto-applied.

It reuses `src-dict/inflection.py` and `src-dict/check-syntax.py` as the single
source of truth, so validation and expansion match the build exactly. The text
files stay authoritative; edits are byte-precise and go through validation.

## Run

```bash
pip install -r editor/requirements.txt
CORPUS_URL=http://localhost:8080 flask --app editor.app run
# open http://127.0.0.1:5000
```

Run from the repo root. `CORPUS_URL` points at a running ConceptSketch server
(`/mnt/d/git/word-sketch-lucene`); if it is down, corpus evidence degrades to
"unknown" and the rest still works.

## Ingest BECL

The BECL provider reads a normalised table in the cache DB. Populate it once:

```bash
python -m editor.ingest_becl path/to/becl_file.tsv \
    --db editor/.editor-cache.db --lemma-col 0 --class-col 1 --delim tab
```

Adjust `--lemma-col`/`--class-col`/`--delim` to the real file layout, and extend
`BECL_CLASS_TO_VERDICT` in `editor/providers/becl.py` if new class names appear.

## Tests

```bash
python3 -m pytest editor/tests -v
```

## Notes

- The source files are authoritative. The app only touches the file you edit,
  one line at a time — review `git diff` and commit through your normal workflow.
  There is no auto-commit.
- `editor/.editor-cache.db` is a disposable cache (git-ignored): issue snapshot
  and evidence lookups. Delete it any time to reset.
