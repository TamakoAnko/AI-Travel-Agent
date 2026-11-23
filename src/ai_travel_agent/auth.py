"""Redis-backed OTP login and revocable opaque tokens."""

import hashlib
import hmac
import re
import secrets

from fastapi import Header, HTTPException

from . import db
from .memory import get_redis

PHONE_PATTERN = r"^1[3-9]\d{9}$"
OTP_TTL = 5 * 60
RESEND_SECONDS = 60
TOKEN_TTL = 30 * 24 * 3600

CODE_KEY = "sms:login:{phone}"
COOLDOWN_KEY = "sms:cooldown:{phone}"
TOKEN_KEY = "auth:token:{token}"


def _code_hash(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def _redis():
    try:
        return get_redis()
    except Exception as exc:
        raise HTTPException(503, f"Redis 未连接，登录/鉴权不可用：{exc}") from exc


def send_code(phone: str) -> str:
    if not re.match(PHONE_PATTERN, phone):
        raise HTTPException(400, "手机号格式不正确")
    r = _redis()
    cooldown = COOLDOWN_KEY.format(phone=phone)
    ttl = r.ttl(cooldown)
    if ttl and ttl > 0:
        raise HTTPException(429, f"发送过于频繁，请 {ttl} 秒后重试")
    code = f"{secrets.randbelow(1_000_000):06d}"
    r.setex(CODE_KEY.format(phone=phone), OTP_TTL, _code_hash(code))
    r.setex(cooldown, RESEND_SECONDS, "1")
    return code


def issue_token(phone: str) -> str:
    token = secrets.token_hex(32)
    _redis().setex(TOKEN_KEY.format(token=token), TOKEN_TTL, phone)
    return token


def login(phone: str, code: str) -> tuple[str, bool]:
    r = _redis()
    key = CODE_KEY.format(phone=phone)
    saved = r.get(key)
    if not saved or not hmac.compare_digest(saved, _code_hash(code)):
        raise HTTPException(401, "验证码错误或已过期")
    r.delete(key)
    is_new = db.upsert_user(phone)
    return issue_token(phone), is_new


def extract_bearer(authorization: str) -> str:
    return authorization.removeprefix("Bearer ").strip()


def get_phone_by_token(token: str) -> str | None:
    if not token:
        return None
    try:
        return _redis().get(TOKEN_KEY.format(token=token))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, f"Redis 鉴权服务不可用：{exc}") from exc


def require_auth(authorization: str = Header("")) -> str:
    phone = get_phone_by_token(extract_bearer(authorization))
    if not phone:
        raise HTTPException(401, "未登录或登录已过期")
    return phone


def logout(authorization: str) -> None:
    token = extract_bearer(authorization)
    if token:
        _redis().delete(TOKEN_KEY.format(token=token))
