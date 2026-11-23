from pathlib import Path

from ai_travel_agent import db
from ai_travel_agent.rag import HashEmbedder, KnowledgeBase, cosine


def test_hash_embedder_is_deterministic():
    emb = HashEmbedder()
    a = emb.embed(["巴黎 博物馆 艺术"])[0]
    b = emb.embed(["巴黎 博物馆 艺术"])[0]
    assert a == b
    assert cosine(a, a) == 1.0


def test_ingest_and_search(tmp_path: Path):
    db.init_db()
    kb = KnowledgeBase()
    kb.embedder = HashEmbedder()
    doc = tmp_path / "rag_test.md"
    doc.write_text("# 测试目的地\n京都适合秋天看红叶，清水寺和岚山是热门景点。\n\n预算每天约 12000 日元。", encoding="utf-8")
    kb.ingest_dir(tmp_path)
    results = kb.search("京都 红叶 预算", top_k=2)
    assert results
    assert "京都" in results[0]["content"]


def test_empty_query():
    kb = KnowledgeBase()
    assert kb.search("") == []
