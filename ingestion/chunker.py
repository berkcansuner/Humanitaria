from typing import List, Dict, Any
from config import get_settings


def chunk_document(
    doc: Dict[str, Any],
    chunk_size: int = None,
    chunk_overlap: int = None,
) -> List[Dict[str, Any]]:
    settings = get_settings()
    size = chunk_size or settings.CHUNK_SIZE
    overlap = chunk_overlap or settings.CHUNK_OVERLAP
    raw_date = doc.get("date", "")
    try:
        date_ts = int(raw_date[:10].replace("-", "")) if raw_date[:10].count("-") == 2 else 0
    except (ValueError, AttributeError):
        date_ts = 0
    body = doc.get("body", "")
    words = body.split()
    if not words:
        return []
    chunks = []
    start = 0
    while start < len(words):
        end = start + size
        chunk_words = words[start:end]
        chunk_text = " ".join(chunk_words)
        chunks.append({
            "id": f"{doc['id']}_{start}",
            "content": chunk_text,
            "metadata": {
                "doc_id": doc["id"],   # used by store.delete_document_chunks for orphan cleanup
                "url": doc.get("url", ""),
                "title": doc.get("title", ""),
                "country": doc.get("country", ""),
                "theme": doc.get("theme", ""),
                "date": doc.get("date", ""),
                "date_ts": date_ts,   # numeric YYYYMMDD for Pinecone $gte range filtering
                "source": doc.get("source", ""),
                "format": doc.get("format", ""),
                "doctype": doc.get("doctype", ""),
            }
        })
        if end >= len(words):
            break
        start = end - overlap
    return chunks
