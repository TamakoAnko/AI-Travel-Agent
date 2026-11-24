"""检索评测：Recall@3 / MRR@5 / 章节命中率。

用法：
  uv run python scripts/eval_rag.py            # 默认按当前实现检索
  uv run python scripts/eval_rag.py --mode vector
  uv run python scripts/eval_rag.py --compare  # vector 与 hybrid 各跑一遍
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ai_travel_agent.rag import city_of, get_kb

CASES = Path(__file__).resolve().parent.parent / "eval" / "retrieval_cases.json"
TOP_K = 5


def run(kb, cases, mode: str, use_city: bool = True) -> dict:
    hits3 = 0
    section_hits3 = 0
    rr = 0.0
    misses = []
    for case in cases:
        # 和生产一致：Agent 会带上目的地城市做过滤
        city = city_of(case["source"]) if use_city else None
        results = kb.search(case["query"], top_k=TOP_K, city=city, mode=mode)
        rank = None
        section_rank = None
        for i, item in enumerate(results, start=1):
            if item["source"] != case["source"]:
                continue
            if rank is None:
                rank = i
            if section_rank is None and case.get("section") and item.get("section") == case["section"]:
                section_rank = i
        if rank:
            hits3 += 1 if rank <= 3 else 0
            rr += 1 / rank
        if section_rank and section_rank <= 3:
            section_hits3 += 1
        if not rank or not section_rank or section_rank > 3:
            misses.append((case["query"], case["source"], case.get("section"), rank, section_rank))
    n = len(cases)
    return {
        "mode": mode,
        "doc_recall_at_3": round(hits3 / n, 3),
        "mrr_at_5": round(rr / n, 3),
        "section_hit_at_3": round(section_hits3 / n, 3),
        "misses": misses,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="hybrid", choices=["hybrid", "vector"])
    parser.add_argument("--compare", action="store_true")
    parser.add_argument("--no-city", action="store_true", help="不做城市过滤（对比用）")
    args = parser.parse_args()

    kb = get_kb()
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    print(f"用例 {len(cases)} 条，知识片段 {kb.count()} 个，embedding={kb.embedder.name}\n")

    modes = ["vector", "hybrid"] if args.compare else [args.mode]
    for mode in modes:
        stats = run(kb, cases, mode, use_city=not args.no_city)
        print(
            f"[{mode:6}] doc Recall@3={stats['doc_recall_at_3']:.3f}  "
            f"MRR@5={stats['mrr_at_5']:.3f}  章节命中@3={stats['section_hit_at_3']:.3f}"
        )
        for q, src, sec, r, sr in stats["misses"]:
            print(f"    miss: {q} 期望 {src}/{sec} 文档排名={r} 章节排名={sr}")
        print()


if __name__ == "__main__":
    main()
