from langchain_core.messages import HumanMessage

from ai_travel_agent import agents
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
