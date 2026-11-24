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


CITY_BY_FILE = {
    "paris": "巴黎", "tokyo": "东京", "bangkok": "曼谷", "rome": "罗马",
    "bali": "巴厘岛", "newyork": "纽约", "beijing": "北京", "shanghai": "上海",
}
HEADING_RE = re.compile(r"^(#{1,3})\s+(.+?)\s*$", re.M)


def city_of(source: str) -> str:
    stem = Path(source).stem.lower()
    return CITY_BY_FILE.get(stem, Path(source).stem)


def tokenize(text: str) -> list[str]:
    """中文按单字 + 二元组切，英文数字按词切；不引额外分词依赖。"""
    tokens = re.findall(r"[\u4e00-\u9fff]|[a-zA-Z0-9]+", text.lower())
    cjk = [t for t in tokens if len(t) == 1 and "\u4e00" <= t <= "\u9fff"]
    return tokens + [a + b for a, b in zip(cjk, cjk[1:])]


def bm25_scores(query: str, docs: list[str], k1: float = 1.5, b: float = 0.75) -> list[float]:
    """朴素 BM25：补上向量检索对精确词（门票、地铁、预约）不敏感的短板。"""
    if not docs:
        return []
    tokenized = [tokenize(d) for d in docs]
    avgdl = sum(len(t) for t in tokenized) / len(tokenized) or 1.0
    df: dict[str, int] = {}
    for tokens in tokenized:
        for term in set(tokens):
            df[term] = df.get(term, 0) + 1
    n = len(docs)
    q_terms = set(tokenize(query))
    scores = []
    for tokens in tokenized:
        tf: dict[str, int] = {}
        for term in tokens:
            tf[term] = tf.get(term, 0) + 1
        score = 0.0
        for term in q_terms:
            freq = tf.get(term, 0)
            if not freq:
                continue
            idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
            score += idf * freq * (k1 + 1) / (freq + k1 * (1 - b + b * len(tokens) / avgdl))
        scores.append(score)
    return scores


def rrf_fuse(rankings: list[list[int]], k: int = 60) -> dict[int, float]:
    """倒数排名融合：只看名次不看分数，避免向量相似度和 BM25 分数量纲不同。"""
    fused: dict[int, float] = {}
    for ranking in rankings:
        for rank, idx in enumerate(ranking, start=1):
            fused[idx] = fused.get(idx, 0.0) + 1.0 / (k + rank)
    return fused


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

    def split_document(self, text: str) -> list[tuple[str, str]]:
        """先按 Markdown 二级标题切主题，再在主题内按长度切，返回 [(section, chunk)]。"""
        matches = list(HEADING_RE.finditer(text))
        if not matches:
            return [("", c.strip()) for c in self.splitter.split_text(text) if c.strip()]
        parts: list[tuple[str, str]] = []
        for i, m in enumerate(matches):
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            section = m.group(2).strip()
            body = text[m.end():end].strip()
            if not body:
                continue
            for chunk in self.splitter.split_text(body):
                if chunk.strip():
                    parts.append((section, chunk.strip()))
        return parts

    def ingest_dir(self, directory: Path, reset: bool = False) -> int:
        files = sorted(Path(directory).glob("*.md")) + sorted(Path(directory).glob("*.txt"))
        if not files:
            logger.warning("知识库目录为空: %s", directory)
            return 0
        if reset:
            with db.connect() as conn:
                conn.execute("DELETE FROM rag_chunks")
        total = 0
        for path in files:
            text = path.read_text(encoding="utf-8")
            city = city_of(path.name)
            parts = self.split_document(text)
            if not parts:
                continue
            # 带城市和主题前缀做 embedding，提升「某城市某主题」的召回
            inputs = [f"{city} {section}\n{chunk}".strip() for section, chunk in parts]
            vectors = self.embedder.embed(inputs)
            source = path.name
            with db.connect() as conn:
                conn.execute("DELETE FROM rag_chunks WHERE source=?", (source,))
                for i, ((section, chunk), vec) in enumerate(zip(parts, vectors)):
                    cid = hashlib.sha1(f"{source}:{section}:{i}:{chunk}".encode()).hexdigest()
                    conn.execute(
                        "INSERT OR REPLACE INTO rag_chunks"
                        "(id, source, chunk_index, city, section, content, embedding, model, updated_at) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            cid,
                            source,
                            i,
                            city,
                            section,
                            chunk,
                            json.dumps(vec),
                            self.embedder.name,
                            db.utc_now(),
                        ),
                    )
            total += len(parts)
        logger.info("知识库索引完成: %s 个片段, 模型=%s", total, self.embedder.name)
        return total

    def search(
        self,
        query: str,
        top_k: int | None = None,
        city: str | None = None,
        mode: str = "hybrid",
    ) -> list[dict]:
        """mode=hybrid：向量 + BM25 排名融合；mode=vector：仅向量（原实现，用于对比）。"""
        if not query.strip() or self.count() == 0:
            return []
        top_k = top_k or settings.rag_top_k
        qvec = self.embedder.embed([query])[0]
        with db.connect() as conn:
            rows = conn.execute(
                "SELECT source, chunk_index, city, section, content, embedding "
                "FROM rag_chunks WHERE model=?",
                (self.embedder.name,),
            ).fetchall()
        if city:
            scoped = [r for r in rows if r["city"] == city]
            rows = scoped or rows  # 城市没命中时退回全库，避免召回为空
        if not rows:
            return []

        vec_scores = [cosine(qvec, json.loads(r["embedding"])) for r in rows]
        if mode == "vector":
            order = sorted(range(len(rows)), key=lambda i: vec_scores[i], reverse=True)
            picked = [(i, vec_scores[i]) for i in order if vec_scores[i] > 0.05][:top_k]
        else:
            docs = [f"{r['city']} {r['section']} {r['content']}" for r in rows]
            lex_scores = bm25_scores(query, docs)
            vec_rank = sorted(range(len(rows)), key=lambda i: vec_scores[i], reverse=True)
            lex_rank = sorted(range(len(rows)), key=lambda i: lex_scores[i], reverse=True)
            fused = rrf_fuse([vec_rank, lex_rank])
            picked = sorted(fused.items(), key=lambda kv: kv[1], reverse=True)[:top_k]

        return [
            {
                "source": rows[i]["source"],
                "chunk": rows[i]["chunk_index"],
                "city": rows[i]["city"],
                "section": rows[i]["section"],
                "content": rows[i]["content"],
                "score": round(float(score), 4),
            }
            for i, score in picked
        ]


_kb: KnowledgeBase | None = None


def get_kb() -> KnowledgeBase:
    global _kb
    if _kb is None:
        _kb = KnowledgeBase()
    return _kb
