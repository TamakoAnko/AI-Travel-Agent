"""FastAPI API + SSE streaming compatible with the reused Vue frontend."""

import asyncio
import json
import logging
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from pydantic import BaseModel

from . import auth, db
from .agents import _text
from .config import settings
from .graph import build_graph
from . import memory
from .memory import ShortTermMemory, check_redis
from .models import (
    ApproveRequest,
    GeocodeBatchRequest,
    LoginRequest,
    RAGSearchRequest,
    SendCodeRequest,
)
from .prompts import NODE_LABELS
from .rag import get_kb
from .tools import geocode_baidu

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    if check_redis():
        logger.info("Redis: 连接成功")
    else:
        logger.warning("Redis: 不可用，登录和短期记忆将不可用")
    try:
        kb = get_kb()
        await asyncio.to_thread(kb.ensure_seed)
    except Exception as exc:
        logger.warning("知识库初始化失败（RAG 将降级）: %s", exc)

    stack = AsyncExitStack()
    try:
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

        saver = await stack.enter_async_context(
            AsyncSqliteSaver.from_conn_string(str(settings.checkpoint_path))
        )
        logger.info("Checkpointer: AsyncSqliteSaver(%s)", settings.checkpoint_path)
    except Exception as exc:
        logger.warning("SQLite checkpointer 不可用，降级内存: %s", exc)
        from langgraph.checkpoint.memory import InMemorySaver

        saver = InMemorySaver()

    app.state.graph = build_graph(saver)
    yield
    await stack.aclose()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _brief_preview(brief: dict) -> str:
    budget = f"￥{brief['budget']}" if brief.get("budget") else "未指定"
    prefs = "、".join(brief.get("preferences") or []) or "无特殊偏好"
    return (
        "### 行程信息确认\n\n"
        f"- 出发地：{brief.get('origin', '未指定')}\n"
        f"- 目的地：{brief.get('destination', '未指定')}\n"
        f"- 天数：{brief.get('days', 5)} 天\n"
        f"- 预算：{budget}\n"
        f"- 出行日期：{brief.get('start_date') or '未指定'}\n"
        f"- 人数：{brief.get('travelers', 1)} 人\n"
        f"- 偏好：{prefs}\n\n"
        "确认后将并行搜索航班、酒店、行程和天气；如果有误，请驳回并说明要改哪里。"
    )


def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}, "recursion_limit": 60}


async def _stream_events(graph, graph_input, config: dict, request: Request):
    seen = set()
    started = set()
    async for event in graph.astream_events(graph_input, config, version="v2"):
        if await request.is_disconnected():
            break
        kind = event.get("event")
        name = event.get("name", "")
        metadata = event.get("metadata") or {}
        node = metadata.get("langgraph_node") or (name if name in NODE_LABELS else "")
        if kind == "on_chain_start" and node in NODE_LABELS:
            if node in started:
                continue
            started.add(node)
            yield _sse({"type": "progress", "node": node, "content": NODE_LABELS[node]})
        elif kind == "on_chat_model_stream" and node == "compose":
            chunk = (event.get("data") or {}).get("chunk")
            text = _text(getattr(chunk, "content", ""))
            if text:
                yield _sse({"type": "message_token", "content": text})
        elif kind == "on_chain_end" and node in ("flight", "hotel", "itinerary", "weather"):
            if node in seen:
                continue
            seen.add(node)
            output = (event.get("data") or {}).get("output") or {}
            research = output.get("research") if isinstance(output, dict) else None
            if research:
                content = (research[-1] or {}).get("content", "")
                yield _sse(
                    {
                        "type": "thinking",
                        "node": node,
                        "content": f"{NODE_LABELS[node]} ✓\n{content[:500]}",
                    }
                )

    state = await graph.aget_state(config)
    stage = (state.values or {}).get("stage")
    if state.next:
        if stage == "trip_review":
            yield _sse(
                {
                    "type": "approval_required",
                    "hitl_stage": "trip_review",
                    "plan_preview": _brief_preview((state.values or {}).get("brief", {})),
                }
            )
        elif stage == "plan_approval":
            yield _sse(
                {
                    "type": "approval_required",
                    "hitl_stage": "plan_approval",
                    "plan_preview": (state.values or {}).get("plan", ""),
                }
            )
        else:
            yield _sse({"type": "error", "content": f"流程停在中途，stage={stage}"})
        return
    plan = (state.values or {}).get("plan", "")
    if plan:
        thread_id = (config.get("configurable") or {}).get("thread_id")
        try:
            mem = ShortTermMemory(thread_id)
            await asyncio.to_thread(mem.append, "assistant", plan)
            await asyncio.to_thread(mem.compress_if_needed)
        except Exception as exc:
            logger.warning("短期记忆写入/压缩失败: %s", exc)
        # 完成一轮后只保留最新 checkpoint，避免每个节点快照都堆在 SQLite 里
        try:
            checkpointer = getattr(graph, "checkpointer", None)
            if checkpointer and thread_id and hasattr(checkpointer, "aprune"):
                await checkpointer.aprune([thread_id], strategy="keep_latest")
        except Exception as exc:
            logger.warning("checkpoint 清理失败: %s", exc)
        yield _sse({"type": "complete", "content": plan})
    else:
        yield _sse({"type": "error", "content": "流程结束但没有生成计划"})


