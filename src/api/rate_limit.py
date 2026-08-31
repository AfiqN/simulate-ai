"""Durable, privacy-preserving rate limiting for public demo endpoints."""

from __future__ import annotations

import hashlib
import time

from fastapi import Request

from config import RATE_LIMIT_SALT, TRUST_PROXY_HEADERS
from src.persistence.db import count_recent_usage, record_usage

RATE_LIMIT_WINDOW = 86_400
DEMO_LIMIT = 3
BYOK_LIMIT = 30


def client_identity(request: Request) -> str:
    """Return a salted hash; never persist a raw client IP."""
    address = request.client.host if request.client else "unknown"
    if TRUST_PROXY_HEADERS:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            address = forwarded.split(",", 1)[0].strip() or address
    return hashlib.sha256(f"{RATE_LIMIT_SALT}:{address}".encode()).hexdigest()


async def quota_state(request: Request) -> tuple[str, int, int]:
    identity = client_identity(request)
    limit = BYOK_LIMIT if request.headers.get("x-api-key", "").strip() else DEMO_LIMIT
    count = await count_recent_usage(
        request.app.state.db, identity, time.time() - RATE_LIMIT_WINDOW
    )
    return identity, count, limit


async def consume(request: Request, identity: str) -> None:
    await record_usage(request.app.state.db, identity, time.time())
