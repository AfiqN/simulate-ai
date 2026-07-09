"""Webhook registration and dispatch for simulation lifecycle events."""

import asyncio
import hashlib
import hmac
import json
import time
from typing import Any, Optional
from dataclasses import dataclass, field

import httpx


@dataclass
class WebhookSubscription:
    """A registered webhook endpoint."""
    id: str
    url: str
    events: list[str]  # e.g. ["simulation.started", "simulation.completed", "*"]
    secret: Optional[str] = None  # HMAC signing secret
    active: bool = True
    created_at: float = field(default_factory=time.time)
    failure_count: int = 0
    max_failures: int = 5  # Auto-disable after this many consecutive failures


# Event types that can be subscribed to
WEBHOOK_EVENTS = [
    "simulation.started",
    "simulation.schema_ready",
    "simulation.round_complete",
    "simulation.completed",
    "simulation.failed",
    "simulation.cancelled",
]

# In-memory store (could be backed by DB for persistence)
_subscriptions: dict[str, WebhookSubscription] = {}


def register_webhook(
    webhook_id: str,
    url: str,
    events: list[str],
    secret: Optional[str] = None,
) -> WebhookSubscription:
    """Register a new webhook subscription."""
    sub = WebhookSubscription(
        id=webhook_id,
        url=url,
        events=events,
        secret=secret,
    )
    _subscriptions[webhook_id] = sub
    return sub


def unregister_webhook(webhook_id: str) -> bool:
    """Remove a webhook subscription. Returns True if found."""
    return _subscriptions.pop(webhook_id, None) is not None


def list_webhooks() -> list[WebhookSubscription]:
    """List all registered webhooks."""
    return list(_subscriptions.values())


def get_webhook(webhook_id: str) -> Optional[WebhookSubscription]:
    """Get a specific webhook by ID."""
    return _subscriptions.get(webhook_id)


def _matches_event(subscription: WebhookSubscription, event_type: str) -> bool:
    """Check if a subscription should receive this event type."""
    if not subscription.active:
        return False
    if "*" in subscription.events:
        return True
    return event_type in subscription.events


def _sign_payload(payload: bytes, secret: str) -> str:
    """Generate HMAC-SHA256 signature for webhook payload."""
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


async def dispatch_webhook_event(
    event_type: str,
    data: dict[str, Any],
    run_id: Optional[str] = None,
) -> None:
    """Dispatch a webhook event to all matching subscribers (fire-and-forget)."""
    matching = [s for s in _subscriptions.values() if _matches_event(s, event_type)]
    if not matching:
        return

    payload = {
        "event": event_type,
        "timestamp": time.time(),
        "run_id": run_id,
        "data": data,
    }
    payload_bytes = json.dumps(payload, default=str).encode()

    tasks = [_deliver(sub, payload_bytes) for sub in matching]
    # Fire-and-forget: don't block the pipeline
    asyncio.gather(*tasks, return_exceptions=True)


async def _deliver(subscription: WebhookSubscription, payload: bytes) -> None:
    """Deliver a webhook payload to a single subscriber."""
    headers = {
        "Content-Type": "application/json",
        "X-SimulateAI-Event": "webhook",
        "X-Webhook-ID": subscription.id,
    }
    if subscription.secret:
        sig = _sign_payload(payload, subscription.secret)
        headers["X-SimulateAI-Signature"] = f"sha256={sig}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(subscription.url, content=payload, headers=headers)
            if resp.status_code >= 400:
                subscription.failure_count += 1
            else:
                subscription.failure_count = 0
    except (httpx.RequestError, httpx.TimeoutException):
        subscription.failure_count += 1

    # Auto-disable after too many failures
    if subscription.failure_count >= subscription.max_failures:
        subscription.active = False
