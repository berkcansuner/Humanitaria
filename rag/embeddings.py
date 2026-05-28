import logging
import time
from typing import List

import ollama
from langchain_core.embeddings import Embeddings

from config import get_settings

logger = logging.getLogger(__name__)

_RETRY_COUNT = 3
_RETRY_BACKOFF_S = 1.0


class OllamaLangChainEmbeddings(Embeddings):
    def __init__(self):
        self.settings = get_settings()
        self.client = ollama.Client(host=self.settings.OLLAMA_LOCAL_BASE_URL)
        self.model = self.settings.OLLAMA_EMBED_MODEL
        self.batch_size = self.settings.EMBED_BATCH_SIZE
        self.expected_dim = self.settings.EMBED_DIM

    def _embed_with_retry(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of texts with exponential-backoff retry."""
        backoff = _RETRY_BACKOFF_S
        for attempt in range(_RETRY_COUNT):
            try:
                resp = self.client.embed(model=self.model, input=texts)
                embeddings = resp.get("embeddings", [])
                if not embeddings or len(embeddings) != len(texts):
                    raise ValueError(
                        f"Invalid embedding response for model '{self.model}': "
                        f"expected {len(texts)} vectors, got {len(embeddings or [])}"
                    )
                return embeddings
            except Exception as e:
                logger.error(
                    "Embedding failed (attempt %d/%d): %s", attempt + 1, _RETRY_COUNT, e
                )
                if attempt < _RETRY_COUNT - 1:
                    time.sleep(backoff)
                    backoff *= 2
                else:
                    raise

    def _validate_dim(self, vec: List[float]) -> None:
        """Assert that the returned dimension matches EMBED_DIM."""
        if len(vec) != self.expected_dim:
            raise ValueError(
                f"Embedding dimension mismatch for model '{self.model}': "
                f"got {len(vec)}, expected EMBED_DIM={self.expected_dim}. "
                "Update EMBED_DIM in .env to match the actual model output dimension."
            )

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        all_embeddings: List[List[float]] = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            batch_vecs = self._embed_with_retry(batch)
            all_embeddings.extend(batch_vecs)
        if all_embeddings:
            self._validate_dim(all_embeddings[0])
        return all_embeddings

    def embed_query(self, text: str) -> List[float]:
        embeddings = self._embed_with_retry([text])
        vec = embeddings[0]
        self._validate_dim(vec)
        return vec
