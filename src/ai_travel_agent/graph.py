"""Compile the multi-agent graph. Checkpointer is injected by the API lifespan."""

import logging

from langgraph.graph import END, START, StateGraph

from .agents import (
    approval_node,
    compose_node,
    finalize_node,
    flight_node,
    hotel_node,
    intake_node,
    itinerary_node,
    review_node,
    route_after_approval,
    route_after_review,
    weather_node,
)
from .models import TravelState

logger = logging.getLogger(__name__)


def build_graph(checkpointer=None):
    builder = StateGraph(TravelState)
    builder.add_node("intake", intake_node)
    builder.add_node("review", review_node)
    builder.add_node("flight", flight_node)
    builder.add_node("hotel", hotel_node)
    builder.add_node("itinerary", itinerary_node)
    builder.add_node("weather", weather_node)
    builder.add_node("compose", compose_node)
    builder.add_node("approval", approval_node)
    builder.add_node("finalize", finalize_node)

    builder.add_edge(START, "intake")
    builder.add_edge("intake", "review")
    builder.add_conditional_edges("review", route_after_review)
    for name in ("flight", "hotel", "itinerary", "weather"):
        builder.add_edge(name, "compose")
    builder.add_edge("compose", "approval")
    builder.add_conditional_edges("approval", route_after_approval)
    builder.add_edge("finalize", END)

    graph = builder.compile(checkpointer=checkpointer)
    logger.info("LangGraph 编译完成")
    return graph
