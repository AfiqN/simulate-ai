"""Administrative webhook management routes.

Webhooks are disabled by default. When enabled, every management endpoint
requires X-Admin-Key and registration performs SSRF-safe URL validation.
"""

from __future__ import annotations

import hmac
import uuid

from fastapi import APIRouter, HTTPException, Request

from config import ADMIN_API_KEY, WEBHOOKS_ENABLED
from src.api.models import WebhookRegisterRequest, WebhookResponse
from src.api.webhooks import (
    WEBHOOK_EVENTS,
    get_webhook,
    list_webhooks,
    register_webhook,
    unregister_webhook,
    validate_webhook_url,
)

router = APIRouter(prefix="/api")


def _require_admin(request: Request) -> None:
    supplied = request.headers.get("x-admin-key", "")
    if not WEBHOOKS_ENABLED:
        raise HTTPException(status_code=404, detail="Webhooks are disabled.")
    if not ADMIN_API_KEY or not hmac.compare_digest(supplied, ADMIN_API_KEY):
        raise HTTPException(status_code=403, detail="Administrative access required.")


def _response(sub) -> WebhookResponse:
    return WebhookResponse(
        id=sub.id,
        url=sub.url,
        events=sub.events,
        active=sub.active,
        created_at=sub.created_at,
        failure_count=sub.failure_count,
    )


# Static route must precede /webhooks/{webhook_id}.
@router.get("/webhooks/events", response_model=list[str])
async def list_event_types(request: Request):
    _require_admin(request)
    return WEBHOOK_EVENTS


@router.post("/webhooks", response_model=WebhookResponse, status_code=201)
async def create_webhook(req: WebhookRegisterRequest, request: Request):
    _require_admin(request)
    for event in req.events:
        if event != "*" and event not in WEBHOOK_EVENTS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid event type '{event}'. Valid types: {WEBHOOK_EVENTS + ['*']}",
            )
    try:
        await validate_webhook_url(req.url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _response(register_webhook(str(uuid.uuid4()), req.url, req.events, req.secret))


@router.get("/webhooks", response_model=list[WebhookResponse])
async def list_all_webhooks(request: Request):
    _require_admin(request)
    return [_response(sub) for sub in list_webhooks()]


@router.get("/webhooks/{webhook_id}", response_model=WebhookResponse)
async def get_webhook_detail(webhook_id: str, request: Request):
    _require_admin(request)
    sub = get_webhook(webhook_id)
    if not sub:
        raise HTTPException(status_code=404, detail=f"Webhook '{webhook_id}' not found.")
    return _response(sub)


@router.delete("/webhooks/{webhook_id}", status_code=204)
async def delete_webhook(webhook_id: str, request: Request):
    _require_admin(request)
    if not unregister_webhook(webhook_id):
        raise HTTPException(status_code=404, detail=f"Webhook '{webhook_id}' not found.")
