"""Redis-backed login state and short-term conversation memory.

Redis is used for:
- OTP codes and login tokens (revocable on logout)
- per-thread conversation buffer + rolling summary

SQLite remains the source of truth for users, long-term trips and RAG vectors.
"""

import json
import logging
import time
from typing import Callable

from .config import settings

logger = logging.getLogger(__name__)

_client = None


def get_redis():
    global _client
    if _client is not None:
        return _client
    if settings.redis_fake:
        import fakeredis

        _client = fakeredis.FakeRedis(decode_responses=True)
        return _client
    import redis

    client = redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        password=settings.redis_password or None,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_keepalive=True,
    )
    try:
        client.ping()
    except Exception:
        client.close()
        raise
    _client = client
    return _client


def reset_redis_client() -> None:
    global _client
    _client = None


def check_redis() -> bool:
    try:
        return bool(get_redis().ping())
    except Exception:
        return False


def _fallback_summary(messages: list[dict], previous: str) -> str:
    lines = [previous] if previous else []
    for message in messages:
        role = "用户" if message.get("role") == "user" else "助手"
        text = (message.get("content") or "").replace("\n", " ")[:160]
        lines.append(f"{role}: {text}")
    return "\n".join(lines)[-settings.short_term_summary_chars :]


def _llm_summary(messages: list[dict], previous: str) -> str:
    """Compress old turns with the same DeepSeek model; fall back to text truncation."""
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        from .agents import _llm, _text

        transcript = "\n".join(
            f"{'用户' if m.get('role') == 'user' else '助手'}: {(m.get('content') or '')[:800]}"
            for m in messages
        )
        prompt = (
            "把下面的旅行对话压缩成不超过 300 字的中文摘要。"
            "保留目的地、天数、预算、偏好、已经确认的决定和用户的修改意见；不要编造。\n\n"
            f"已有摘要：{previous or '无'}\n\n旧对话：\n{transcript}"
        )
        response = _llm(settings.sub_agent_model, 0.1).invoke(
            [
                SystemMessage(content="你是对话压缩器，只输出摘要正文。"),
                HumanMessage(content=prompt),
            ]
        )
        return _text(response.content).strip() or _fallback_summary(messages, previous)
    except Exception as exc:
        logger.warning("短期记忆压缩 LLM 失败，使用文本兜底: %s", exc)
        return _fallback_summary(messages, previous)


class ShortTermMemory:
    """Per-thread Redis list with a rolling summary.

    Keys:
      travel:chat:{thread_id}:messages  -> list of JSON messages
      travel:chat:{thread_id}:summary   -> compressed older turns
    """

    def __init__(self, thread_id: str) -> None:
        self.thread_id = thread_id
        self.key = f"travel:chat:{thread_id}:messages"
        self.summary_key = f"travel:chat:{thread_id}:summary"

    def append(self, role: str, content: str) -> None:
        r = get_redis()
        payload = json.dumps(
            {"role": role, "content": content, "ts": time.time()}, ensure_ascii=False
        )
        r.rpush(self.key, payload)
        self._expire()

    def load(self) -> list[dict]:
        r = get_redis()
        return [json.loads(item) for item in r.lrange(self.key, 0, -1)]

    def summary(self) -> str:
        return get_redis().get(self.summary_key) or ""

    def _expire(self) -> None:
        r = get_redis()
        r.expire(self.key, settings.short_term_ttl)
        if r.exists(self.summary_key):
            r.expire(self.summary_key, settings.short_term_ttl)

    def context(self, exclude_last_user: str | None = None) -> str:
        """Format summary + recent turns for prompt injection."""
        messages = self.load()
        if (
            exclude_last_user
            and messages
            and messages[-1].get("role") == "user"
            and (messages[-1].get("content") or "").strip() == exclude_last_user.strip()
        ):
            messages = messages[:-1]
        summary = self.summary()
        recent = messages[-settings.short_term_keep_messages :]
        lines = []
        if summary:
            lines.append(f"历史摘要：{summary}")
        for message in recent:
            content = (message.get("content") or "").strip()
            if len(content) > 600:
                content = content[:600] + "..."
            role = "用户" if message.get("role") == "user" else "助手"
            lines.append(f"{role}：{content}")
        return "\n".join(lines)[-2500:]

    def compress_if_needed(
        self, summarizer: Callable[[list[dict], str], str] | None = None
    ) -> bool:
        """When the list hits the limit, summarize old turns and keep only recent ones."""
        r = get_redis()
        total = r.llen(self.key)
        if total < settings.short_term_max_messages:
            return False
        messages = self.load()
        keep = max(1, settings.short_term_keep_messages)
        old = messages[:-keep]
        if not old:
            return False
        previous = self.summary()
        summary = (summarizer or _llm_summary)(old, previous)
        r.set(
            self.summary_key,
            summary[: settings.short_term_summary_chars],
            ex=settings.short_term_ttl,
        )
        r.ltrim(self.key, -keep, -1)
        self._expire()
        logger.info(
            "短期记忆压缩 thread=%s: %s 条 -> %s 条", self.thread_id, total, keep
        )
        return True
