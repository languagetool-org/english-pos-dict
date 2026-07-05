"""Flask app: search + entry editor, issue queue, and evidence panel.

The source text files stay authoritative; edits go through the validated,
byte-precise DictFile save path. Derived data (issues snapshot, evidence) is
cached in SQLite.
"""

from pathlib import Path

from flask import (Flask, jsonify, redirect, render_template, request,
                   url_for, abort)

from editor.cache import Cache
from editor.config import default_config
from editor.dictmodel import DictFile, StaleFileError
from editor.dictlogic import expand_line, validate_line
from editor.issues import scan_entries
from editor.providers.aggregate import gather, adjudicate
from editor.providers.becl import BeclProvider
from editor.providers.corpus import CorpusProvider
from editor.providers.wiktionary import WiktionaryProvider


def create_app(config=None):
    app = Flask(__name__)
    cfg = default_config()
    if config:
        cfg.update(config)
    app.config.update(cfg)

    # One DictFile per source, keyed by basename.
    dictfiles = {}
    for path in cfg["SOURCE_FILES"]:
        p = Path(path)
        if p.exists():
            dictfiles[p.name] = DictFile(p)
    app.config["_DICTFILES"] = dictfiles
    app.config["_CACHE"] = Cache(cfg["DB_PATH"])

    _build_index(app)

    # ------------------------------------------------------------------ views
    @app.route("/")
    def home():
        return redirect(url_for("search"))

    @app.route("/search")
    def search():
        q = request.args.get("q", "").strip()
        results = _search_entries(app, q) if q else []
        return render_template("search.html", q=q, results=results)

    @app.route("/entry/<file>/<int:line_no>")
    def entry(file, line_no):
        df = dictfiles.get(file)
        if df is None:
            abort(404)
        entries = df.entries()
        if line_no < 1 or line_no > len(entries):
            abort(404)
        e = entries[line_no - 1]
        show_evidence = request.args.get("evidence") == "1"
        return render_template("entry.html", entry=e, file=file,
                               show_evidence=show_evidence)

    @app.route("/issues")
    def issues():
        cache = app.config["_CACHE"]
        snapshot = cache.get_issues_snapshot()
        if snapshot is None:
            snapshot = _rescan(app)
        grouped = {}
        for issue in snapshot:
            grouped.setdefault(issue["rule"], []).append(issue)
        return render_template("issues.html", grouped=grouped,
                               total=len(snapshot))

    # ------------------------------------------------------------------- api
    @app.post("/api/validate")
    def api_validate():
        line = (request.get_json(silent=True) or {}).get("line", "")
        try:
            expansion = [list(t) for t in expand_line(line)]
        except Exception as exc:  # malformed line still returns validation msgs
            expansion = []
        return jsonify({"problems": validate_line(line), "expansion": expansion})

    @app.post("/api/save")
    def api_save():
        data = request.get_json(silent=True) or {}
        file = data.get("file")
        line_no = data.get("line_no")
        line = data.get("line", "")
        df = dictfiles.get(file)
        if df is None or not isinstance(line_no, int):
            return jsonify({"error": "unknown file or line_no"}), 400
        problems = validate_line(line)
        if problems:
            return jsonify({"error": "validation failed", "problems": problems}), 400
        try:
            df.replace_line(line_no, line)
        except StaleFileError as exc:
            return jsonify({"error": str(exc)}), 409
        _build_index(app)  # keep search fresh
        return jsonify({"ok": True})

    @app.post("/api/rescan")
    def api_rescan():
        snapshot = _rescan(app)
        return jsonify({"ok": True, "count": len(snapshot)})

    @app.get("/api/evidence/<lemma>")
    def api_evidence(lemma):
        cache = app.config["_CACHE"]
        providers = [
            BeclProvider(cache),
            CorpusProvider(cfg["CORPUS_URL"]),
            WiktionaryProvider(),
        ]
        current_tags = _current_tags_for(app, lemma)
        evidences = gather(lemma, providers, cache)
        result = adjudicate(evidences, current_tags)
        return jsonify(result)

    return app


# ---------------------------------------------------------------- internals
def _build_index(app):
    """Build lemma/form -> [(file, line_no)] index over all entries."""
    index = {}
    for name, df in app.config["_DICTFILES"].items():
        for e in df.entries():
            if e.suppressed or not e.tags:
                continue
            keys = {e.lemma_field.lower()}
            try:
                for form, lemma, _tag, _var in expand_line(e.logical_line):
                    keys.add(form.lower())
                    keys.add(lemma.lower())
            except Exception:
                pass
            for k in keys:
                index.setdefault(k, []).append((name, e.line_no))
    app.config["_INDEX"] = index


def _search_entries(app, q):
    index = app.config["_INDEX"]
    dictfiles = app.config["_DICTFILES"]
    hits = []
    seen = set()
    ql = q.lower()
    # exact match first, then prefix matches
    keys = [ql] + sorted(k for k in index if k.startswith(ql) and k != ql)
    for key in keys:
        for file, line_no in index.get(key, []):
            if (file, line_no) in seen:
                continue
            seen.add((file, line_no))
            e = dictfiles[file].entries()[line_no - 1]
            hits.append({"file": file, "line_no": line_no,
                         "lemma": e.lemma_field, "tags": e.tags,
                         "variants": e.variants})
            if len(hits) >= 100:
                return hits
    return hits


def _rescan(app):
    all_entries = []
    for df in app.config["_DICTFILES"].values():
        all_entries.extend(df.entries())
    issues = [i.to_dict() for i in scan_entries(all_entries)]
    app.config["_CACHE"].put_issues_snapshot(issues)
    return issues


def _current_tags_for(app, lemma):
    tags = set()
    for name, line_no in app.config["_INDEX"].get(lemma.lower(), []):
        e = app.config["_DICTFILES"][name].entries()[line_no - 1]
        try:
            for _f, _l, tag, _v in expand_line(e.logical_line):
                tags.add(tag)
        except Exception:
            pass
    return tags