@app.get("/api/health")
async def health():
    kb = get_kb()
    return {
        "status": "healthy",
        "version": "0.1.0",
        "services": {
            "deepseek": bool(settings.deepseek_api_key),
            "tavily": bool(settings.tavily_api_key),
            "baidu_map": bool(settings.baidu_map_api_key),
            "redis": check_redis(),
            "short_term": check_redis(),
            "rag": kb.count() > 0,
            "rag_backend": getattr(kb, "backend_name", "unknown"),
            "embedding": kb.embedder.name,
        },
    }


@app.get("/api/status")
async def status():
    kb = get_kb()
    return {
        "deepseek": bool(settings.deepseek_api_key),
        "tavily": bool(settings.tavily_api_key),
        "baidu_map": bool(settings.baidu_map_api_key),
        "rag": kb.count() > 0,
        "checkpoint": True,
        "memory": True,
        "short_term": check_redis(),
        "embedding": kb.embedder.name,
        # 兼容复用前端的设置抽屉字段（语义分别是：会话记忆/用户画像/语义检索）
        "redis": check_redis(),
        "mysql": True,
        "milvus": kb.count() > 0,
    }


@app.post("/api/auth/send-code")
async def send_code(payload: SendCodeRequest):
    code = auth.send_code(payload.phone.strip())
    return {
        "status": "ok",
        "message": "验证码已发送（开发模式）",
        "dev_mode": True,
        "dev_code": code,
    }


@app.post("/api/auth/login")
async def login(payload: LoginRequest):
    token, is_new = auth.login(payload.phone.strip(), payload.code.strip())
    return {"token": token, "phone": payload.phone.strip(), "is_new_user": is_new}


@app.get("/api/auth/me")
async def me(current_user: str = Depends(auth.require_auth)):
    return {"phone": current_user, "user_id": current_user}


@app.post("/api/auth/logout")
async def logout(authorization: str = Header("")):
    auth.logout(authorization)
    return {"status": "ok"}


class FeedbackRequest(BaseModel):
    rating: int
    comment: str = ""


@app.post("/api/feedback/{thread_id}")
async def feedback(thread_id: str, payload: FeedbackRequest, current_user: str = Depends(auth.require_auth)):
    logger.info("feedback thread=%s user=%s rating=%s", thread_id, current_user, payload.rating)
    return {"status": "ok"}


async def _owns_thread(graph, user: str, thread_id: str) -> bool:
    if thread_id in memory.list_thread_ids(user):
        return True
    try:
        state = await graph.aget_state({"configurable": {"thread_id": thread_id}})
    except Exception:
        return False
    return (state.values or {}).get("user_id") == user


async def _drop_thread(graph, user_id: str, thread_id: str) -> None:
    """删掉一个会话的全部痕迹：Redis 索引、短期记忆、LangGraph 断点。"""
    await asyncio.to_thread(memory.forget_thread, user_id, thread_id)
    await asyncio.to_thread(memory.clear_thread, thread_id)
    checkpointer = getattr(graph, "checkpointer", None)
    if checkpointer is not None and hasattr(checkpointer, "adelete_thread"):
        try:
            await checkpointer.adelete_thread(thread_id)
        except Exception as exc:
            logger.warning("删除 checkpoint 失败: %s", exc)


@app.get("/api/threads")
async def threads(request: Request, current_user: str = Depends(auth.require_auth)):
    items = await asyncio.to_thread(memory.thread_summaries, memory.list_thread_ids(current_user))
    known = {i["thread_id"] for i in items}
    graph = request.app.state.graph
    # 兼容旧数据：没登记进索引的对话，按 checkpoint 里的 user_id 归属
    for tid in await asyncio.to_thread(memory.all_memory_threads):
        if tid in known:
            continue
        if await _owns_thread(graph, current_user, tid):
            items.extend(await asyncio.to_thread(memory.thread_summaries, [tid]))
    items.sort(key=lambda x: x["updated_at"], reverse=True)
    return {"items": items}


