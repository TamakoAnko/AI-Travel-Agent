"""Demo-grade phone + OTP auth. No SMS provider: the code is returned in dev mode."""

import base64
import hashlib
import hmac
import re
import secrets
import time

from fastapi import Header, HTTPException

from . import db
from .config import settings

PHONE_PATTERN = r"^1[3-9]\d{9}$"
OTP_TTL = 5 * 60
RESEND_SECONDS = 60


def _code_hash(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def send_code(phone: str) -> str:
    if not re.match(PHONE_PATTERN, phone):
        raise HTTPException(400, "手机号格式不正确")
    row = db.get_otp(phone)
    if row and time.time() - row["created_at"] < RESEND_SECONDS:
        raise HTTPException(429, f"发送过于频繁，请 {int(RESEND_SECONDS - (time.time() - row['created_at']))} 秒后重试")
    code = f"{secrets.randbelow(1_000_000):06d}"
    now = time.time()
    db.save_otp(phone, _code_hash(code), now + OTP_TTL, now)
    return code


def login(phone: str, code: str) -> tuple[str, bool]:
    row = db.get_otp(phone)
    if not row or row["expires_at"] < time.time():
        raise HTTPException(401, "验证码错误或已过期")
    if not hmac.compare_digest(row["code_hash"], _code_hash(code)):
        raise HTTPException(401, "验证码错误或已过期")
    db.delete_otp(phone)
    is_new = db.upsert_user(phone)
    return issue_token(phone), is_new


def issue_token(phone: str) -> str:
    exp = int(time.time()) + 30 * 24 * 3600
    payload = f"{phone}.{exp}"
    sig = hmac.new(settings.app_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=") + "." + sig


def verify_token(token: str) -> str | None:
    try:
        payload_b64, sig = token.split(".", 1)
        payload = base64.urlsafe_b64decode(payload_b64 + "=" * (-len(payload_b64) % 4)).decode()
        phone, exp = payload.split(".", 1)
        expected = hmac.new(settings.app_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        if int(exp) < time.time() or not re.match(PHONE_PATTERN, phone):
            return None
        return phone
    except Exception:
        return None


def require_auth(authorization: str = Header("")) -> str:
    token = authorization.removeprefix("Bearer ").strip()
    phone = verify_token(token)
    if not phone:
        raise HTTPException(401, "未登录或登录已过期")
    return phone

