"""Ingest a raw BECL file into the normalised ``becl`` cache table.

Usage:
    python -m editor.ingest_becl <becl_file> [--db editor/.editor-cache.db]
                                 [--lemma-col 0] [--class-col 1] [--delim tab]

The raw BECL distribution format is not yet finalised here, so the parser is
deliberately tolerant: it reads a delimited table and lets you point at the
lemma and class columns. Each row is stored with its raw class plus the mapped
verdict, so the mapping stays auditable and revisable.
"""

import argparse
import csv
import sys

from editor.cache import Cache
from editor.providers.becl import classify


def ingest(path, cache, lemma_col=0, class_col=1, delimiter="\t"):
    count = 0
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.reader(f, delimiter=delimiter)
        for row in reader:
            if not row or row[0].startswith("#"):
                continue
            if len(row) <= max(lemma_col, class_col):
                continue
            lemma = row[lemma_col].strip()
            becl_class = row[class_col].strip()
            if not lemma:
                continue
            cache.put_becl(lemma, becl_class, classify(becl_class))
            count += 1
    return count


def _main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("becl_file")
    p.add_argument("--db", default="editor/.editor-cache.db")
    p.add_argument("--lemma-col", type=int, default=0)
    p.add_argument("--class-col", type=int, default=1)
    p.add_argument("--delim", default="tab",
                   help="'tab', 'comma', or a literal delimiter character")
    args = p.parse_args(argv)
    delimiter = {"tab": "\t", "comma": ","}.get(args.delim, args.delim)
    cache = Cache(args.db)
    n = ingest(args.becl_file, cache, args.lemma_col, args.class_col, delimiter)
    print(f"Ingested {n} BECL entries into {args.db}")


if __name__ == "__main__":
    _main(sys.argv[1:])
