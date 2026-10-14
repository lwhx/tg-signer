import asyncio
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from pyrogram import errors

from backend.app.auth import AuthFlow, AuthManager
from backend.app.schemas import Check2FA, SendCode, SignIn
from backend.app.security import attempts


@pytest.fixture
def auth_flow(monkeypatch):
    attempts.clear()
    manager = AuthManager()
    client = SimpleNamespace(
        sign_in=AsyncMock(),
        check_password=AsyncMock(),
        resend_code=AsyncMock(return_value=SimpleNamespace(phone_code_hash="new-hash")),
        is_connected=False,
        is_initialized=False,
    )
    spec = SendCode(phone="+8613800000000", api_id=1234, api_hash="a" * 32)
    flow = AuthFlow(client=client, spec=spec, code_hash="hash")
    manager.flows["flow"] = flow
    monkeypatch.setattr("backend.app.auth.persist_account", AsyncMock(return_value=42))
    return manager, client, flow


async def test_login_2fa_and_success(auth_flow):
    manager, client, flow = auth_flow
    client.sign_in.side_effect = errors.SessionPasswordNeeded()
    result = await manager.sign_in(SignIn(flow_id="flow", code="12345", phone_code_hash="hash"))
    assert result["status"] == "2FA_REQUIRED"
    assert flow.state == "2FA_REQUIRED"
    with pytest.raises(HTTPException) as error:
        await manager.sign_in(SignIn(flow_id="flow", code="12345", phone_code_hash="hash"))
    assert error.value.status_code == 409
    client.check_password.side_effect = errors.PasswordHashInvalid()
    with pytest.raises(HTTPException) as error:
        await manager.check_2fa(Check2FA(flow_id="flow", password="incorrect"))
    assert error.value.status_code == 400
    assert flow.state == "2FA_REQUIRED"
    client.check_password.side_effect = None
    result = await manager.check_2fa(Check2FA(flow_id="flow", password="correct"))
    assert result == {"status": "AUTHORIZED", "account_id": 42}
    assert "flow" not in manager.flows


async def test_invalid_code_remains_retryable(auth_flow):
    manager, client, flow = auth_flow
    client.sign_in.side_effect = errors.PhoneCodeInvalid()
    with pytest.raises(HTTPException) as error:
        await manager.sign_in(SignIn(flow_id="flow", code="12345", phone_code_hash="hash"))
    assert error.value.status_code == 400
    assert flow.state == "CODE_SENT"
    client.sign_in.side_effect = None
    client.sign_in.return_value = SimpleNamespace(id=123)
    assert (await manager.sign_in(SignIn(flow_id="flow", code="12345", phone_code_hash="hash")))[
        "status"
    ] == "AUTHORIZED"


async def test_expiration_and_attempt_limit(auth_flow):
    manager, client, flow = auth_flow
    flow.attempts = 8
    with pytest.raises(HTTPException) as error:
        manager.get("flow", "CODE_SENT")
    assert error.value.status_code == 429
    flow.created = time.monotonic() - 601
    with pytest.raises(HTTPException) as error:
        manager.get("flow", "CODE_SENT")
    assert error.value.status_code == 410
    await manager.cleanup()
    assert not manager.flows


async def test_resend_rotates_hash_and_enforces_cooldown(auth_flow):
    manager, client, flow = auth_flow
    spec = SendCode(phone="+8613800000000", flow_id="flow")
    with pytest.raises(HTTPException) as error:
        await manager.send(spec)
    assert error.value.status_code == 429
    flow.sent -= 61
    result = await manager.send(spec)
    assert result["phone_code_hash"] == "new-hash"
    with pytest.raises(HTTPException) as error:
        await manager.sign_in(SignIn(flow_id="flow", code="12345", phone_code_hash="hash"))
    assert error.value.status_code == 409
    client.sign_in.assert_not_awaited()


async def test_concurrent_submit_only_commits_once(auth_flow):
    manager, client, flow = auth_flow
    client.sign_in.return_value = SimpleNamespace(id=123)
    data = SignIn(flow_id="flow", code="12345", phone_code_hash="hash")
    results = await asyncio.gather(
        manager.sign_in(data), manager.sign_in(data), return_exceptions=True
    )
    assert sum(isinstance(r, dict) for r in results) == 1
    assert client.sign_in.await_count == 1


async def test_floodwait_and_cancel(auth_flow):
    manager, client, flow = auth_flow
    client.sign_in.side_effect = errors.FloodWait(30)
    with pytest.raises(HTTPException) as error:
        await manager.sign_in(SignIn(flow_id="flow", code="12345", phone_code_hash="hash"))
    assert error.value.status_code == 429
    assert error.value.headers["Retry-After"] == "30"
    await manager.cancel("flow")
    assert not manager.flows
