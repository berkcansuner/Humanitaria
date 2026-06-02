from typing import List, Dict, Any

from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import get_settings


def chunk_document(doc: Dict[str, Any], chunk_size: int = None, chunk_overlap: int = None) -> List[Dict[str, Any]]:
    settings = get_settings()
    size = chunk_size or settings.CHUNK_SIZE          # characters
    overlap = chunk_overlap or settings.CHUNK_OVERLAP
    raw_date = doc.get("date", "")
    try:
        date_ts = int(raw_date[:10].replace("-", "")) if raw_date[:10].count("-") == 2 else 0
    except (ValueError, AttributeError):
        date_ts = 0
    body = doc.get("body", "")
    if not body or not body.strip():
        return []
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=size,
        chunk_overlap=overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = []
    for i, chunk_text in enumerate(splitter.split_text(body)):
        chunks.append({
            "id": f"{doc['id']}_{i}",
            "content": chunk_text,
            "metadata": {
                "doc_id": doc["id"],
                "url": doc.get("url", ""),
                "title": doc.get("title", ""),
                "country": doc.get("country", ""),
                "theme": doc.get("theme", ""),
                "date": doc.get("date", ""),
                "date_ts": date_ts,
                "source": doc.get("source", ""),
                "format": doc.get("format", ""),
                "doctype": doc.get("doctype", ""),
            },
        })
    return chunks
