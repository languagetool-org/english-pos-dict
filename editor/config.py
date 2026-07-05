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
        ],
        "DB_PATH": str(Path(__file__).resolve().parent / ".editor-cache.db"),
        "CORPUS_URL": os.environ.get("CORPUS_URL", "http://localhost:8080"),
    }
