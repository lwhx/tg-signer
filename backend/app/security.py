import os
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

import jwt
from cryptography.fernet import Fernet
from fastapi import HTTPException, Request
from pwdlib import PasswordHash

from .db import DATA, get_setting


def persistent_secret(name, factory):
    path = DATA / name
    if not path.exists():
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as fp:
            fp.write(factory())
    return path.read_text().strip()


KEY = os.getenv("ENCRYPTION_KEY") or persistent_secret(
    "encryption.key", lambda: Fernet.generate_key().decode()
)
JWT_KEY = os.getenv("JWT_SECRET") or persistent_secret("jwt.key", lambda: secrets.token_urlsafe(48))
cipher = Fernet(KEY.encode())
passwords = PasswordHash.recommended()
COOKIE = "tg_dashboard"
SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
TTL = 60 * 60 * 12


def encrypt(value):
    return cipher.encrypt(value.encode()).decode() if value else ""


def decrypt(value):
    return cipher.decrypt(value.encode()).decode() if value else ""


def token():
    return jwt.encode(
        {
            "sub": "admin",
            "v": get_setting("token_version", "0"),
            "exp": datetime.now(timezone.utc) + timedelta(seconds=TTL),
            "iat": datetime.now(timezone.utc),
        },
        JWT_KEY,
        algorithm="HS256",
    )


def valid_token(value):
    try:
        data = jwt.decode(
            value or "",
            JWT_KEY,
            algorithms=["HS256"],
            options={"require": ["exp", "sub", "iat"]},
        )
        return data["sub"] == "admin" and data.get("v") == get_setting("token_version", "0")
    except jwt.InvalidTokenError:
        return False


def require_admin(request: Request):
    bearer = request.headers.get("authorization", "")
    value = bearer[7:] if bearer.startswith("Bearer ") else request.cookies.get(COOKIE)
    if not valid_token(value):
        raise HTTPException(401, "请先登录管理面板")


attempts = defaultdict(deque)


def rate_limit(key, limit=10, window=300):
    t = time.monotonic()
    bucket = attempts[key]
    while bucket and bucket[0] < t - window:
        bucket.popleft()
    if len(bucket) >= limit:
        raise HTTPException(429, "请求过于频繁，请稍后再试", headers={"Retry-After": str(window)})
    bucket.append(t)
    # Bound storage for unauthenticated addresses.
    if len(attempts) > 10000:
        for old in list(attempts)[:5000]:
            if old != key:
                attempts.pop(old, None)
