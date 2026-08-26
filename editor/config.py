"""Runtime configuration (paths, corpus URL) with environment overrides."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_DICT = ROOT / "src-dict"


def default_config():
    return {
        "SOURCE_FILES": [
            str(SRC_DICT / "src-clean.txt"),
            str(SRC_DICT / "src-pending.txt"),
            str(SRC_DICT / "src-discarded.txt"),
        ],
        "DB_PATH": str(Path(__file__).resolve().parent / ".editor-cache.db"),
        "CORPUS_URL": os.environ.get("CORPUS_URL", ""),
        # word-sketch/BlackLab server exposing POST /api/bcql (article test).
        "BCQL_URL": os.environ.get("BCQL_URL", ""),
        # Path to ESDB scowl.db (github.com/en-wl/wordlist). Defaults to a
        # well-known dev location when present; empty means off.
        "ESDB_PATH": os.environ.get(
            "ESDB_PATH",
            str(Path("/tmp/enwl/scowl.db"))
            if Path("/tmp/enwl/scowl.db").exists() else ""),
    }