@app.get("/api/threads/{thread_id}/messages")
async def thread_messages(
    thread_id: str, request: Request, current_user: str = Depends(auth.require_auth)
):
    graph = request.app.state.graph
    if not await _owns_thread(graph, current_user, thread_id):
        raise HTTPException(404, "对话不存在")
    messages = await asyncio.to_thread(ShortTermMemory(thread_id).load)
    # 对话可能停在中途（等人工审批），把断点信息一起返回，前端才能恢复审批卡片
    pending = None
    state = await graph.aget_state({"configurable": {"thread_id": thread_id}})
    if state.next:
        values = state.values or {}
        stage = values.get("stage")
        if stage == "trip_review":
            pending = {"stage": stage, "preview": _brief_preview(values.get("brief", {}))}
        elif stage == "plan_approval":
            pending = {"stage": stage, "preview": values.get("plan", "")}
        else:
            pending = {"stage": stage or "", "preview": ""}
    return {"thread_id": thread_id, "messages": messages, "pending": pending}


@app.delete("/api/threads/{thread_id}")
async def delete_thread(
    thread_id: str, request: Request, current_user: str = Depends(auth.require_auth)
):
    if not await _owns_thread(request.app.state.graph, current_user, thread_id):
        raise HTTPException(404, "对话不存在")
    await _drop_thread(request.app.state.graph, current_user, thread_id)
    return {"status": "ok"}


@app.get("/api/trips")
async def trips(current_user: str = Depends(auth.require_auth)):
    return {"items": await asyncio.to_thread(db.list_trips, current_user)}


@app.delete("/api/trips/{trip_id}")
async def delete_trip(
    trip_id: int, request: Request, current_user: str = Depends(auth.require_auth)
):
    thread_id = await asyncio.to_thread(db.delete_trip, current_user, trip_id)
    if thread_id is None:
        raise HTTPException(404, "行程不存在")
    # 删行程时顺手删掉对应会话，避免「历史对话」里留一条已删行程的对话
    if thread_id:
        await _drop_thread(request.app.state.graph, current_user, thread_id)
    return {"status": "ok", "thread_deleted": bool(thread_id)}


@app.post("/api/rag/search")
async def rag_search(payload: RAGSearchRequest, current_user: str = Depends(auth.require_auth)):
    results = await asyncio.to_thread(
        get_kb().search, payload.query, payload.top_k, payload.city or None
    )
    return {"query": payload.query, "city": payload.city, "results": results}


@app.post("/api/baidu/geocode-batch")
async def geocode_batch(payload: GeocodeBatchRequest):
    names = list(dict.fromkeys(n.strip() for n in payload.names if n.strip()))[:20]
    if not names:
        return {"items": []}
    sem = asyncio.Semaphore(5)

    async def one(name: str):
        async with sem:
            return await asyncio.to_thread(geocode_baidu, payload.city, name)

    return {"items": await asyncio.gather(*(one(n) for n in names))}


@app.get("/api/stream/{thread_id}")
async def stream(
    thread_id: str,
    request: Request,
    message: str = Query(..., min_length=1),
    current_user: str = Depends(auth.require_auth),
):
    graph = request.app.state.graph
    config = _config(thread_id)
    state = await graph.aget_state(config)
    if state.values and state.values.get("user_id") != current_user:
        raise HTTPException(403, "无权访问该会话")
    if state.values and state.next:
        raise HTTPException(409, "该会话还有未处理的审批，请先确认或驳回")

    try:
        await asyncio.to_thread(memory.remember_thread, current_user, thread_id)
        await asyncio.to_thread(ShortTermMemory(thread_id).append, "user", message)
    except Exception as exc:
        logger.warning("写入短期记忆失败: %s", exc)

    initial = {
        "messages": [HumanMessage(content=message)],
        "user_id": current_user,
        "thread_id": thread_id,
        "request": message,
        "brief": {},
        "feedback": "",
        "research": [],
        "plan": "",
        "final": "",
        "stage": "intake",
    }
    return StreamingResponse(
        _stream_events(graph, initial, config, request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/stream/resume/{thread_id}")
async def resume(
    thread_id: str,
    request: Request,
    action: str = Query("approve"),
    feedback: str = Query(""),
    current_user: str = Depends(auth.require_auth),
):
    if action not in {"approve", "reject"}:
        raise HTTPException(400, "action 只能是 approve 或 reject")
    graph = request.app.state.graph
    config = _config(thread_id)
    state = await graph.aget_state(config)
    if not state.values:
        raise HTTPException(404, "未找到该会话")
    if state.values.get("user_id") != current_user:
        raise HTTPException(403, "无权访问该会话")
    if not state.next:
        raise HTTPException(409, "该会话没有待处理的审批")

    if action == "reject" and feedback:
        try:
            await asyncio.to_thread(
                ShortTermMemory(thread_id).append, "user", f"修改意见：{feedback}"
            )
        except Exception as exc:
            logger.warning("写入短期记忆失败: %s", exc)

    resume_value = {"action": action, "feedback": feedback if action == "reject" else ""}
    return StreamingResponse(
        _stream_events(graph, Command(resume=resume_value), config, request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )



