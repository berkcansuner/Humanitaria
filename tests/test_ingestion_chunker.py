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


def test_chunk_metadata_includes_enrichment_fields():
    doc = _doc("Bir cümle. " * 400, iso3="SYR", language="English",
               themes=["Health", "Protection and Human Rights"], glide="EQ-2023-000015-SYR")
    md = chunk_document(doc, chunk_size=1500, chunk_overlap=200)[0]["metadata"]
    assert md["iso3"] == "SYR"
    assert md["language"] == "English"
    assert md["themes"] == ["Health", "Protection and Human Rights"]
    assert md["glide"] == "EQ-2023-000015-SYR"


def test_chunk_metadata_includes_disaster_type():
    doc = _doc("Bir cümle. " * 400, disaster_type="Flood")
    md = chunk_document(doc, chunk_size=1500, chunk_overlap=200)[0]["metadata"]
    assert md["disaster_type"] == "Flood"


def test_chunk_metadata_disaster_type_defaults_empty_when_absent():
    md = chunk_document(_doc("Bir cümle. " * 400), chunk_size=1500, chunk_overlap=200)[0]["metadata"]
    assert md["disaster_type"] == ""


def test_chunk_omits_empty_themes_list():
    # No themes → the list key is omitted (Pinecone metadata dislikes empty lists).
    md = chunk_document(_doc("Bir cümle. " * 400), chunk_size=1500, chunk_overlap=200)[0]["metadata"]
    assert "themes" not in md
