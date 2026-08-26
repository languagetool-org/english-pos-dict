"""SQLite cache for derived data only (evidence lookups, issue snapshot).

The dictionary text files remain authoritative; nothing here is a source of
truth. Safe to delete at any time (git-ignored).
"""

import json
import sqlite3
import threading
import time


class Cache:
    def __init__(self, db_path):
        self.db_path = str(db_path)
        # Flask's dev server serves requests on multiple threads; allow the
        # connection to be shared and serialise access with a lock.
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS evidence (
                lemma TEXT NOT NULL,
                source TEXT NOT NULL,
                json TEXT NOT NULL,
                fetched_at REAL NOT NULL,
                ttl REAL,
                PRIMARY KEY (lemma, source)
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS becl (
                lemma TEXT PRIMARY KEY,
                becl_class TEXT,
                verdict TEXT
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS kv (
                key TEXT PRIMARY KEY,
                json TEXT NOT NULL
            )
        """)
        self._conn.commit()

    # --- evidence ---------------------------------------------------------
    def put_evidence(self, lemma, source, value, ttl_seconds=None):
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO evidence (lemma, source, json, fetched_at, ttl)"
                " VALUES (?, ?, ?, ?, ?)",
                (lemma, source, json.dumps(value), time.time(), ttl_seconds))
            self._conn.commit()

    def get_evidence(self, lemma, source):
        with self._lock:
            row = self._conn.execute(
                "SELECT json, fetched_at, ttl FROM evidence WHERE lemma=? AND source=?",
                (lemma, source)).fetchone()
        if row is None:
            return None
        payload, fetched_at, ttl = row
        if ttl is not None and time.time() > fetched_at + ttl:
            return None
        return json.loads(payload)

    # --- BECL import ------------------------------------------------------
    def put_becl(self, lemma, becl_class, verdict, commit=True):
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO becl (lemma, becl_class, verdict)"
                " VALUES (?, ?, ?)", (lemma, becl_class, verdict))
            if commit:
                self._conn.commit()

    def get_becl(self, lemma):
        with self._lock:
            row = self._conn.execute(
                "SELECT becl_class, verdict FROM becl WHERE lemma=?",
                (lemma,)).fetchone()
        if row is None:
            return None
        return {"becl_class": row[0], "verdict": row[1]}

    # --- issue snapshot ---------------------------------------------------
    def put_issues_snapshot(self, issues):
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO kv (key, json) VALUES ('issues', ?)",
                (json.dumps(issues),))
            self._conn.commit()

    def get_issues_snapshot(self):
        with self._lock:
            row = self._conn.execute(
                "SELECT json FROM kv WHERE key='issues'").fetchone()
        return json.loads(row[0]) if row else None

    # --- runtime settings ------------------------------------------------
    def get_setting(self, key, default=None):
        with self._lock:
            row = self._conn.execute(
                "SELECT json FROM kv WHERE key=?", (f"setting:{key}",)).fetchone()
        if row is None:
            return default
        return json.loads(row[0])

    def set_setting(self, key, value):
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO kv (key, json) VALUES (?, ?)",
                (f"setting:{key}", json.dumps(value)))
            self._conn.commit()

    def clear_evidence(self, source=None):
        """Drop cached evidence rows (optionally for one source)."""
        with self._lock:
            if source:
                self._conn.execute("DELETE FROM evidence WHERE source=?", (source,))
            else:
                self._conn.execute("DELETE FROM evidence")
            self._conn.commit()
