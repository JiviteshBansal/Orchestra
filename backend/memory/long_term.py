import os
import json
import logging
import numpy as np
from typing import Optional
from pathlib import Path

from backend.config import settings

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 384


class LongTermMemory:
    def __init__(self, store_path: Optional[str] = None):
        self.store_path = Path(store_path or settings.VECTOR_STORE_PATH)
        self.store_path.mkdir(parents=True, exist_ok=True)
        self._index = None
        self._documents: list[dict] = []
        self._embedder = None
        self._initialized = False

    def _ensure_initialized(self):
        if self._initialized:
            return

        try:
            import faiss
            self._index = faiss.IndexFlatL2(EMBEDDING_DIM)
            self._load_documents()
            self._initialized = True
            logger.info("FAISS vector store initialized")
        except ImportError:
            logger.warning("FAISS not available — long-term memory will use fallback text search")
            self._initialized = True

        try:
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer("all-MiniLM-L6-v2")
        except ImportError:
            logger.warning("sentence-transformers not available — embeddings disabled")

    def _embed(self, text: str) -> np.ndarray:
        if self._embedder:
            return self._embedder.encode([text])[0].astype("float32")
        return np.random.randn(EMBEDDING_DIM).astype("float32")

    def add(self, content: str, metadata: Optional[dict] = None) -> int:
        self._ensure_initialized()
        doc_id = len(self._documents)
        doc = {
            "id": doc_id,
            "content": content,
            "metadata": metadata or {},
        }
        self._documents.append(doc)

        if self._index is not None:
            vec = self._embed(content).reshape(1, -1)
            self._index.add(vec)

        self._save_documents()
        return doc_id

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        self._ensure_initialized()

        if self._index is not None and self._index.ntotal > 0:
            vec = self._embed(query).reshape(1, -1)
            k = min(top_k, self._index.ntotal)
            distances, indices = self._index.search(vec, k)
            results = []
            for i, idx in enumerate(indices[0]):
                if idx < len(self._documents):
                    doc = self._documents[idx].copy()
                    doc["score"] = float(distances[0][i])
                    results.append(doc)
            return results

        query_lower = query.lower()
        scored = []
        for doc in self._documents:
            content_lower = doc["content"].lower()
            if query_lower in content_lower:
                scored.append({**doc, "score": 1.0})
        return scored[:top_k]

    def get_all(self) -> list[dict]:
        self._ensure_initialized()
        return list(self._documents)

    def _save_documents(self):
        docs_path = self.store_path / "documents.json"
        with open(docs_path, "w") as f:
            json.dump(self._documents, f, indent=2)

    def _load_documents(self):
        docs_path = self.store_path / "documents.json"
        if docs_path.exists():
            with open(docs_path) as f:
                self._documents = json.load(f)
            if self._index is not None and self._documents:
                for doc in self._documents:
                    vec = self._embed(doc["content"]).reshape(1, -1)
                    self._index.add(vec)
            logger.info(f"Loaded {len(self._documents)} documents from store")


long_term_memory = LongTermMemory()
