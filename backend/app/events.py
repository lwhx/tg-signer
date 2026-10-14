import logging
from collections import deque
from contextvars import ContextVar

from .db import now

log_context = ContextVar("log_context", default=None)
execution_errors = ContextVar("execution_errors", default=None)


class EventBus:
    def __init__(self):
        self.history = deque(maxlen=500)
        self.clients = set()

    def emit(self, message, level="INFO", **meta):
        entry = {
            "time": now(),
            "level": level,
            "message": str(message)[:16000],
            **(log_context.get() or {}),
            **meta,
        }
        self.history.append(entry)
        for queue in list(self.clients):
            if queue.full():
                queue.get_nowait()
            queue.put_nowait(entry)


bus = EventBus()


class LogBridge(logging.Handler):
    def emit(self, record):
        errors = execution_errors.get()
        if errors is not None and record.levelno >= logging.WARNING:
            errors.append(record.getMessage())
        # Upstream raw Telegram responses belong in the authenticated console.
        bus.emit(record.getMessage(), record.levelname)
