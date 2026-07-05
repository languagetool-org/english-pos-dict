from editor.cache import Cache
from editor.providers.becl import BeclProvider, classify
from editor.ingest_becl import ingest


def test_classify_maps_classes():
    assert classify("uncountable") == "uncountable"
    assert classify("Countable") == "countable"
    assert classify("mass") == "uncountable"
    assert classify("dual") == "both"
    assert classify("weird") == "unknown"


def test_provider_reads_table(tmp_path):
    cache = Cache(tmp_path / "c.db")
    cache.put_becl("advice", "uncountable", "uncountable")
    ev = BeclProvider(cache).lookup("advice")
    assert ev.source == "becl"
    assert ev.verdict == "uncountable"
    assert ev.confidence == "high"
    assert ev.detail["becl_class"] == "uncountable"


def test_provider_missing_lemma(tmp_path):
    cache = Cache(tmp_path / "c.db")
    ev = BeclProvider(cache).lookup("nope")
    assert ev.verdict == "unknown"
    assert ev.detail["found"] is False


def test_ingest_tsv(tmp_path):
    raw = tmp_path / "becl.tsv"
    raw.write_text("# lemma\tclass\nadvice\tuncountable\nbicycle\tcountable\n",
                   encoding="utf-8")
    cache = Cache(tmp_path / "c.db")
    n = ingest(str(raw), cache)
    assert n == 2
    assert BeclProvider(cache).lookup("bicycle").verdict == "countable"
