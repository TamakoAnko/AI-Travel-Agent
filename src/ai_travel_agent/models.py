from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


def merge_research(left: list[dict] | None, right: list[dict] | None) -> list[dict]:
    """Append specialist output, but allow intake to clear the previous turn."""
    right = right or []
    if right and isinstance(right[0], dict) and right[0].get("_reset"):
        return right[1:]
    return (left or []) + right


MAX_MESSAGES = 20


def keep_recent_messages(left: list | None, right: list | None) -> list:
    """Keep the checkpoint small: only the latest 20 messages are retained."""
    merged = add_messages(left or [], right or [])
    return merged[-MAX_MESSAGES:]


class TripBrief(BaseModel):
    origin: str = Field("未指定", description="出发城市，未提及则填未指定")
    destination: str = Field(..., description="目的地城市")
    days: int = Field(5, ge=1, le=30, description="旅行天数")
    budget: int | None = Field(None, description="总预算，人民币元；未提及则为 null")
    start_date: str | None = Field(None, description="出发日期，YYYY-MM-DD；未提及则为 null")
    travelers: int = Field(1, ge=1, le=20, description="出行人数")
    preferences: list[str] = Field(default_factory=list, description="兴趣偏好关键词")
    summary: str = Field("", description="一句话概括用户需求")


class SendCodeRequest(BaseModel):
    phone: str


class LoginRequest(BaseModel):
    phone: str
    code: str


class ApproveRequest(BaseModel):
    action: str
    feedback: str = ""


class GeocodeBatchRequest(BaseModel):
    city: str = ""
    names: list[str] = Field(default_factory=list)


class RAGSearchRequest(BaseModel):
    query: str
    top_k: int = 4


class TravelState(TypedDict):
    messages: Annotated[list[BaseMessage], keep_recent_messages]
    user_id: str
    thread_id: str
    request: str
    brief: dict
    feedback: str
    research: Annotated[list[dict], merge_research]
    plan: str
    final: str
    stage: str


