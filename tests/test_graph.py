from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

from ai_travel_agent.agents import route_after_approval, route_after_review
from ai_travel_agent.graph import build_graph


def test_graph_compiles():
    graph = build_graph(InMemorySaver())
    names = set(graph.get_graph().nodes)
    assert {"intake", "review", "flight", "hotel", "itinerary", "weather", "compose", "approval", "finalize"} <= names


def test_route_after_review_returns_parallel_sends():
    result = route_after_review({"stage": "research", "request": "x", "brief": {}, "user_id": "u"})
    assert len(result) == 4
    assert {send.node for send in result} == {"flight", "hotel", "itinerary", "weather"}


def test_route_after_review_back_to_intake():
    assert route_after_review({"stage": "intake"}) == "intake"


def test_route_after_approval():
    assert route_after_approval({"stage": "final"}) == "finalize"
    assert route_after_approval({"stage": "compose"}) == "compose"
