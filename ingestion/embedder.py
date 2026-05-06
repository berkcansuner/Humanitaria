import logging
import time
from typing import List, Dict, Any
import ollama
from config import get_settings

logger = logging.getLogger(__name__)

class OllamaEmbedder:
    def __init__(self):
        self.settings = get_settings()
        self.client = ollama.Client(host=self.settings.OLLAMA_LOCAL_BASE_URL)
        self.model = self.settings.OLLAMA_EMBED_MODEL

    def embed(self, text: str) -> List[float]:
        max_retries = 3
        backoff = 1.0
        for attempt in range(max_retries):
            try:
                resp = self.client.embed(model=self.model, input=[text])
                embeddings = resp.get("embeddings", [])
                if embeddings and len(embeddings) > 0:
                    return embeddings[0]
                raise ValueError("Empty embedding response")
            except Exception as e:
                logger.error("Embedding failed (attempt %d): %s", attempt + 1, e)
                if attempt < max_retries - 1:
                    time.sleep(backoff)
                    backoff *= 2
                else:
                    raise
        return []

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        max_retries = 3
        backoff = 1.0
        for attempt in range(max_retries):
            try:
                resp = self.client.embed(model=self.model, input=texts)
                embeddings = resp.get("embeddings", [])
                if embeddings and len(embeddings) == len(texts):
                    return embeddings
                raise ValueError(f"Expected {len(texts)} embeddings, got {len(embeddings)}")
            except Exception as e:
                logger.error("Batch embedding failed (attempt %d): %s", attempt + 1, e)
                if attempt < max_retries - 1:
                    time.sleep(backoff)
                    backoff *= 2
                else:
                    raise
        return []
