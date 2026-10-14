import hashlib
import sqlite3
import time
from pathlib import Path

class DispatchLedger:
    """Persistent deduplication for deliveries to an existing Telegram bot."""
    def __init__(self, workdir):
        self.path = Path(workdir) / "dispatch_log.sqlite3"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS deliveries (target TEXT NOT NULL, digest TEXT NOT NULL, state TEXT NOT NULL, updated INTEGER NOT NULL, PRIMARY KEY (target, digest))")

    def reserve(self, target, text, lease_seconds=300):
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        now = int(time.time())
        with sqlite3.connect(self.path, timeout=10) as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT state, updated FROM deliveries WHERE target=? AND digest=?", (target, digest)).fetchone()
            if row and (row[0] == "sent" or (row[0] == "sending" and now - row[1] < lease_seconds)):
                return None
            db.execute("INSERT INTO deliveries (target,digest,state,updated) VALUES (?,?,?,?) ON CONFLICT(target,digest) DO UPDATE SET state=excluded.state, updated=excluded.updated", (target,digest,"sending",now))
        return digest

    def finish(self, target, digest, success):
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE deliveries SET state=?,updated=? WHERE target=? AND digest=?", ("sent" if success else "failed",int(time.time()),target,digest))
