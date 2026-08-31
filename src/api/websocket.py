"""Replayable in-process event bus for simulation streaming."""

from __future__ import annotations

import asyncio
from collections import deque
from typing import Any


class SimulationEventBus:
    """Fan-out event bus with bounded per-run replay history."""

    def __init__(self, history_size: int = 512):
        self._channels: dict[str, list[asyncio.Queue]] = {}
        self._history: dict[str, deque[dict[str, Any]]] = {}
        self._sequence: dict[str, int] = {}
        self._history_size = history_size

    def emit(self, run_id: str, event: dict[str, Any]) -> dict[str, Any]:
        seq = self._sequence.get(run_id, 0) + 1
        self._sequence[run_id] = seq
        enriched = {**event, "seq": seq}
        history = self._history.setdefault(run_id, deque(maxlen=self._history_size))
        history.append(enriched)
        for queue in list(self._channels.get(run_id, [])):
            try:
                queue.put_nowait(enriched)
            except asyncio.QueueFull:
                # Drop the oldest queued event; the client can recover it from replay.
                try:
                    queue.get_nowait()
                    queue.put_nowait(enriched)
                except (asyncio.QueueEmpty, asyncio.QueueFull):
                    pass
        return enriched

    def subscribe(self, run_id: str, since: int = 0) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=self._history_size)
        for event in self._history.get(run_id, ()):
            if int(event.get("seq", 0)) > since:
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    break
        self._channels.setdefault(run_id, []).append(queue)
        return queue

    def unsubscribe(self, run_id: str, queue: asyncio.Queue) -> None:
        queues = self._channels.get(run_id, [])
        if queue in queues:
            queues.remove(queue)
        if not queues:
            self._channels.pop(run_id, None)

    def latest_sequence(self, run_id: str) -> int:
        return self._sequence.get(run_id, 0)

    def clear(self, run_id: str) -> None:
        self._channels.pop(run_id, None)
        self._history.pop(run_id, None)
        self._sequence.pop(run_id, None)


event_bus = SimulationEventBus()
