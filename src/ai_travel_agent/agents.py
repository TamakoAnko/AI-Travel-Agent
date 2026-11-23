"""LangGraph nodes: supervisor intake, four parallel specialists, compose, HITL."""

import json
import logging
import re
from functools import lru_cache

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.types import Send, interrupt

from . import db
from .config import settings
from .models import TripBrief
from .prompts import SPECIALIST_PROMPTS, build_compose_prompt, build_intake_prompt, plan_is_valid
from .tools import TOOL_MAP, knowledge_tool, weather_tool, web_search_tool

logger = logging.getLogger(__name__)

CITY_HINTS = [
    "巴黎", "东京", "京都", "大阪", "罗马", "佛罗伦萨", "威尼斯", "米兰", "伦敦", "纽约",
    "曼谷", "新加坡", "北京", "上海", "杭州", "成都", "三亚", "大理", "丽江", "青岛",
    "厦门", "西安", "重庆", "广州", "深圳", "香港", "澳门", "台北", "巴厘岛", "迪拜",
    "悉尼", "墨尔本", "洛杉矶", "旧金山", "巴塞罗那", "马德里", "阿姆斯特丹", "布拉格",
]


@lru_cache(maxsize=8)
def _llm(model: str, temperature: float) -> ChatDeepSeek:
    if not settings.deepseek_api_key:
        raise RuntimeError("DEEPSEEK_API_KEY 未配置，无法调用大模型")
    return ChatDeepSeek(
        model=model,
        api_key=settings.deepseek_api_key,
        api_base=settings.deepseek_base_url,
        temperature=temperature,
        max_tokens=4096,
        timeout=120,
        max_retries=2,
    )


def _text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(item.get("text", ""))
            else:
                parts.append(str(item))
        return "".join(parts)
    return str(content or "")


def _json_object(text: str) -> dict:
    match = re.search(r"\{[\s\S]*\}", text or "")
    if not match:
        raise ValueError("模型未返回 JSON")
    return json.loads(match.group(0))


def heuristic_brief(request: str) -> TripBrief:
    destination = next((c for c in CITY_HINTS if c in request), "未指定")
    origin_match = re.search(r"从([\u4e00-\u9fff]{2,8})(?:出发|去|到)", request)
    days_match = re.search(r"(\d{1,2})\s*天", request)
    budget_match = re.search(r"预算[^\d]{0,8}(\d+(?:\.\d+)?)\s*(万)?", request)
    budget = None
    if budget_match:
        budget = int(float(budget_match.group(1)) * (10000 if budget_match.group(2) else 1))
    return TripBrief(
        origin=origin_match.group(1) if origin_match else "未指定",
        destination=destination,
        days=int(days_match.group(1)) if days_match else 5,
        budget=budget,
        start_date=None,
        preferences=[],
        summary=request[:80],
    )


def extract_brief(request: str, user_id: str, feedback: str = "") -> TripBrief:
    recent = db.recent_trips(user_id, limit=2)
    prompt = build_intake_prompt(request, recent, feedback)
    messages = [SystemMessage(content="你是旅行需求结构化专家。"), HumanMessage(content=prompt)]
    try:
        structured = _llm(settings.supervisor_model, 0.1).with_structured_output(TripBrief)
        result = structured.invoke(messages)
        return result if isinstance(result, TripBrief) else TripBrief(**result)
    except Exception as exc:
        logger.warning("结构化提取失败，降级 JSON 解析: %s", exc)
    try:
        raw = _llm(settings.supervisor_model, 0.1).invoke(
            [*messages, HumanMessage(content="只输出一个 JSON 对象，不要 Markdown 代码块。")]
        )
        return TripBrief(**_json_object(_text(raw.content)))
    except Exception as exc:
        logger.warning("JSON 提取失败，使用正则兜底: %s", exc)
        return heuristic_brief(request)


def intake_node(state: dict) -> dict:
    brief = extract_brief(state["request"], state.get("user_id", ""), state.get("feedback", ""))
    return {
        "brief": brief.model_dump(),
        "stage": "trip_review",
        "research": [{"_reset": True}],
        "messages": [HumanMessage(content=state["request"])],
    }


def review_node(state: dict) -> dict:
    decision = interrupt({"stage": "trip_review", "brief": state["brief"]})
    decision = decision or {}
    if decision.get("action", "approve") == "approve":
        return {"stage": "research", "feedback": ""}
    return {"stage": "intake", "feedback": decision.get("feedback", "用户希望修改行程信息")}


