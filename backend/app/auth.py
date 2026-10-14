"""Bounded, expiring Telegram authentication state machine; never calls start()."""

import asyncio
import base64
import secrets
import time
from dataclasses import dataclass, field

from fastapi import HTTPException
from pyrogram import Client, errors
from sqlalchemy import select
from tg_signer.core import get_api_config, get_proxy

from .db import Account, Session, get_setting, now
from .schemas import SendCode
from .security import decrypt, encrypt, rate_limit


async def disconnect(client):
    try:
        if client.is_initialized:
            await client.terminate()
        if client.is_connected:
            await client.disconnect()
    except (ConnectionError, OSError):
        pass


def telegram_error(exc):
    if isinstance(exc, errors.FloodWait):
        return HTTPException(
            429,
            f"Telegram 要求等待 {exc.value} 秒",
            headers={"Retry-After": str(exc.value)},
        )
    mapping = {
        "PhoneCodeInvalid": "验证码错误",
        "PhoneCodeExpired": "验证码已过期，请重新发送",
        "PasswordHashInvalid": "二步验证密码错误",
        "PhoneNumberInvalid": "手机号格式错误",
        "PhoneNumberBanned": "此手机号已被 Telegram 封禁",
        "ApiIdInvalid": "API_ID 或 API_HASH 无效",
        "AuthKeyUnregistered": "Session 已失效，请重新登录",
        "SessionRevoked": "Session 已被撤销",
    }
    return HTTPException(
        400, mapping.get(type(exc).__name__, f"Telegram 请求失败：{type(exc).__name__}")
    )


async def persist_account(client, spec):
    me = await client.get_me()
    if me.is_bot:
        raise HTTPException(400, "请导入 Telegram 用户账号 Session")
    session_string = await client.export_session_string()
    avatar = ""
    if me.photo:
        try:
            async with asyncio.timeout(10):
                stream = await client.download_media(me.photo.small_file_id, in_memory=True)
                if stream:
                    avatar = (
                        "data:image/jpeg;base64," + base64.b64encode(stream.getvalue()).decode()
                    )
        except Exception:
            pass
    with Session() as db:
        account = db.scalar(select(Account).where(Account.user_id == str(me.id)))
        if not account:
            account = Account(user_id=str(me.id))
            db.add(account)
        account.name = spec.name or me.first_name or str(me.id)
        account.phone = "+" + (me.phone_number or spec.phone).lstrip("+")
        account.username = me.username or ""
        account.session = encrypt(session_string)
        account.api_id = spec.api_id
        account.api_hash = encrypt(spec.api_hash)
        account.proxy = encrypt(spec.proxy)
        account.avatar = avatar
        account.status = "online"
        account.last_checked = now()
        db.commit()
        return account.id


@dataclass
class AuthFlow:
    client: Client
    spec: SendCode
    state: str = "CODE_SENT"
    code_hash: str = ""
    created: float = field(default_factory=time.monotonic)
    sent: float = field(default_factory=time.monotonic)
    attempts: int = 0
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class AuthManager:
    def __init__(self):
        self.flows: dict[str, AuthFlow] = {}
        self.send_lock = asyncio.Lock()

    async def cleanup(self):
        for key, flow in list(self.flows.items()):
            if time.monotonic() - flow.created > 600 and not flow.lock.locked():
                await self.cancel(key)

    async def cancel(self, key):
        flow = self.flows.get(key)
        if flow:
            async with flow.lock:
                self.flows.pop(key, None)
                await disconnect(flow.client)

    def get(self, key, state):
        flow = self.flows.get(key)
        if not flow or time.monotonic() - flow.created > 600:
            raise HTTPException(410, "登录流程已过期，请重新开始")
        if flow.state != state:
            raise HTTPException(409, "当前登录步骤不匹配")
        if flow.attempts >= 8:
            raise HTTPException(429, "验证次数过多，请重新开始")
        return flow

    async def send(self, spec):
        async with self.send_lock:
            await self.cleanup()
            rate_limit("tg:" + spec.phone, limit=5, window=600)
            if spec.flow_id:
                flow = self.get(spec.flow_id, "CODE_SENT")
                async with flow.lock:
                    self.get(spec.flow_id, "CODE_SENT")
                    if time.monotonic() - flow.sent < 60:
                        raise HTTPException(429, "请等待 60 秒再重发验证码")
                    try:
                        async with asyncio.timeout(45):
                            result = await flow.client.resend_code(flow.spec.phone, flow.code_hash)
                        flow.code_hash, flow.sent = (
                            result.phone_code_hash,
                            time.monotonic(),
                        )
                        return self.payload(spec.flow_id, flow)
                    except errors.RPCError as exc:
                        raise telegram_error(exc) from exc
            if len(self.flows) >= 20:
                raise HTTPException(429, "待完成的登录流程过多")
            if not spec.api_id:
                spec.api_id, spec.api_hash = get_api_config()
            proxy = spec.proxy or decrypt(get_setting("global_proxy"))
            client = Client(
                "auth-" + secrets.token_hex(8),
                api_id=spec.api_id,
                api_hash=spec.api_hash,
                in_memory=True,
                proxy=get_proxy(proxy),
                no_updates=True,
            )
            try:
                async with asyncio.timeout(45):
                    await client.connect()
                    result = await client.send_code(spec.phone)
                flow = AuthFlow(client=client, spec=spec, code_hash=result.phone_code_hash)
                key = secrets.token_urlsafe(32)
                self.flows[key] = flow
                return self.payload(key, flow)
            except BaseException as exc:
                await disconnect(client)
                if isinstance(exc, errors.RPCError):
                    raise telegram_error(exc) from exc
                raise

    @staticmethod
    def payload(key, flow):
        return {
            "flow_id": key,
            "status": flow.state,
            "phone_code_hash": flow.code_hash,
            "resend_after": 60,
            "expires_in": max(0, int(600 - time.monotonic() + flow.created)),
        }

    async def finish(self, key, flow):
        account_id = await persist_account(flow.client, flow.spec)
        flow.state = "AUTHORIZED"
        self.flows.pop(key, None)
        await disconnect(flow.client)
        return {"status": "AUTHORIZED", "account_id": account_id}

    async def sign_in(self, data):
        flow = self.get(data.flow_id, "CODE_SENT")
        async with flow.lock:
            self.get(data.flow_id, "CODE_SENT")
            if not secrets.compare_digest(flow.code_hash, data.phone_code_hash):
                raise HTTPException(409, "验证码流程已更新，请使用最新验证码")
            flow.attempts += 1
            try:
                async with asyncio.timeout(45):
                    user = await flow.client.sign_in(flow.spec.phone, flow.code_hash, data.code)
                    if not hasattr(user, "id"):
                        raise HTTPException(400, "此手机号尚未注册，请先在 Telegram 客户端注册")
                    return await self.finish(data.flow_id, flow)
            except errors.SessionPasswordNeeded:
                flow.state = "2FA_REQUIRED"
                return {"status": "2FA_REQUIRED", "flow_id": data.flow_id}
            except errors.RPCError as exc:
                if isinstance(exc, errors.PhoneCodeExpired):
                    flow.created = 0
                raise telegram_error(exc) from exc

    async def check_2fa(self, data):
        flow = self.get(data.flow_id, "2FA_REQUIRED")
        async with flow.lock:
            self.get(data.flow_id, "2FA_REQUIRED")
            flow.attempts += 1
            try:
                async with asyncio.timeout(45):
                    await flow.client.check_password(data.password)
                    return await self.finish(data.flow_id, flow)
            except errors.RPCError as exc:
                raise telegram_error(exc) from exc


auth = AuthManager()
