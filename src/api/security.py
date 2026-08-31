"""Capability-token helpers for run ownership and read-only sharing."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Any

from fastapi import HTTPException, Request, WebSocket


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def token_matches(token: str | None, expected_hash: str | None) -> bool:
    if not token or not expected_hash:
        return False
    return hmac.compare_digest(hash_token(token), expected_hash)


def bearer_token(headers: Any) -> str | None:
    value = headers.get("authorization", "")
    if value.lower().startswith("bearer "):
        return value[7:].strip() or None
    return headers.get("x-run-token") or None


def request_token(request: Request) -> str | None:
    return bearer_token(request.headers)


def require_owner(request: Request, row: dict[str, Any]) -> None:
    if not token_matches(request_token(request), row.get("owner_token_hash")):
        raise HTTPException(status_code=403, detail="Owner access token required.")


def require_read_access(request: Request, row: dict[str, Any]) -> str:
    # Legacy runs created before capability tokens remain readable so existing
    # portfolio examples/history do not break. New runs always have a token.
    if not row.get("owner_token_hash"):
        return "legacy"
    if token_matches(request_token(request), row.get("owner_token_hash")):
        return "owner"
    share = request.query_params.get("share") or request.headers.get("x-share-token")
    if row.get("share_enabled") and token_matches(share, row.get("share_token_hash")):
        return "shared"
    raise HTTPException(status_code=403, detail="A valid run or share token is required.")


def websocket_has_access(websocket: WebSocket, row: dict[str, Any]) -> bool:
    owner = websocket.query_params.get("token")
    share = websocket.query_params.get("share")
    return token_matches(owner, row.get("owner_token_hash")) or bool(
        row.get("share_enabled") and token_matches(share, row.get("share_token_hash"))
    )
