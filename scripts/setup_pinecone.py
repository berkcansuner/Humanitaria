import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pinecone import Pinecone, ServerlessSpec

from config import get_settings

logger = logging.getLogger(__name__)


def create_index() -> None:
    """Create the Pinecone serverless index if it does not already exist."""
    settings = get_settings()
    # gemini-embedding-001 (OpenAI-compatible endpoint) always returns 3072 dim.
    # Creating the index at any other dimension silently breaks every upsert.
    if settings.EMBED_PROVIDER == "gemini" and settings.EMBED_DIM != 3072:
        raise ValueError(
            f"EMBED_PROVIDER=gemini requires EMBED_DIM=3072 (got {settings.EMBED_DIM}). "
            "Fix EMBED_DIM in .env before creating the Pinecone index."
        )
    pc = Pinecone(api_key=settings.PINECONE_API_KEY)
    existing = [idx.name for idx in pc.list_indexes()]
    if settings.PINECONE_INDEX in existing:
        print(f"Index '{settings.PINECONE_INDEX}' already exists — nothing to do.")
        return
    pc.create_index(
        name=settings.PINECONE_INDEX,
        dimension=settings.EMBED_DIM,
        metric="cosine",
        spec=ServerlessSpec(cloud=settings.PINECONE_CLOUD, region=settings.PINECONE_REGION),
    )
    print(
        f"Created index '{settings.PINECONE_INDEX}' "
        f"(dim={settings.EMBED_DIM}, cosine, {settings.PINECONE_CLOUD}/{settings.PINECONE_REGION})."
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    create_index()
