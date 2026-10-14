import logging
import sqlite3
from datetime import datetime, timezone
from types import SimpleNamespace
import pytest
from tg_signer.automation.dispatch_ledger import DispatchLedger
from tg_signer.automation.handlers import dispatch_link_to_bot
from tg_signer.automation.models import AutomationContext, Event, RuleStateStore

class Worker:
    def __init__(self, fail=False):
        self.sent = []
        self.fail = fail
    async def send_message(self, target, message):
        if self.fail:
            raise RuntimeError("send failed")
        self.sent.append((target, message))

def context(tmp_path, worker, text):
    event = Event(type="message", chat_id=-1001, message=SimpleNamespace(text=text, caption=None, id=10), now=datetime.now(timezone.utc), trigger_id="t", rule_id="r")
    ctx = AutomationContext(vars={}, state=RuleStateStore(tmp_path / "state.json", logging.getLogger("test")), client=None, logger=logging.getLogger("test"), worker=worker, workdir=tmp_path)
    return event, ctx

@pytest.mark.asyncio
async def test_delivery_is_deduplicated(tmp_path):
    worker = Worker()
    event, ctx = context(tmp_path, worker, "标题\nhttps://115cdn.com/s/example?password=abc#")
    params = {"bot_chat_id": "@save_bot", "pattern": r"(https?://115cdn\.com/s/[^\s]+)"}
    assert await dispatch_link_to_bot(event, ctx, params) == "continue"
    assert await dispatch_link_to_bot(event, ctx, params) == "continue"
    assert worker.sent == [("@save_bot", "https://115cdn.com/s/example?password=abc#")]
    with sqlite3.connect(tmp_path / "dispatch_log.sqlite3") as db:
        assert db.execute("SELECT state FROM deliveries").fetchone() == ("sent",)

@pytest.mark.asyncio
async def test_failed_delivery_can_retry(tmp_path):
    worker = Worker(fail=True)
    event, ctx = context(tmp_path, worker, "https://115cdn.com/s/example")
    params = {"bot_chat_id": "@save_bot", "pattern": r"(https?://115cdn\.com/s/[^\s]+)"}
    assert await dispatch_link_to_bot(event, ctx, params) == "stop"
    worker.fail = False
    assert await dispatch_link_to_bot(event, ctx, params) == "continue"
    assert len(worker.sent) == 1

def test_ledger_deduplication_across_instances(tmp_path):
    ledger1 = DispatchLedger(tmp_path)
    ledger2 = DispatchLedger(tmp_path)
    token = ledger1.reserve("@bot", "a")
    assert token is not None
    assert ledger2.reserve("@bot", "a") is None
    ledger1.finish("@bot", token, True)
    assert ledger2.reserve("@bot", "a") is None
