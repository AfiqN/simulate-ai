"""WebSocket event bus for real-time simulation streaming."""

import asyncio
from typing import Any


class SimulationEventBus:
    """Fan-out event bus: one simulation emits, many WebSocket clients receive."""

    def __init__(self):
        self._channels: dict[str, list[asyncio.Queue]] = {}

    def emit(self, run_id: str, event: dict[str, Any]) -> None:
        """Push an event to all subscribers of a given run_id."""
        for queue in self._channels.get(run_id, []):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass

    def subscribe(self, run_id: str) -> asyncio.Queue:
        """Subscribe to events for a run. Returns a Queue to read from."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=256)
        self._channels.setdefault(run_id, []).append(queue)
        return queue

    def unsubscribe(self, run_id: str, queue: asyncio.Queue) -> None:
        """Remove a subscriber queue."""
        queues = self._channels.get(run_id, [])
        if queue in queues:
            queues.remove(queue)
        if not queues and run_id in self._channels:
            del self._channels[run_id]


event_bus = SimulationEventBus()
