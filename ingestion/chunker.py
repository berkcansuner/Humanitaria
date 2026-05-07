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
                "url": doc.get("url", ""),
                "title": doc.get("title", ""),
                "country": doc.get("country", ""),
                "theme": doc.get("theme", ""),
                "date": doc.get("date", ""),
                "source": doc.get("source", ""),
                "format": doc.get("format", ""),
                "doctype": doc.get("doctype", ""),
            }
        })
        if end >= len(words):
            break
        start = end - overlap
    return chunks
