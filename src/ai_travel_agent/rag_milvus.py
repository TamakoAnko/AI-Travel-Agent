"""LlamaIndex + Milvus 检索后端。

与 rag.KnowledgeBase 保持同一接口：count() / ensure_seed() / search()。
"""

import hashlib
import logging
from pathlib import Path

from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.llms import MockLLM
from llama_index.core.retrievers import QueryFusionRetriever, VectorIndexRetriever
from llama_index.core.schema import TextNode
from llama_index.core.vector_stores import MetadataFilter, MetadataFilters
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.vector_stores.milvus import MilvusVectorStore
from pymilvus import MilvusClient

from .config import settings
from .rag import city_of, get_embedder, split_document

logger = logging.getLogger(__name__)

FUSION_MODE = "reciprocal_rerank"  # RRF：只看名次，不看分数量纲


class ProjectEmbedding(BaseEmbedding):
    """把项目已有的 Embedder（DashScope / Ollama / hash）适配给 LlamaIndex。"""

    def __init__(self, embedder) -> None:
        super().__init__()
        self._embedder = embedder

    def _get_text_embedding(self, text: str):
        return self._embedder.embed([text])[0]

    def _get_query_embedding(self, query: str):
        return self._embedder.embed([query])[0]

    async def _aget_text_embedding(self, text: str):
        return self._get_text_embedding(text)

    async def _aget_query_embedding(self, query: str):
        return self._get_query_embedding(query)


def build_nodes(directory: Path) -> list[TextNode]:
    """复用 run:split_document 的章节切分，转成带 city/section 元数据的 LlamaIndex 节点。"""
    nodes: list[TextNode] = []
    files = sorted(Path(directory).glob("*.md")) + sorted(Path(directory).glob("*.txt"))
    for path in files:
        city = city_of(path.name)
        parts = split_document(path.read_text(encoding="utf-8"))
        for i, (section, chunk) in enumerate(parts):
            nodes.append(
                TextNode(
                    text=chunk,
                    id_=hashlib.sha1(f"{path.name}:{section}:{i}:{chunk}".encode()).hexdigest(),
                    metadata={"source": path.name, "city": city, "section": section},
                )
            )
    return nodes


class MilvusKnowledgeBase:
    backend_name = "milvus"

    def __init__(self) -> None:
        self.embedder = get_embedder()
        safe_name = "".join(c if (c.isalnum() or c == "_") else "_" for c in self.embedder.name)
        self.collection = f"{settings.milvus_collection}_{safe_name}"
        self.client = MilvusClient(uri=settings.milvus_uri, timeout=10)
        self.nodes = build_nodes(settings.knowledge_dir)
        self.vector_store = self._make_store()
        self._index: VectorStoreIndex | None = None
        self._loaded = False

    def _make_store(self) -> MilvusVectorStore:
        # overwrite=False 时集成会先 describe 一个不存在的集合而报错，首次创建必须 overwrite=True
        exists = self.collection in self.client.list_collections()
        return MilvusVectorStore(
            uri=settings.milvus_uri,
            collection_name=self.collection,
            dim=self.embedder.dim,
            similarity_metric="COSINE",
            overwrite=not exists,
        )

    def _ensure_loaded(self) -> None:
        if self._loaded or self.collection not in self.client.list_collections():
            return
        try:
            self.client.load_collection(self.collection)
            self._loaded = True
        except Exception as exc:
            logger.warning("Milvus load_collection 失败: %s", exc)

    def count(self) -> int:
        if self.collection not in self.client.list_collections():
            return 0
        try:
            stats = self.client.get_collection_stats(self.collection)
            return int(stats.get("row_count", 0))
        except Exception:
            return 0

    def ensure_seed(self, reset: bool = False) -> int:
        if reset and self.collection in self.client.list_collections():
            self.client.drop_collection(self.collection)
            self.vector_store = self._make_store()
            self._index = None
            self._loaded = False
        if self.count() == 0:
            logger.info("Milvus 集合为空，写入 %s 个节点", len(self.nodes))
            VectorStoreIndex(
                self.nodes,
                storage_context=StorageContext.from_defaults(vector_store=self.vector_store),
                embed_model=ProjectEmbedding(self.embedder),
                show_progress=False,
            )
            self.client.flush(self.collection)
        self._ensure_loaded()
        return self.count()

    def _get_index(self) -> VectorStoreIndex:
        if self._index is None:
            self._index = VectorStoreIndex.from_vector_store(
                vector_store=self.vector_store,
                embed_model=ProjectEmbedding(self.embedder),
            )
        return self._index

    def search(
        self,
        query: str,
        top_k: int | None = None,
        city: str | None = None,
        mode: str = "hybrid",
    ) -> list[dict]:
        top_k = top_k or settings.rag_top_k
        if not query.strip() or self.count() == 0:
            return []
        self._ensure_loaded()
        filters = (
            MetadataFilters(filters=[MetadataFilter(key="city", value=city)]) if city else None
        )
        vector_retriever = VectorIndexRetriever(
            index=self._get_index(), similarity_top_k=20, filters=filters
        )
        if mode == "vector":
            retriever = vector_retriever
        else:
            nodes = [n for n in self.nodes if not city or n.metadata.get("city") == city]
            pool = nodes or self.nodes
            bm25 = BM25Retriever.from_defaults(
                nodes=pool, similarity_top_k=min(20, len(pool))
            )
            retriever = QueryFusionRetriever(
                [vector_retriever, bm25],
                llm=MockLLM(max_tokens=1),  # num_queries=1 时不会真正调用，只为避免解析默认 OpenAI
                similarity_top_k=top_k,
                num_queries=1,
                mode=FUSION_MODE,
                use_async=False,
            )
        return [
            {
                "source": res.node.metadata.get("source", ""),
                "city": res.node.metadata.get("city", ""),
                "section": res.node.metadata.get("section", ""),
                "content": res.node.get_content(),
                "score": round(float(res.score or 0.0), 4),
            }
            for res in retriever.retrieve(query)[:top_k]
        ]
