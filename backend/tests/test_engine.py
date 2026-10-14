import asyncio
from collections import defaultdict
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from backend.app.db import Run, Session, Task
from backend.app.engine import TaskEngine, matches
from backend.app.schemas import TaskInput


class FakeClient:
    def __init__(self):
        self.handlers = []

    def add_handler(self, handler, group):
        self.handlers.append(handler)

    def remove_handler(self, handler, group):
        self.handlers.remove(handler)


class FakeWorker:
    def __init__(self, responses, warning=""):
        self.app = FakeClient()
        self.context = SimpleNamespace(sign_chats=defaultdict(list), chat_messages={})
        self.warnings = []
        self.responses = responses
        self.warning = warning
        self.persisted = False

    async def resolve_chat_route_key(self, chat):
        return (123, chat.message_thread_id)

    async def _on_message(self, client, message):
        pass

    async def sign_a_chat(self, chat):
        for message in self.responses:
            if isinstance(message, str):
                self.on_callback_text(message)
            else:
                await self.app.handlers[0].callback(self.app, message)
        if self.warning:
            self.warnings.append(self.warning)

    def persist_sign_record(self, *args):
        self.persisted = True

    def load_sign_record(self):
        return {}


def message(text, outgoing=False, chat_id=123, thread=None):
    return SimpleNamespace(
        id=1,
        chat=SimpleNamespace(id=chat_id),
        text=text,
        caption=None,
        outgoing=outgoing,
        message_thread_id=thread,
    )


def make_task(account, **overrides):
    payload = {
        "id": 1,
        "name": "sign",
        "account_id": account,
        "kind": "signer",
        "enabled": False,
        "cron": "0 8 * * *",
        "timezone": "Asia/Shanghai",
        "delay_min": 10,
        "delay_max": 300,
        "success_pattern": "签到成功",
        "failure_pattern": "失败",
        "response_timeout": 1,
        "folder": "",
        "config": {
            "sign_at": "0 8 * * *",
            "sign_interval": 0,
            "chats": [
                {"chat_id": 123, "actions": [{"action": 1, "text": "/sign"}], "action_interval": 0}
            ],
        },
        **overrides,
    }
    return Task(**payload)


@pytest.mark.parametrize(
    "responses,pattern,warning,expected",
    [
        ([message("签到成功，获得 10 积分")], "签到成功", "", "success"),
        (["签到成功（按钮提示）"], "签到成功", "", "success"),
        ([message("签到成功，但失败")], "签到成功", "", "failed"),
        ([message("签到成功", outgoing=True)], "签到成功", "", "failed"),
        ([message("签到成功", chat_id=999)], "签到成功", "", "failed"),
        ([message("已收到")], "", "", "completed"),
        ([message("已收到")], "", "等待超时: 点击按钮", "failed"),
    ],
)
async def test_real_engine_result_classification(
    monkeypatch, responses, pattern, warning, expected
):
    engine = TaskEngine()
    worker = FakeWorker(responses, warning)
    monkeypatch.setattr("backend.app.engine.telegram.worker", AsyncMock(return_value=worker))
    monkeypatch.setattr(engine, "discover", AsyncMock())
    result = await engine.sign(make_task(1, success_pattern=pattern))
    assert result[0] == expected
    assert not worker.app.handlers, "message handlers must be removed after every run"
    assert worker.persisted == (expected in {"success", "completed"})


async def test_randomized_schedule_persisted_and_sunday_semantics(client, account):
    engine = TaskEngine()
    engine.scheduler.start()
    try:
        with Session() as db:
            task = make_task(account, enabled=True, cron="0 8 * * 0", delay_min=23, delay_max=23)
            db.add(task)
            db.commit()
            task_id = task.id
        engine.schedule(task_id)
        with Session() as db:
            value = db.get(Task, task_id).next_run
        scheduled = datetime.fromisoformat(value)
        assert scheduled.weekday() == 6  # POSIX Sunday, not APScheduler Monday
        assert scheduled.hour == 8 and scheduled.minute == 0 and scheduled.second == 23
        engine.schedule(task_id, restore=True)
        with Session() as db:
            assert db.get(Task, task_id).next_run == value
    finally:
        engine.scheduler.shutdown(wait=False)


@pytest.mark.parametrize(
    "current,expected",
    [
        ("2030-01-01T00:00:00+08:00", "2030-01-01T07:05:23+08:00"),
        ("2030-01-01T07:05:00+08:00", "2030-01-15T07:05:23+08:00"),
        ("2030-01-15T07:05:00+08:00", "2030-01-31T07:05:23+08:00"),
        ("2030-01-31T07:05:00+08:00", "2030-02-01T07:05:23+08:00"),
        ("2030-02-15T07:05:00+08:00", "2030-03-01T07:05:23+08:00"),
    ],
)
async def test_monthly_multiple_dates_schedule(client, account, monkeypatch, current, expected):
    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls.fromisoformat(current).astimezone(tz)

    monkeypatch.setattr("backend.app.engine.datetime", FixedDateTime)
    engine = TaskEngine()
    engine.scheduler.start()
    try:
        with Session() as db:
            task = make_task(
                account, enabled=True, cron="5 7 1,15,31 * *", delay_min=23, delay_max=23
            )
            db.add(task)
            db.commit()
            task_id = task.id
        engine.schedule(task_id)
        with Session() as db:
            assert db.get(Task, task_id).next_run == expected
    finally:
        engine.scheduler.shutdown(wait=False)


async def test_concurrent_run_rejected_and_cancel_recorded(client, account, monkeypatch):
    engine = TaskEngine()

    async def pending(task):
        await asyncio.Event().wait()

    monkeypatch.setattr(engine, "sign", pending)
    with Session() as db:
        task = make_task(account)
        db.add(task)
        db.commit()
        task_id = task.id
    engine.launch(task_id)
    await asyncio.sleep(0.01)
    with pytest.raises(HTTPException) as error:
        engine.launch(task_id)
    assert error.value.status_code == 409
    await engine.stop(task_id)
    with Session() as db:
        record = db.query(Run).filter_by(task_id=task_id).first()
        assert record.status == "cancelled"
        assert record.finished_at is not None


def test_regex_execution_budget():
    with pytest.raises(TimeoutError):
        matches("(a+)+$", "a" * 20000 + "!")


def test_empty_actions_and_negative_intervals_rejected():
    task = make_task(1)
    cfg = task.config
    cfg["chats"][0]["actions"] = []
    with pytest.raises(ValueError):
        TaskInput(name="bad", account_id=1, config=cfg)
