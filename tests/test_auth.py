import pytest
from fastapi import HTTPException

from ai_travel_agent import auth, db
from ai_travel_agent.memory import get_redis


def test_send_code_and_login():
    db.init_db()
    phone = "13900000001"
    code = auth.send_code(phone)
    assert len(code) == 6 and code.isdigit()
    with pytest.raises(HTTPException) as exc:
        auth.login(phone, "000000" if code != "000000" else "111111")
    assert exc.value.status_code == 401
    token, is_new = auth.login(phone, code)
    assert auth.get_phone_by_token(token) == phone
    assert isinstance(is_new, bool)


def test_logout_revokes_token():
    db.init_db()
    phone = "13900000004"
    code = auth.send_code(phone)
    token, _ = auth.login(phone, code)
    assert auth.get_phone_by_token(token) == phone
    auth.logout(f"Bearer {token}")
    assert auth.get_phone_by_token(token) is None


def test_send_code_cooldown():
    phone = "13900000005"
    auth.send_code(phone)
    with pytest.raises(HTTPException) as exc:
        auth.send_code(phone)
    assert exc.value.status_code == 429


def test_otp_expiry():
    phone = "13900000002"
    code = auth.send_code(phone)
    get_redis().delete(f"sms:login:{phone}")
    with pytest.raises(HTTPException):
        auth.login(phone, code)