def route_after_review(state: dict):
    if state.get("stage") == "intake":
        return "intake"
    return [Send("flight", state), Send("hotel", state), Send("itinerary", state), Send("weather", state)]


def _run_tool_agent(system: str, task: str, tools: list, max_steps: int = 3) -> str:
    llm = _llm(settings.sub_agent_model, 0.1).bind_tools(tools)
    messages = [SystemMessage(content=system), HumanMessage(content=task)]
    response = llm.invoke(messages)
    for _ in range(max_steps):
        calls = getattr(response, "tool_calls", None) or []
        if not calls:
            break
        messages.append(response)
        for call in calls:
            fn = TOOL_MAP.get(call.get("name", ""))
            try:
                result = fn.invoke(call.get("args") or {}) if fn else f"未知工具 {call.get('name')}"
            except Exception as exc:
                result = f"工具执行失败：{exc}"
            messages.append(ToolMessage(content=str(result), tool_call_id=call.get("id", "")))
        response = llm.invoke(messages)
    return _text(response.content)


def _brief_task(state: dict) -> str:
    brief = state.get("brief", {})
    return (
        f"用户需求：{state.get('request', '')}\n"
        f"结构化信息：{json.dumps(brief, ensure_ascii=False)}\n"
        "请完成你的专业任务，只输出结论，不要输出工具调用过程。"
    )


def _specialist(name: str, tools: list):
    def node(state: dict) -> dict:
        try:
            content = _run_tool_agent(SPECIALIST_PROMPTS[name], _brief_task(state), tools)
        except Exception as exc:
            logger.exception("子 Agent %s 执行失败", name)
            content = f"⚠️ {name} 子 Agent 执行失败：{exc}"
        return {"research": [{"agent": name, "content": content}]}

    node.__name__ = f"{name}_node"
    return node


def flight_node(state: dict) -> dict:
    return _specialist("flight", [web_search_tool])(state)


def hotel_node(state: dict) -> dict:
    return _specialist("hotel", [web_search_tool])(state)


def itinerary_node(state: dict) -> dict:
    return _specialist("itinerary", [knowledge_tool, web_search_tool])(state)


def weather_node(state: dict) -> dict:
    return _specialist("weather", [weather_tool])(state)


def _stream_text(llm, messages: list) -> str:
    parts = []
    for chunk in llm.stream(messages):
        text = _text(chunk.content)
        if text:
            parts.append(text)
    return "".join(parts)


def compose_node(state: dict) -> dict:
    brief = state.get("brief", {})
    research = state.get("research", [])
    feedback = state.get("feedback", "")
    prompt = build_compose_prompt(brief, research, feedback, state.get("plan", ""))
    system = SystemMessage(content="你是旅行规划主编，负责把多位专家的结论整合成一份可执行的 Markdown 行程。")
    llm = _llm(settings.supervisor_model, 0.3)
    plan = _stream_text(llm, [system, HumanMessage(content=prompt)])
    days = int(brief.get("days", 5))
    if not plan_is_valid(plan, days):
        logger.warning("计划格式不完整，重试一次")
        retry = prompt + (
            "\n\n上一次输出不合格：缺少连续的 DAY 标题或预算汇总表。"
            "请重新输出完整 Markdown，必须从 DAY 1 连续到 DAY "
            f"{days}，并包含 ## 预算汇总 表格。"
        )
        plan = _stream_text(llm, [system, HumanMessage(content=retry)])
    return {"plan": plan, "stage": "plan_approval"}


def approval_node(state: dict) -> dict:
    decision = interrupt({"stage": "plan_approval", "plan": state.get("plan", "")})
    decision = decision or {}
    if decision.get("action", "approve") == "approve":
        return {"stage": "final"}
    return {"stage": "compose", "feedback": decision.get("feedback", "用户希望调整计划")}


def route_after_approval(state: dict):
    return "finalize" if state.get("stage") == "final" else "compose"


def finalize_node(state: dict) -> dict:
    try:
        db.save_trip(
            state.get("user_id", ""),
            state.get("thread_id", ""),
            state.get("brief", {}),
            state.get("plan", ""),
        )
    except Exception as exc:
        logger.warning("保存行程失败: %s", exc)
    return {"stage": "done", "final": state.get("plan", "")}


