import pytest
from ingestion.chunker import chunk_document


class TestChunker:
    def test_chunks_preserves_metadata(self):
        doc = {
            "id": "abc",
            "url": "https://example.com",
            "title": "Title",
            "body": "Word " * 200,
            "date": "2026-04-01",
            "country": "Iran",
            "theme": "Food",
            "source": "WFP",
            "format": "Report",
            "doctype": "report",
        }
        chunks = chunk_document(doc, chunk_size=50, chunk_overlap=10)
        assert len(chunks) > 1
        for c in chunks:
            assert c["metadata"]["title"] == "Title"
            assert c["metadata"]["country"] == "Iran"
            assert c["metadata"]["url"] == "https://example.com"
            assert c["metadata"]["doctype"] == "report"
            assert "content" in c

    def test_short_body_single_chunk(self):
        doc = {
            "id": "abc", "url": "https://example.com", "title": "T",
            "body": "Short body.", "date": "", "country": "", "theme": "", "source": "", "format": "", "doctype": "disaster"
        }
        chunks = chunk_document(doc, chunk_size=100, chunk_overlap=10)
        assert len(chunks) == 1
        assert chunks[0]["content"] == "Short body."
        assert chunks[0]["metadata"]["doctype"] == "disaster"

    def test_doctype_in_metadata(self):
        doc = {
            "id": "xyz", "url": "u", "title": "T", "body": "text",
            "date": "", "country": "", "theme": "", "source": "", "format": "", "doctype": "country"
        }
        chunks = chunk_document(doc)
        assert chunks[0]["metadata"]["doctype"] == "country"