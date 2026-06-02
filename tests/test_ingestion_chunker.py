from ingestion.chunker import chunk_document


def _doc(body, **kw):
    base = {"id": "abc", "url": "u", "title": "T", "country": "Syria", "theme": "Health",
            "date": "2026-05-01", "source": "WHO", "format": "Report", "doctype": "report"}
    base.update(kw); base["body"] = body
    return base


def test_empty_body_returns_no_chunks():
    assert chunk_document(_doc("")) == []
    assert chunk_document(_doc("   ")) == []


def test_long_body_splits_into_bounded_chunks():
    body = ("Bir cümle. " * 400)  # ~4400 chars
    chunks = chunk_document(_doc(body), chunk_size=1500, chunk_overlap=200)
    assert len(chunks) >= 3
    # Each chunk respects the size bound (allow a small separator slack).
    assert all(len(c["content"]) <= 1500 + 50 for c in chunks)


def test_chunk_metadata_and_ids_preserved():
    chunks = chunk_document(_doc("Bir cümle. " * 400), chunk_size=1500, chunk_overlap=200)
    c = chunks[0]
    assert c["id"] == "abc_0"
    assert c["metadata"]["doc_id"] == "abc"
    assert c["metadata"]["country"] == "Syria"
    assert c["metadata"]["date"] == "2026-05-01"
    assert c["metadata"]["date_ts"] == 20260501
    assert c["metadata"]["doctype"] == "report"
    # ids are doc_id-prefixed + ordinal (orphan cleanup uses the "{doc_id}_" prefix)
    assert [x["id"] for x in chunks] == [f"abc_{i}" for i in range(len(chunks))]


def test_invalid_date_gives_zero_ts():
    chunks = chunk_document(_doc("Bir cümle. " * 400, date=""), chunk_size=1500, chunk_overlap=200)
    assert chunks[0]["metadata"]["date_ts"] == 0


def test_short_body_single_chunk():
    chunks = chunk_document(_doc("Kısa bir gövde."), chunk_size=1500, chunk_overlap=200)
    assert len(chunks) == 1
    assert chunks[0]["content"] == "Kısa bir gövde."
