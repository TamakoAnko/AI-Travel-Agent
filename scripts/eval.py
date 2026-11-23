import asyncio
import json
import time
from pathlib import Path

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from ai_travel_agent import db
from ai_travel_agent.graph import build_graph
from ai_travel_agent.prompts import plan_is_valid

CASES = Path(__file__).resolve().parent.parent / "eval" / "cases.json"


async def run_case(graph, case: dict) -> dict:
    thread_id = f"eval-{case['id']}"
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 60}
    initial = {
        "messages": [HumanMessage(content=case["request"])],
        "user_id": "eval-user",
        "thread_id": thread_id,
        "request": case["request"],
        "brief": {},
        "feedback": "",
        "research": [],
        "plan": "",
        "final": "",
        "stage": "intake",
    }
    started = time.perf_counter()
    await graph.ainvoke(initial, config)
    await graph.ainvoke(Command(resume={"action": "approve"}), config)
    state = await graph.ainvoke(Command(resume={"action": "approve"}), config)
    elapsed = time.perf_counter() - started
    plan = state.get("plan", "")
    days = state.get("brief", {}).get("days", 5)
    checks = {
        "destination": case["destination"] in plan,
        "days": plan_is_valid(plan, days),
        "budget": "## 预算汇总" in plan,
        "weather": "天气" in plan or "℃" in plan,
    }
    return {"id": case["id"], "elapsed": elapsed, "passed": all(checks.values()), **checks}


async def main() -> None:
    db.init_db()
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    graph = build_graph(InMemorySaver())
    results = []
    for case in cases:
        print(f"running {case['id']} ...", flush=True)
        try:
            results.append(await run_case(graph, case))
        except Exception as exc:
            results.append({"id": case["id"], "passed": False, "error": str(exc), "elapsed": 0})
    print("\nid\tpassed\tlatency\tdestination\tdays\tbudget\tweather")
    for r in results:
        print(
            f"{r['id']}\t{r.get('passed')}\t{r.get('elapsed', 0):.1f}s\t"
            f"{r.get('destination')}\t{r.get('days')}\t{r.get('budget')}\t{r.get('weather')}"
        )
    passed = sum(1 for r in results if r.get("passed"))
    print(f"\npassed {passed}/{len(results)}")


if __name__ == "__main__":
    asyncio.run(main())
