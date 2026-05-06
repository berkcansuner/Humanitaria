from typing import List
import ollama
from langchain_core.embeddings import Embeddings
from config import get_settings


class OllamaLangChainEmbeddings(Embeddings):
    def __init__(self):
        self.settings = get_settings()
        self.client = ollama.Client(host=self.settings.OLLAMA_LOCAL_BASE_URL)
        self.model = self.settings.OLLAMA_EMBED_MODEL

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        resp = self.client.embed(model=self.model, input=texts)
        embeddings = resp.get("embeddings", [])
        if not embeddings or len(embeddings) != len(texts):
            raise ValueError("Invalid embedding response")
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        resp = self.client.embed(model=self.model, input=[text])
        embeddings = resp.get("embeddings", [])
        if not embeddings:
            raise ValueError("Empty embedding response")
        return embeddings[0]
