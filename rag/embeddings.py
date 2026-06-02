import logging
import time
from typing import List

from langchain_core.embeddings import Embeddings
from openai import OpenAI

from config import get_settings

logger = logging.getLogger(__name__)

_RETRY_COUNT = 3
_RETRY_BACKOFF_S = 1.0


class GeminiLangChainEmbeddings(Embeddings):
    """Gemini embedding via the OpenAI-compatible endpoint (gemini-embedding-001, 3072 dim).

    Reuses GEMINI_API_KEY / GEMINI_BASE_URL — the same auth the chat LLM uses.
    """

    def __init__(self):
        self.settings = get_settings()
        self.client = OpenAI(
            api_key=self.settings.GEMINI_API_KEY,
            base_url=self.settings.GEMINI_BASE_URL,
        )
        self.model = self.settings.GEMINI_EMBED_MODEL
        self.batch_size = self.settings.EMBED_BATCH_SIZE
        self.expected_dim = self.settings.EMBED_DIM

    def _embed_with_retry(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of texts with exponential-backoff retry."""
        backoff = _RETRY_BACKOFF_S
        for attempt in range(_RETRY_COUNT):
            try:
                resp = self.client.embeddings.create(model=self.model, input=texts)
                vectors = [d.embedding for d in resp.data]
                if len(vectors) != len(texts):
                    raise ValueError(
                        f"Invalid embedding response for model '{self.model}': "
                        f"expected {len(texts)} vectors, got {len(vectors)}"
                    )
                return vectors
            except Exception as e:
                logger.error(
                    "Gemini embedding failed (attempt %d/%d): %s", attempt + 1, _RETRY_COUNT, e
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
            all_embeddings.extend(self._embed_with_retry(batch))
        if all_embeddings:
            self._validate_dim(all_embeddings[0])
        return all_embeddings

    def embed_query(self, text: str) -> List[float]:
        vec = self._embed_with_retry([text])[0]
        self._validate_dim(vec)
        return vec


def get_embeddings() -> Embeddings:
    return GeminiLangChainEmbeddings()
