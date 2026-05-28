import logging
import time
from typing import List

import ollama

from config import get_settings

logger = logging.getLogger(__name__)


class OllamaEmbedder:
    def __init__(self):
        self.settings = get_settings()
        self.client = ollama.Client(host=self.settings.OLLAMA_LOCAL_BASE_URL)
        self.model = self.settings.OLLAMA_EMBED_MODEL
        self.batch_size = self.settings.EMBED_BATCH_SIZE

    def embed(self, text: str) -> List[float]:
        max_retries = 3
        backoff = 1.0
        for attempt in range(max_retries):
            try:
                resp = self.client.embed(model=self.model, input=[text], options={"num_gpu": 999})
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

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of texts, sending at most EMBED_BATCH_SIZE per Ollama call."""
        all_embeddings: List[List[float]] = []
        for i in range(0, len(texts), self.batch_size):
            sub_batch = texts[i : i + self.batch_size]
            all_embeddings.extend(self._embed_sub_batch(sub_batch))
        return all_embeddings

    def _embed_sub_batch(self, texts: List[str]) -> List[List[float]]:
        max_retries = 3
        backoff = 1.0
        for attempt in range(max_retries):
            try:
                resp = self.client.embed(model=self.model, input=texts, options={"num_gpu": 999})
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
