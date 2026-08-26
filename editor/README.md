# Dictionary Editor

A small single-user local web app for maintaining the English PoS dictionary
source (`src-dict/src-clean.txt`, `src-dict/src-pending.txt`).

Features:
- **Search + structured editor** with live validation and an expansion preview.
- **Issue queue** flagging inconsistencies (headline: `NN:U` uncountable nouns
  that also carry an `NNS` plural; also orphan plurals and validation errors).
- **Countability evidence** per entry from BECL, two independent corpus
  sources (BCQL article test + plural-rate counts), Wiktionary, and ESDB —
  advisory only, never auto-applied.
- **ESDB plurale-tantum signal** (`editor/scowl.db`): flags naive singulars of
  plural-only nouns (`gallow` → `gallows`).

It reuses `src-dict/inflection.py` and `src-dict/check-syntax.py` as the single
source of truth, so validation and expansion match the build exactly. The text
files stay authoritative; edits are byte-precise and go through validation.

## Run

```bash
pip install -r editor/requirements.txt
flask --app app run
# open http://127.0.0.1:5000
```

Run from the repo root. The **Corpus** dropdown in the header configures both
corpus endpoints at runtime (persisted in the cache DB) — no env var or restart
needed. They are independent corpora and run as separate evidence rows:

- **BCQL endpoint** (`POST {url}/api/bcql`, e.g. the word-sketch/BlackLab
  server at `:8080`): counts the lemma's indefinite-article contexts,
  `[word="an?"] [lemma="X"] [xpos!="V.*"]` ("a/an X"), against total lemma
  frequency. A noun that regularly takes *a/an* is being used as a countable
  singular (rate ≥ 0.014 with ≥ 10 hits ⇒ countable, medium confidence).
- **Count endpoint** (`GET {url}/count?q=term&field=en`, e.g. the
  `corpus-lucene-service` at `:8082`): plain Lucene term counts; the plural
  rate (plural hits / singular hits, plural form taken from the dictionary's
  own curated inflections) ≥ 0.05 ⇒ countable.

If an endpoint is down or unset, its evidence degrades to "unknown" and the
rest still works.

ESDB (`editor/scowl.db`, from <https://github.com/en-wl/wordlist>) powers the
plurale-tantum filter. It is optional: if absent, that signal is off. Set
`ESDB_PATH` to point elsewhere.

## Ingest BECL

The BECL provider reads a normalised table in the cache DB. Populate it once:

```bash
python -m editor.ingest_becl path/to/BECL_2.1_master.csv \
    --db editor/.editor-cache.db --encoding latin-1
```

Defaults already match the BECL 2.1 layout (`--lemma-col 1 --class-col 26 --delim ;`).
Adjust `--lemma-col`/`--class-col`/`--delim`/`--encoding` only for a different
format, and extend `BECL_CLASS_TO_VERDICT` in `editor/providers/becl.py` if new
class names appear.

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
