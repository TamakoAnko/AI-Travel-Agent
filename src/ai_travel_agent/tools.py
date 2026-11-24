"""External tools used by the specialist agents."""

import logging

import httpx
from langchain_core.tools import tool

from .config import settings
from .rag import get_kb

logger = logging.getLogger(__name__)

WEATHER_CODES = {
    0: "晴", 1: "大部晴朗", 2: "多云", 3: "阴", 45: "雾", 48: "霜雾",
    51: "小毛毛雨", 53: "毛毛雨", 55: "强毛毛雨", 61: "小雨", 63: "中雨", 65: "大雨",
    71: "小雪", 73: "中雪", 75: "大雪", 80: "阵雨", 81: "强阵雨", 82: "暴雨",
    95: "雷暴", 96: "雷暴伴冰雹", 99: "强雷暴伴冰雹",
}


def web_search(query: str, max_results: int = 5) -> str:
    if not settings.tavily_api_key:
        return "搜索服务未配置（TAVILY_API_KEY 为空），请基于常识给出保守建议。"
    try:
        with httpx.Client(timeout=20) as client:
            resp = client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": settings.tavily_api_key,
                    "query": query,
                    "max_results": max_results,
                    "search_depth": "basic",
                    "include_answer": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()
        lines = [f"[搜索] {query}"]
        for item in data.get("results", [])[:max_results]:
            content = (item.get("content") or "").replace("\n", " ")[:400]
            lines.append(f"- {item.get('title', '')}\n  {content}\n  来源: {item.get('url', '')}")
        return "\n".join(lines) if len(lines) > 1 else "未搜索到结果。"
    except Exception as exc:
        logger.warning("Tavily 搜索失败: %s", exc)
        return f"搜索失败：{exc}"


def get_weather(city: str, start_date: str = "", days: int = 5) -> str:
    try:
        with httpx.Client(timeout=20) as client:
            geo = client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": city, "count": 1, "language": "zh", "format": "json"},
            ).json()
            results = geo.get("results") or []
            if not results:
                return f"未找到城市「{city}」的天气坐标。"
            loc = results[0]
            forecast_days = max(1, min(int(days), 7))
            forecast = client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": loc["latitude"],
                    "longitude": loc["longitude"],
                    "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code",
                    "timezone": "auto",
                    "forecast_days": forecast_days,
                },
            ).json()
        daily = forecast.get("daily") or {}
        dates = daily.get("time") or []
        if not dates:
            return f"未获取到「{city}」的天气预报。"
        lines = [f"[{loc.get('name', city)} 天气，未来 {len(dates)} 天]"]
        for i, day in enumerate(dates):
            code = (daily.get("weather_code") or [None])[i]
            lines.append(
                f"- {day}: {WEATHER_CODES.get(code, '未知')}，"
                f"{daily['temperature_2m_min'][i]}~{daily['temperature_2m_max'][i]}℃，"
                f"降水概率 {daily['precipitation_probability_max'][i]}%"
            )
        return "\n".join(lines)
    except Exception as exc:
        logger.warning("天气查询失败: %s", exc)
        return f"天气查询失败：{exc}"


def search_travel_knowledge(query: str, top_k: int = 4, city: str = "") -> str:
    try:
        results = get_kb().search(query, top_k=top_k, city=city or None)
    except Exception as exc:
        logger.warning("知识库检索失败: %s", exc)
        return f"知识库暂不可用：{exc}"
    if not results:
        return "知识库中没有找到相关内容。"
    blocks = [f"[知识库] {query}"]
    for item in results:
        where = item["source"] + (f" · {item['section']}" if item.get("section") else "")
        blocks.append(f"- 来源 {where}\n  {item['content'][:500]}")
    return "\n".join(blocks)


@tool
def web_search_tool(query: str) -> str:
    """搜索实时航班、酒店、景点、价格和攻略。查询应包含城市、日期和具体需求。"""
    return web_search(query)


@tool
def weather_tool(city: str, days: int = 5) -> str:
    """查询城市未来 1-7 天的天气预报和降水概率。"""
    return get_weather(city, days=days)


@tool
def knowledge_tool(query: str, city: str = "") -> str:
    """检索本地旅行知识库，获取目的地季节、区域、交通、美食和预算建议。city 填目的地中文名可提高准确率。"""
    return search_travel_knowledge(query, city=city)


TOOL_MAP = {
    "web_search_tool": web_search_tool,
    "weather_tool": weather_tool,
    "knowledge_tool": knowledge_tool,
}


def geocode_baidu(city: str, name: str) -> dict:
    if not settings.baidu_map_api_key:
        return {"name": name, "found": False}
    params = {
        "ak": settings.baidu_map_api_key,
        "output": "json",
        "address": name,
        "city": city,
    }
    try:
        with httpx.Client(timeout=8) as client:
            data = client.get("https://api.map.baidu.com/geocoding/v3/", params=params).json()
        if data.get("status") == 0:
            loc = (data.get("result") or {}).get("location") or {}
            if loc.get("lat") and loc.get("lng"):
                return {"name": name, "lat": loc["lat"], "lng": loc["lng"], "found": True}
    except Exception as exc:
        logger.warning("百度地理编码失败 %s: %s", name, exc)
    return {"name": name, "found": False}

