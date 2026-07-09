"""Webhook management API routes."""

import uuid

from fastapi import APIRouter, HTTPException

from src.api.models import WebhookRegisterRequest, WebhookResponse
from src.api.webhooks import (
    register_webhook,
    unregister_webhook,
    list_webhooks,
    get_webhook,
    WEBHOOK_EVENTS,
)


router = APIRouter(prefix="/api")


@router.post("/webhooks", response_model=WebhookResponse, status_code=201)
async def create_webhook(req: WebhookRegisterRequest):
    """Register a new webhook endpoint to receive simulation lifecycle events."""
    # Validate event types
    for event in req.events:
        if event != "*" and event not in WEBHOOK_EVENTS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid event type '{event}'. Valid types: {WEBHOOK_EVENTS + ['*']}",
            )

    webhook_id = str(uuid.uuid4())
    sub = register_webhook(
        webhook_id=webhook_id,
        url=req.url,
        events=req.events,
        secret=req.secret,
    )

    return WebhookResponse(
        id=sub.id,
        url=sub.url,
        events=sub.events,
        active=sub.active,
        created_at=sub.created_at,
        failure_count=sub.failure_count,
    )


@router.get("/webhooks", response_model=list[WebhookResponse])
async def list_all_webhooks():
    """List all registered webhook subscriptions."""
    subs = list_webhooks()
    return [
        WebhookResponse(
            id=s.id,
            url=s.url,
            events=s.events,
            active=s.active,
            created_at=s.created_at,
            failure_count=s.failure_count,
        )
        for s in subs
    ]


@router.get("/webhooks/{webhook_id}", response_model=WebhookResponse)
async def get_webhook_detail(webhook_id: str):
    """Get details of a specific webhook subscription."""
    sub = get_webhook(webhook_id)
    if not sub:
        raise HTTPException(status_code=404, detail=f"Webhook '{webhook_id}' not found.")
    return WebhookResponse(
        id=sub.id,
        url=sub.url,
        events=sub.events,
        active=sub.active,
        created_at=sub.created_at,
        failure_count=sub.failure_count,
    )


@router.delete("/webhooks/{webhook_id}", status_code=204)
async def delete_webhook(webhook_id: str):
    """Unregister a webhook subscription."""
    if not unregister_webhook(webhook_id):
        raise HTTPException(status_code=404, detail=f"Webhook '{webhook_id}' not found.")


@router.get("/webhooks/events", response_model=list[str])
async def list_event_types():
    """List all subscribable webhook event types."""
    return WEBHOOK_EVENTS
