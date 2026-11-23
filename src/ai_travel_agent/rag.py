"""Small, dependency-light RAG stack: LangChain splitters + pluggable embeddings + SQLite vectors."""

import hashlib
import json
import logging
import math
import re
from pathlib import Path
from typing import Protocol

import httpx
from langchain_text_splitters import RecursiveCharacterTextSplitter

from . import db
from .config import settings

logger = logging.getLogger(__name__)


class Embedder(Protocol):
    name: str
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class DashScopeEmbedder:
    """OpenAI-compatible DashScope embeddings."""

    def __init__(self) -> None:
        self.name = settings.embed_model
        self.dim = settings.embed_dim
        self.url = "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings"

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        headers = {"Authorization": f"Bearer {settings.dashscope_api_key}"}
        with httpx.Client(timeout=60) as client:
            for i in range(0, len(texts), 10):
                batch = texts[i : i + 10]
                resp = client.post(
                    self.url,
                    headers=headers,
                    json={
                        "model": self.name,
                        "input": batch,
                        "dimensions": self.dim,
                        "encoding_format": "float",
                    },
                )
                resp.raise_for_status()
                data = resp.json()["data"]
                vectors.extend(item["embedding"] for item in sorted(data, key=lambda x: x["index"]))
        return vectors


class OllamaEmbedder:
    def __init__(self) -> None:
        self.name = f"ollama:{settings.embed_model}"
        self.dim = settings.embed_dim
        self.base = settings.ollama_base_url.rstrip("/")

    def embed(self, texts: list[str]) -> list[list[float]]:
        with httpx.Client(timeout=120) as client:
            resp = client.post(
                f"{self.base}/api/embed",
                json={"model": settings.embed_model, "input": texts},
            )
            resp.raise_for_status()
            return resp.json()["embeddings"]


class HashEmbedder:
    """Offline fallback so the RAG pipeline is runnable without any API key.

    It is lexical, not semantic. Use DashScope/Ollama for real retrieval quality.
    """

    name = "hash-256"
    dim = 256

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._one(t) for t in texts]

    def _one(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        tokens = re.findall(r"[\u4e00-\u9fff]|[a-zA-Z0-9]+", text.lower())
        for token in tokens:
            idx = int(hashlib.md5(token.encode()).hexdigest(), 16) % self.dim
            vec[idx] += 1.0
        cjk = [t for t in tokens if len(t) == 1 and "\u4e00" <= t <= "\u9fff"]
        for a, b in zip(cjk, cjk[1:]):
            idx = int(hashlib.md5((a + b).encode()).hexdigest(), 16) % self.dim
            vec[idx] += 1.5
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]


def get_embedder() -> Embedder:
    provider = settings.embed_provider.lower()
    if provider == "dashscope" or (provider == "auto" and settings.dashscope_api_key):
        if not settings.dashscope_api_key:
            raise RuntimeError("EMBED_PROVIDER=dashscope 但 DASHSCOPE_API_KEY 为空")
        return DashScopeEmbedder()
    if provider == "ollama":
        return OllamaEmbedder()
    if provider == "auto":
        return HashEmbedder()
    if provider == "hash":
        return HashEmbedder()
    raise ValueError(f"未知 EMBED_PROVIDER: {provider}")


def cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


class KnowledgeBase:
    def __init__(self) -> None:
        self.embedder = get_embedder()
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=80,
            separators=["\n\n", "\n", "。", "；", " ", ""],
        )

    def count(self) -> int:
        with db.connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM rag_chunks WHERE model=?", (self.embedder.name,)
            ).fetchone()
        return int(row["n"])

    def ensure_seed(self, reset: bool = False) -> int:
        if not reset and self.count() > 0:
            return self.count()
        return self.ingest_dir(settings.knowledge_dir, reset=reset)

    def ingest_dir(self, directory: Path, reset: bool = False) -> int:
        files = sorted(Path(directory).glob("*.md")) + sorted(Path(directory).glob("*.txt"))
        if not files:
            logger.warning("知识库目录为空: %s", directory)
            return 0
        total = 0
        for path in files:
            text = path.read_text(encoding="utf-8")
            chunks = [c.strip() for c in self.splitter.split_text(text) if c.strip()]
            if not chunks:
                continue
            vectors = self.embedder.embed(chunks)
            source = path.name
            with db.connect() as conn:
                if reset:
                    conn.execute("DELETE FROM rag_chunks")
                conn.execute("DELETE FROM rag_chunks WHERE source=?", (source,))
                for i, (chunk, vec) in enumerate(zip(chunks, vectors)):
                    cid = hashlib.sha1(f"{source}:{i}:{chunk}".encode()).hexdigest()
                    conn.execute(
                        "INSERT OR REPLACE INTO rag_chunks"
                        "(id, source, chunk_index, content, embedding, model, updated_at) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            cid,
                            source,
                            i,
                            chunk,
                            json.dumps(vec),
                            self.embedder.name,
                            db.utc_now(),
                        ),
                    )
            total += len(chunks)
        logger.info("知识库索引完成: %s 个片段, 模型=%s", total, self.embedder.name)
        return total

    def search(self, query: str, top_k: int | None = None) -> list[dict]:
        if not query.strip() or self.count() == 0:
            return []
        qvec = self.embedder.embed([query])[0]
        with db.connect() as conn:
            rows = conn.execute(
                "SELECT source, chunk_index, content, embedding FROM rag_chunks WHERE model=?",
                (self.embedder.name,),
            ).fetchall()
        scored = []
        for row in rows:
            score = cosine(qvec, json.loads(row["embedding"]))
            if score > 0.05:
                scored.append(
                    {
                        "source": row["source"],
                        "chunk": row["chunk_index"],
                        "content": row["content"],
                        "score": round(score, 4),
                    }
                )
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[: (top_k or settings.rag_top_k)]


_kb: KnowledgeBase | None = None


def get_kb() -> KnowledgeBase:
    global _kb
    if _kb is None:
        _kb = KnowledgeBase()
    return _kb
