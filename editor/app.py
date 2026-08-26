"""Flask app: search + entry editor, issue queue, and evidence panel.

The source text files stay authoritative; edits go through the validated,
byte-precise DictFile save path. Derived data (issues snapshot, evidence) is
cached in SQLite.
"""

import os
import subprocess
import sys
from pathlib import Path

from flask import (Flask, jsonify, redirect, render_template, request,
                   url_for, abort)

from editor.cache import Cache
from editor.config import default_config
from editor.dictmodel import DictFile, StaleFileError
from editor.dictlogic import expand_line, validate_line
from editor.issues import scan_entries
from editor.providers.aggregate import gather, adjudicate
from editor.providers.bcql import BcqlProvider
from editor.providers.becl import BeclProvider
from editor.providers.corpus import CorpusProvider
from editor.providers.wiktionary import WiktionaryProvider

ROOT = Path(__file__).resolve().parents[1]


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
    cache = Cache(cfg["DB_PATH"])
    app.config["_CACHE"] = cache
    # Dev tool: provider logic/URLs may change between runs; never serve
    # corpus evidence computed with a previous version of the code.
    cache.clear_evidence("corpus")
    cache.clear_evidence("bcql")

    # ESDB signal: plurale-tantum incorrect-singular detection. The DB is
    # optional — if missing, we just degrade to no ESDB signal.
    from editor.esdb import Esdb, EsdbError
    try:
        esdb = Esdb(cfg.get("ESDB_PATH", ""))
    except (EsdbError, OSError):
        esdb = None
    app.config["_ESDB"] = esdb

    _build_index(app)

    # ------------------------------------------------------------------ views
    @app.route("/")
    def home():
        return redirect(url_for("search"))

    @app.route("/search")
    def search():
        q = request.args.get("q", "").strip()
        results = _search_entries(app, q) if q else []
        stats = _file_stats(app)
        return render_template("search.html", q=q, results=results, stats=stats)

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
        prev_no = line_no - 1 if line_no > 1 else None
        next_no = line_no + 1 if line_no < len(entries) else None
        return render_template("entry.html", entry=e, file=file,
                               show_evidence=show_evidence,
                               prev_no=prev_no, next_no=next_no,
                               total_entries=len(entries))

    @app.route("/files")
    def files():
        stats = _file_stats(app)
        return render_template("files.html", stats=stats)

    @app.route("/files/<name>")
    def file_view(name):
        df = dictfiles.get(name)
        if df is None:
            abort(404)
        entries = df.entries()
        start = request.args.get("start", 1, type=int)
        page_size = 200
        start = max(1, min(start, len(entries)))
        end = min(start + page_size - 1, len(entries))
        page = entries[start - 1:end]
        return render_template("file_view.html", name=name, entries=page,
                               start=start, total=len(entries),
                               page_size=page_size)

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
        df.invalidate()          # re-parse on next access
        _build_index(app)        # keep search fresh
        return jsonify({"ok": True})

    @app.post("/api/move")
    def api_move():
        """Triage: move an entry between source files (pending→clean, clean→pending,
        either→discarded). The entry is removed from its current file and appended
        to the destination, then validation runs before the destination write."""
        data = request.get_json(silent=True) or {}
        file = data.get("file")
        line_no = data.get("line_no")
        dest = data.get("dest")
        df = dictfiles.get(file)
        dest_df = dictfiles.get(dest)
        if df is None or dest_df is None or not isinstance(line_no, int):
            return jsonify({"error": "unknown file or line_no"}), 400
        if file == dest:
            return jsonify({"error": "source and destination are the same"}), 400
        entries = df.entries()
        if line_no < 1 or line_no > len(entries):
            return jsonify({"error": "line_no out of range"}), 400
        entry = entries[line_no - 1]
        # Preserve suppression and comment when moving.
        body = f"{entry.lemma_field}={entry.tags}={entry.variants}"
        if entry.comment:
            body = f"{body} # {entry.comment.lstrip('#').strip()}"
        raw = (("#" if entry.suppressed else "") + body).rstrip() + "\n"
        problems = validate_line(raw.lstrip("#"))
        if problems:
            return jsonify({"error": "validation failed", "problems": problems}), 400
        try:
            df.remove_line(line_no)
        except StaleFileError as exc:
            return jsonify({"error": str(exc)}), 409
        try:
            dest_df.append_line(raw)
        except StaleFileError as exc:
            # Source already changed; try to restore by re-append and report.
            df.append_line(raw)
            return jsonify({"error": str(exc)}), 409
        df.invalidate()
        dest_df.invalidate()
        _build_index(app)
        return jsonify({"ok": True, "from": file, "to": dest, "line_no": line_no})

    @app.post("/api/rescan")
    def api_rescan():
        snapshot = _rescan(app)
        return jsonify({"ok": True, "count": len(snapshot)})

    @app.get("/api/stats")
    def api_stats():
        return jsonify(_file_stats(app))

    @app.post("/api/validate-all")
    def api_validate_all():
        """Run check-syntax validation on every entry across all files."""
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "check_syntax", str(ROOT / "src-dict" / "check-syntax.py"))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            check_line = mod.check_line
        except Exception as exc:
            return jsonify({"error": f"cannot load check-syntax: {exc}"}), 500
        results = []
        for name, df in dictfiles.items():
            for e in df.entries():
                problems = check_line(e.raw_line)
                if problems:
                    results.append({"file": name, "line_no": e.line_no,
                                    "lemma": e.lemma_field,
                                    "problems": problems})
        return jsonify({"ok": True, "count": len(results), "results": results})

    @app.get("/api/git/status")
    def api_git_status():
        out = _git_run(["status", "--porcelain"])
        files = []
        for line in out.strip().splitlines():
            if line.strip():
                status = line[:2].strip()
                path = line[3:].strip()
                files.append({"status": status, "path": path})
        return jsonify({"ok": True, "files": files})

    @app.get("/api/git/diff")
    def api_git_diff():
        path = request.args.get("path", "")
        args = ["diff", "--word-diff=porcelain"]
        if path:
            args.append("--")
            args.append(path)
        out = _git_run(args)
        return jsonify({"ok": True, "diff": out})

    @app.post("/api/git/commit")
    def api_git_commit():
        data = request.get_json(silent=True) or {}
        message = data.get("message", "").strip()
        if not message:
            return jsonify({"error": "commit message required"}), 400
        paths = data.get("paths", [])
        if paths:
            _git_run(["add"] + paths)
        else:
            _git_run(["add", "-u"])
        out = _git_run(["commit", "-m", message])
        return jsonify({"ok": True, "output": out})

    @app.post("/api/run/build-dict")
    def api_run_build_dict():
        out, err, rc = _run_script(
            [sys.executable, str(ROOT / "src-dict" / "build-src-dict.py")],
            cwd=str(ROOT / "src-dict"))
        return jsonify({"ok": rc == 0, "rc": rc, "stdout": out, "stderr": err})

    @app.post("/api/run/separate")
    def api_run_separate():
        out, err, rc = _run_script(
            [sys.executable, str(ROOT / "src-dict" / "separate.py")],
            cwd=str(ROOT / "src-dict"))
        if rc == 0:
            for df in dictfiles.values():
                df.invalidate()
            _build_index(app)
        return jsonify({"ok": rc == 0, "rc": rc, "stdout": out, "stderr": err})

    @app.get("/api/settings")
    def api_settings_get():
        cache = app.config["_CACHE"]
        corpus_url = cache.get_setting("corpus_url", cfg.get("CORPUS_URL", ""))
        bcql_url = cache.get_setting("bcql_url", cfg.get("BCQL_URL", ""))
        return jsonify({"corpus_url": corpus_url,
                        "bcql_url": bcql_url,
                        "enabled": bool(corpus_url),
                        "default": cfg.get("CORPUS_URL", "")})

    @app.post("/api/settings")
    def api_settings_set():
        data = request.get_json(silent=True) or {}
        cache = app.config["_CACHE"]
        if "corpus_url" in data:
            url = (data.get("corpus_url") or "").strip()
            old = cache.get_setting("corpus_url", "")
            cache.set_setting("corpus_url", url)
            if url != old:
                cache.clear_evidence("corpus")
        if "bcql_url" in data:
            url = (data.get("bcql_url") or "").strip()
            old = cache.get_setting("bcql_url", "")
            cache.set_setting("bcql_url", url)
            if url != old:
                cache.clear_evidence("bcql")
        corpus_url = cache.get_setting("corpus_url", cfg.get("CORPUS_URL", ""))
        bcql_url = cache.get_setting("bcql_url", cfg.get("BCQL_URL", ""))
        return jsonify({"ok": True, "corpus_url": corpus_url,
                        "bcql_url": bcql_url,
                        "enabled": bool(corpus_url)})

    @app.get("/api/evidence/<lemma>")
    def api_evidence(lemma):
        cache = app.config["_CACHE"]
        corpus_url = cache.get_setting("corpus_url", cfg.get("CORPUS_URL", ""))
        bcql_url = cache.get_setting("bcql_url", cfg.get("BCQL_URL", ""))
        plural_form = _plural_form_for(app, lemma)
        providers = [
            BeclProvider(cache),
            CorpusProvider(corpus_url, plural_form=plural_form),
            BcqlProvider(bcql_url),
            WiktionaryProvider(),
        ]
        current_tags = _current_tags_for(app, lemma)
        evidences = gather(lemma, providers, cache)
        result = adjudicate(evidences, current_tags)
        result["lemma"] = lemma
        # ESDB signal. Two modes: (a) flag incorrect singulars of plurale
        # tantum nouns (gallow→gallows) as uncountable/high; (b) for any noun
        # ESDB knows, add an informational spelling-attestation row — never
        # countability evidence, since ESDB lists regular plurals mechanically
        # even for mass nouns ('advices', 'furnitures').
        esdb = app.config.get("_ESDB")
        if esdb is not None and lemma.islower():
            if esdb.singular_is_incorrect(lemma):
                result["plural_tantum"] = True
                result["plural_tantum_plural"] = esdb.plural_surface(lemma)
                result["verdicts"].append({
                    "source": "esdb", "verdict": "uncountable",
                    "confidence": "high",
                    "detail": {
                        "note": (f"'{lemma}' has no singular noun; its plural "
                                 f"'{esdb.plural_surface(lemma)}' is plural-only "
                                 "in ESDB (plurale tantum)."),
                        "available": True, "source_url": "ESDB",
                    }})
            elif esdb.is_noun_headword(lemma):
                pl = esdb.attested_plural(lemma)
                note = f"'{lemma}' is an ESDB noun headword; "
                note += (f"plural '{pl}' recorded." if pl
                         else "no plural recorded.")
                result["verdicts"].append({
                    "source": "esdb", "verdict": "unknown",
                    "confidence": "low",
                    "detail": {"note": note, "available": True,
                               "source_url": "ESDB"}})
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


