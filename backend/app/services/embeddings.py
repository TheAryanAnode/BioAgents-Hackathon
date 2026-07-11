"""Embedding + vector store abstraction with graceful fallbacks.

Embeddings use a deterministic hashing scheme (no network, no model download) so
the demo always has working semantic-ish retrieval. Chat and reports use Nebius
Token Factory; vector search stays local.

Order of preference for the vector store:
  1. ChromaDB (persistent, local).
  2. An in-memory numpy cosine store if Chroma is unavailable.
"""

from __future__ import annotations

import hashlib
import math
import os
import re
from typing import Optional

import numpy as np

from app.core.config import get_settings

# ChromaDB telemetry is incompatible with some posthog versions — disable it.
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_HASH_DIM = 384


def _hashing_embed(text: str, dim: int = _HASH_DIM) -> list[float]:
    """Cheap, deterministic bag-of-tokens hashing embedding (TF weighted)."""
    vec = np.zeros(dim, dtype=np.float32)
    tokens = _TOKEN_RE.findall(text.lower())
    if not tokens:
        return vec.tolist()
    for tok in tokens:
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if (h >> 8) % 2 == 0 else -1.0
        vec[idx] += sign
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec /= norm
    return vec.tolist()


class EmbeddingClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def mode(self) -> str:
        return "hashing"

    def embed(self, texts: list[str], *, interactive: bool = False) -> list[list[float]]:
        return [_hashing_embed(t) for t in texts]

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text], interactive=True)[0]


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


class _InMemoryStore:
    """Minimal numpy cosine store used when ChromaDB is unavailable."""

    def __init__(self) -> None:
        self.ids: list[str] = []
        self.vecs: list[np.ndarray] = []
        self.docs: list[str] = []
        self.metas: list[dict] = []

    def add(self, ids, embeddings, documents, metadatas) -> None:
        for i, e, d, m in zip(ids, embeddings, documents, metadatas):
            if i in self.ids:
                continue
            self.ids.append(i)
            self.vecs.append(np.array(e, dtype=np.float32))
            self.docs.append(d)
            self.metas.append(m)

    def query(self, embedding, n_results, where=None):
        q = np.array(embedding, dtype=np.float32)
        scored = []
        for idx, v in enumerate(self.vecs):
            if where and not all(self.metas[idx].get(k) == val for k, val in where.items()):
                continue
            scored.append((idx, _cosine(q, v)))
        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[:n_results]
        return {
            "ids": [[self.ids[i] for i, _ in top]],
            "documents": [[self.docs[i] for i, _ in top]],
            "metadatas": [[self.metas[i] for i, _ in top]],
            "distances": [[1 - s for _, s in top]],
        }


class VectorStore:
    """Per-corpus vector index. One logical collection per research session."""

    def __init__(self, embedder: EmbeddingClient) -> None:
        self.embedder = embedder
        self._chroma_client = None
        self._collections: dict[str, object] = {}
        self._memory: dict[str, _InMemoryStore] = {}
        try:
            import chromadb

            self._chroma_client = chromadb.Client()
        except Exception:
            self._chroma_client = None

    @property
    def backend(self) -> str:
        return "chromadb" if self._chroma_client else "in-memory"

    def _coll(self, corpus_id: str):
        key = f"corpus_{corpus_id}".replace("-", "_")
        if self._chroma_client:
            if key not in self._collections:
                self._collections[key] = self._chroma_client.get_or_create_collection(key)
            return self._collections[key]
        if key not in self._memory:
            self._memory[key] = _InMemoryStore()
        return self._memory[key]

    def add_chunks(
        self,
        corpus_id: str,
        paper_id: str,
        chunks: list[str],
        meta: dict,
    ) -> int:
        if not chunks:
            return 0
        coll = self._coll(corpus_id)
        embeddings = self.embedder.embed(chunks)
        ids = [f"{paper_id}::{i}" for i in range(len(chunks))]
        metadatas = [{**meta, "paper_id": paper_id, "chunk_index": i} for i in range(len(chunks))]
        coll.add(ids=ids, embeddings=embeddings, documents=chunks, metadatas=metadatas)
        return len(chunks)

    def search(self, corpus_id: str, query: str, k: int = 8, where: Optional[dict] = None):
        coll = self._coll(corpus_id)
        q = self.embedder.embed_one(query)
        try:
            res = coll.query(query_embeddings=[q], n_results=k, where=where)  # type: ignore[arg-type]
        except TypeError:
            res = coll.query(embedding=q, n_results=k, where=where)  # in-memory signature
        hits = []
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        dists = res.get("distances", [[]])[0]
        for doc, meta, dist in zip(docs, metas, dists):
            relevance = max(0.0, 1.0 - float(dist))
            hits.append({"document": doc, "meta": meta, "relevance": relevance})
        return hits
