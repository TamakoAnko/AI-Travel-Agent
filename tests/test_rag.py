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


def test_structured_chunks_carry_city_and_section(tmp_path: Path):
    db.init_db()
    kb = KnowledgeBase()
    kb.embedder = HashEmbedder()
    doc = tmp_path / "paris.md"
    doc.write_text(
        "# 巴黎旅行知识\n\n## 交通\n地铁覆盖密集，建议买 Navigo Easy。\n\n## 美食\n可颂和洋葱汤，午市套餐约 18-28 欧元。",
        encoding="utf-8",
    )
    kb.ingest_dir(tmp_path)
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT city, section FROM rag_chunks WHERE source='paris.md'"
        ).fetchall()
    assert {r["section"] for r in rows} == {"交通", "美食"}
    assert all(r["city"] == "巴黎" for r in rows)


def test_city_filter_limits_results(tmp_path: Path):
    db.init_db()
    kb = KnowledgeBase()
    kb.embedder = HashEmbedder()
    (tmp_path / "paris.md").write_text("# 巴黎\n\n## 交通\n地铁和 RER 进城。", encoding="utf-8")
    (tmp_path / "tokyo.md").write_text("# 东京\n\n## 交通\n地铁和 JR 进城。", encoding="utf-8")
    kb.ingest_dir(tmp_path)
    results = kb.search("地铁 怎么坐", top_k=5, city="东京")
    assert results
    assert all(r["city"] == "东京" for r in results)


def test_hybrid_mode_returns_section(tmp_path: Path):
    db.init_db()
    kb = KnowledgeBase()
    kb.embedder = HashEmbedder()
    (tmp_path / "paris.md").write_text(
        "# 巴黎\n\n## 交通\n地铁按天买票更划算。\n\n## 美食\n午市套餐人均 18-28 欧元。",
        encoding="utf-8",
    )
    kb.ingest_dir(tmp_path)
    results = kb.search("午市套餐人均多少欧元", top_k=3, mode="hybrid")
    assert results
    assert results[0]["section"] == "美食"
