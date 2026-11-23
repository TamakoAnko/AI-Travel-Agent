import time

import pytest
from fastapi import HTTPException

from ai_travel_agent import auth, db


def test_token_roundtrip():
    token = auth.issue_token("13800138000")
    assert auth.verify_token(token) == "13800138000"
    assert auth.verify_token(token + "x") is None
    assert auth.verify_token("not-a-token") is None


def test_send_code_and_login():
    db.init_db()
    phone = "13900000001"
    code = auth.send_code(phone)
    assert len(code) == 6 and code.isdigit()
    with pytest.raises(HTTPException) as exc:
        auth.login(phone, "000000" if code != "000000" else "111111")
    assert exc.value.status_code == 401
    token, is_new = auth.login(phone, code)
    assert auth.verify_token(token) == phone
    assert isinstance(is_new, bool)


def test_otp_expiry():
    db.init_db()
    phone = "13900000002"
    code = auth.send_code(phone)
    row = db.get_otp(phone)
    db.save_otp(phone, row["code_hash"], time.time() - 1, row["created_at"])
    with pytest.raises(HTTPException):
        auth.login(phone, code)