def _file_stats(app):
    """Return entry counts and issue counts per file."""
    stats = {}
    for name, df in app.config["_DICTFILES"].items():
        entries = df.entries()
        total = len(entries)
        suppressed = sum(1 for e in entries if e.suppressed)
        active = total - suppressed
        stats[name] = {"total": total, "active": active,
                        "suppressed": suppressed}
    return stats


def _rescan(app):
    all_entries = []
    for df in app.config["_DICTFILES"].values():
        all_entries.extend(df.entries())
    issues = [i.to_dict() for i in scan_entries(all_entries)]
    app.config["_CACHE"].put_issues_snapshot(issues)
    return issues


def _plural_form_for(app, lemma):
    """Find the plural (NNS) form for a lemma from the dictionary entries.

    Uses the lexicographer-curated inflections (e.g. 'boxes/NNS', 'theories')
    instead of naive +s pluralisation. Returns None if no NNS form is recorded.
    """
    for name, line_no in app.config["_INDEX"].get(lemma.lower(), []):
        e = app.config["_DICTFILES"][name].entries()[line_no - 1]
        try:
            for form, _l, tag, _v in expand_line(e.logical_line):
                if tag == "NNS":
                    return form
        except Exception:
            pass
    return None


def _current_tags_for(app, lemma):
    """All inflection tags recorded for the lemma, with the compound NN:UN
    ('countable AND uncountable') expanded into its components so that
    one-sided evidence verdicts compare correctly against dual-tagged
    entries (e.g. theory=noun_UN must not disagree with 'countable')."""
    tags = set()
    for name, line_no in app.config["_INDEX"].get(lemma.lower(), []):
        e = app.config["_DICTFILES"][name].entries()[line_no - 1]
        try:
            for _f, _l, tag, _v in expand_line(e.logical_line):
                if tag == "NN:UN":
                    tags.update({"NN", "NN:U"})
                else:
                    tags.add(tag)
        except Exception:
            pass
    return tags


def _git_run(args):
    """Run a git command in the repo root; return stdout."""
    try:
        r = subprocess.run(["git"] + args, capture_output=True, text=True,
                           cwd=str(ROOT), timeout=30)
        return r.stdout
    except Exception as exc:
        return f"git error: {exc}\n"


def _run_script(cmd, cwd=None, timeout=120):
    """Run a script and return (stdout, stderr, returncode)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           cwd=cwd, timeout=timeout)
        return r.stdout, r.stderr, r.returncode
    except subprocess.TimeoutExpired:
        return "", "timed out", 1
    except Exception as exc:
        return "", str(exc), 1
