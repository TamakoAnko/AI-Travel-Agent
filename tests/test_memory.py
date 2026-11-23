from langchain_core.messages import HumanMessage

from ai_travel_agent import agents
from ai_travel_agent.memory import ShortTermMemory
from ai_travel_agent.models import TripBrief, keep_recent_messages


def test_intake_does_not_duplicate_the_user_message(monkeypatch):
    brief = TripBrief(destination="巴黎", days=5)
    monkeypatch.setattr(agents, "extract_brief", lambda *args, **kwargs: brief)
    result = agents.intake_node({"request": "巴黎5天", "user_id": "u"})
    assert "messages" not in result
    assert result["stage"] == "trip_review"


def test_message_reducer_keeps_latest_20():
    messages = [HumanMessage(content=str(i)) for i in range(30)]
    merged = keep_recent_messages([], messages)
    assert len(merged) == 20
    assert merged[0].content == "10"


def test_short_term_memory_compression():
    mem = ShortTermMemory("test-compress")
    for i in range(12):
        mem.append("user", f"消息{i}")
    changed = mem.compress_if_needed(lambda old, previous: f"摘要({len(old)}) {previous}")
    assert changed
    assert len(mem.load()) == 6
    assert "摘要(6)" in mem.summary()
    assert "消息11" in mem.context()


def test_context_excludes_current_user_message():
    mem = ShortTermMemory("test-context")
    mem.append("user", "巴黎5天")
    mem.append("assistant", "已生成计划")
    mem.append("user", "改成3天")
    context = mem.context(exclude_last_user="改成3天")
    assert "改成3天" not in context
    assert "巴黎5天" in context
