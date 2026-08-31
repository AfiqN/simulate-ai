"""Hardened webhook registration, validation, and delivery."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import ipaddress
import json
import socket
import time
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import urlparse

import httpx

from config import WEBHOOKS_ENABLED


@dataclass
class WebhookSubscription:
    id: str
    url: str
    events: list[str]
    secret: Optional[str] = None
    active: bool = True
    created_at: float = field(default_factory=time.time)
    failure_count: int = 0
    max_failures: int = 5


WEBHOOK_EVENTS = [
    "simulation.started",
    "simulation.schema_ready",
    "simulation.round_complete",
    "simulation.completed",
    "simulation.failed",
    "simulation.cancelled",
]

_subscriptions: dict[str, WebhookSubscription] = {}
_delivery_tasks: set[asyncio.Task] = set()


def register_webhook(webhook_id: str, url: str, events: list[str], secret: Optional[str] = None) -> WebhookSubscription:
    sub = WebhookSubscription(id=webhook_id, url=url, events=events, secret=secret)
    _subscriptions[webhook_id] = sub
    return sub


def unregister_webhook(webhook_id: str) -> bool:
    return _subscriptions.pop(webhook_id, None) is not None


def list_webhooks() -> list[WebhookSubscription]:
    return list(_subscriptions.values())


def get_webhook(webhook_id: str) -> Optional[WebhookSubscription]:
    return _subscriptions.get(webhook_id)


def _is_public_address(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return False
    return bool(ip.is_global)


async def validate_webhook_url(url: str) -> None:
    """Reject credentials, non-HTTPS URLs, and any non-public DNS answer."""
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise ValueError("Webhook URL must use HTTPS and include a hostname.")
    if parsed.username or parsed.password:
        raise ValueError("Webhook URL must not contain credentials.")
    hostname = parsed.hostname.rstrip(".").lower()
    if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(".localhost"):
        raise ValueError("Webhook target must be a public host.")
    try:
        infos = await asyncio.get_running_loop().run_in_executor(
            None, lambda: socket.getaddrinfo(hostname, parsed.port or 443, type=socket.SOCK_STREAM)
        )
    except socket.gaierror as exc:
        raise ValueError("Webhook hostname could not be resolved.") from exc
    addresses = {info[4][0] for info in infos}
    if not addresses or any(not _is_public_address(address) for address in addresses):
        raise ValueError("Webhook target resolves to a non-public network address.")


def _matches_event(subscription: WebhookSubscription, event_type: str) -> bool:
    return subscription.active and ("*" in subscription.events or event_type in subscription.events)


def _sign_payload(payload: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


async def dispatch_webhook_event(event_type: str, data: dict[str, Any], run_id: Optional[str] = None) -> None:
    """Schedule tracked deliveries without blocking simulation execution."""
    if not WEBHOOKS_ENABLED:
        return
    payload = json.dumps({
        "event": event_type,
        "timestamp": time.time(),
        "run_id": run_id,
        "data": data,
    }, default=str).encode()
    for subscription in list(_subscriptions.values()):
        if _matches_event(subscription, event_type):
            task = asyncio.create_task(_deliver(subscription, payload))
            _delivery_tasks.add(task)
            task.add_done_callback(_delivery_tasks.discard)


async def _deliver(subscription: WebhookSubscription, payload: bytes) -> None:
    headers = {
        "Content-Type": "application/json",
        "X-SimulateAI-Event": "webhook",
        "X-Webhook-ID": subscription.id,
    }
    if subscription.secret:
        headers["X-SimulateAI-Signature"] = f"sha256={_sign_payload(payload, subscription.secret)}"
    try:
        # Resolve again immediately before delivery to reduce DNS-rebinding risk.
        await validate_webhook_url(subscription.url)
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
            response = await client.post(subscription.url, content=payload, headers=headers)
            subscription.failure_count = 0 if response.status_code < 400 else subscription.failure_count + 1
    except (ValueError, httpx.RequestError, httpx.TimeoutException):
        subscription.failure_count += 1
    if subscription.failure_count >= subscription.max_failures:
        subscription.active = False


async def shutdown_webhooks() -> None:
    """Finish bounded outbound deliveries during graceful shutdown."""
    if not _delivery_tasks:
        return
    done, pending = await asyncio.wait(tuple(_delivery_tasks), timeout=10.0)
    for task in pending:
        task.cancel()
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)
