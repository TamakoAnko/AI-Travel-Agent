import json
import re
from datetime import date


PLAN_FORMAT = """输出严格的 Markdown，结构必须如下（不要输出 JSON，不要省略 DAY 标题）：
# {origin} → {destination} · {days}天旅行计划

出发地：{origin}
目的地：{destination}
天数：{days}天
预算：{budget}
出行时间：{start_date}
偏好：{preferences}

## 行程总览
2-3 句话概括路线、节奏和亮点。

## DAY 1 · 当日主题
- **上午（9:00-12:00）**：[景点名] —— 具体活动和理由（门票约￥X）
- **午餐（12:00-13:30）**：[餐厅或区域] | 菜系/特色 | 人均约￥X
- **下午（14:00-17:30）**：[景点名] —— 具体活动（门票约￥X）
- **晚上（18:30-21:00）**：[活动或餐厅] —— 具体安排
- **当日贴士**：交通、预约、避坑提醒

## DAY 2 · 当日主题
（同上格式，每天一组，直到 DAY {days}）

## 交通建议
出发地到目的地、机场到市区、市内交通，写清耗时和大致费用。

## 住宿建议
按经济/舒适两档给区域和价格区间，说明为什么选这个区域。

## 美食推荐
5-8 个具体菜品或餐厅类型，标注人均价格。

## 预算汇总
| 类别 | 说明 | 金额 |
| 交通 | 往返机票/火车+市内交通 | ￥X |
| 住宿 | {days}晚 | ￥X |
| 餐饮 | 每日约￥X | ￥X |
| 门票 | 主要景点 | ￥X |
| 其他 | 购物/保险/机动 | ￥X |
| 总计 | 合计 | ￥X |

## 实用贴士
天气与穿衣、预约、安全、支付、网络等 4-6 条。

硬性要求：
1. 每个 DAY 必须使用 `## DAY N · 主题` 标题，且从 DAY 1 连续编号到 DAY {days}。
2. 每个 DAY 至少包含上午、午餐、下午、晚上四条，景点名放在方括号里。
3. 预算汇总必须是 Markdown 表格，金额用 `￥数字`。
4. 结合天气研究和知识库内容，不要编造具体营业时间；不确定的信息标注“以官方为准”。
5. 全文使用中文，控制在 1200-2200 字。"""


def build_intake_prompt(request: str, recent: list[dict], feedback: str = "") -> str:
    today = date.today().isoformat()
    context = ""
    if recent:
        context = "\n用户最近的行程（仅作偏好参考，不要照抄）：\n" + json.dumps(
            [r["brief"] for r in recent], ensure_ascii=False
        )
    extra = f"\n上一次用户驳回并给出的修改意见：{feedback}\n" if feedback else ""
    return f"""今天是 {today}。从用户需求中提取旅行信息。
用户需求：{request}{extra}{context}

规则：
- 用户没说的字段不要编造：出发地填“未指定”，预算填 null，日期填 null。
- “1.5万”“两万”要换算成 15000、20000。
- 偏好提取为简短关键词，如“美食”“博物馆”“亲子”“不想太累”。
- 目的地必须是明确城市或地区。"""


SPECIALIST_PROMPTS = {
    "flight": """你是航班与城际交通专家。先用 web_search_tool 搜索出发地到目的地的航班或火车选择，再给出 2-3 个方案。
输出 150-250 字：直飞/中转、航空公司或车次类型、价格区间、耗时、订票提醒。没有实时数据时明确说明是估算。""",
    "hotel": """你是住宿专家。先用 web_search_tool 搜索目的地住宿区域和价格，再给出经济型、舒适型各 2 个区域建议。
输出 150-250 字：区域、适合人群、每晚价格区间、交通便利性、预订提醒。""",
    "itinerary": """你是行程规划专家。必须先调用 knowledge_tool 检索目的地知识，再用 web_search_tool 补充 2-3 个具体景点或餐厅。
输出 250-400 字：按天给出路线骨架，每天 3-4 个点，考虑地理顺序和节奏，标注门票/人均价格。不要写预算汇总。""",
    "weather": """你是天气与穿衣顾问。必须先调用 weather_tool 查询目的地未来天气。
输出 100-180 字：温度区间、降水、穿衣建议、需要带的东西、对行程的影响。""",
}

NODE_LABELS = {
    "intake": "正在理解你的旅行需求",
    "review": "等待你确认行程信息",
    "flight": "正在搜索航班与城际交通",
    "hotel": "正在筛选住宿区域",
    "itinerary": "正在检索知识库并编排每日行程",
    "weather": "正在查询目的地天气",
    "compose": "正在汇总生成完整旅行计划",
    "approval": "等待你审批最终方案",
    "finalize": "正在保存行程",
}


def build_compose_prompt(brief: dict, research: list[dict], feedback: str = "", previous_plan: str = "") -> str:
    sections = "\n\n".join(f"### {r.get('agent')}\n{r.get('content')}" for r in research)
    revision = ""
    if feedback:
        revision = f"\n用户对上一版方案的修改意见：{feedback}\n上一版方案：\n{previous_plan[:3000]}\n请针对意见修改。\n"
    return PLAN_FORMAT.format(
        origin=brief.get("origin", "未指定"),
        destination=brief.get("destination", ""),
        days=brief.get("days", 5),
        budget=f"￥{brief['budget']}" if brief.get("budget") else "未指定（请给出合理估算）",
        start_date=brief.get("start_date") or "未指定",
        preferences="、".join(brief.get("preferences") or []) or "无特殊偏好",
    ) + f"\n\n以下是四位专家的研究结果，请整合，不要逐条复制：\n{sections}{revision}"


def plan_is_valid(md: str, days: int | None = None) -> bool:
    if not md or "## 预算汇总" not in md:
        return False
    day_numbers = [int(n) for n in re.findall(r"^#{1,4}\s*DAY\s*(\d{1,2})", md, re.I | re.M)]
    if not day_numbers or day_numbers[0] != 1:
        return False
    if days and days <= 10 and len(day_numbers) < days:
        return False
    if days and days <= 10 and day_numbers != list(range(1, days + 1)):
        return False
    return "|" in md

