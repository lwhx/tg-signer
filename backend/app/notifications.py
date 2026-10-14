import json
import logging
from urllib.parse import quote

import httpx

from .db import get_setting
from .security import decrypt


async def notify(title, body):
    configs = json.loads(decrypt(get_setting("notifications")) or "[]")
    results = []
    async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
        for item in configs:
            if not item.get("enabled", True):
                continue
            kind = item.get("type")
            try:
                if kind == "bark":
                    response = await client.post(
                        item["url"].rstrip("/") + "/push",
                        json={"device_key": item["key"], "title": title, "body": body},
                    )
                elif kind == "telegram":
                    response = await client.post(
                        f"https://api.telegram.org/bot{item['token']}/sendMessage",
                        json={"chat_id": item["chat_id"], "text": f"{title}\n{body}"},
                    )
                elif kind == "serverchan":
                    key = item["key"]
                    if key.startswith("sctp"):
                        import re

                        match = re.match(r"sctp(\d+)t", key)
                        if not match:
                            raise ValueError("Invalid ServerChan key")
                        url = f"https://{match.group(1)}.push.ft07.com/send/{quote(key, safe='')}.send"
                    else:
                        url = f"https://sctapi.ftqq.com/{quote(key, safe='')}.send"
                    response = await client.post(url, data={"title": title, "desp": body})
                elif kind == "pushdeer":
                    response = await client.post(
                        item.get("url", "https://api2.pushdeer.com").rstrip("/") + "/message/push",
                        data={"pushkey": item["key"], "text": title, "desp": body},
                    )
                elif kind == "webhook":
                    response = await client.post(
                        item["url"],
                        json={"title": title, "message": body},
                        headers=item.get("headers", {}),
                    )
                else:
                    raise ValueError("Unknown notification provider")
                response.raise_for_status()
                payload = (
                    response.json() if "json" in response.headers.get("content-type", "") else {}
                )
                if (kind == "telegram" and not payload.get("ok")) or (
                    kind in {"bark", "serverchan", "pushdeer"}
                    and payload.get("code", 0) not in {0, 200}
                ):
                    raise ValueError("Provider rejected notification")
                results.append({"type": kind, "ok": True})
            except Exception as exc:
                # URL/token-bearing exceptions must never enter logs.
                logging.getLogger("dashboard").warning(
                    "Notification %s failed: %s", kind, type(exc).__name__
                )
                results.append({"type": kind, "ok": False, "error": type(exc).__name__})
    return results
