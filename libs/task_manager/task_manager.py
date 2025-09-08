"""
Task Manager
`TaskManager` wrapper that tracks available
slots and runs tasks asynchronously while delegating broker
calls to `TaskBrokerClient` (no background loop).
"""

import asyncio
import logging
from typing import Awaitable, Callable

from task_broker_client import TaskBrokerClient


class TaskManager:
    """
    Tracks available slots and orchestrates asynchronous
    task execution without a background loop.
    Wraps TaskBrokerClient for broker interactions
    and never stops during service lifetime.
    """

    def __init__(
        self, broker: TaskBrokerClient, *, max_concurrent: int
    ) -> None:
        self.broker = broker
        self.max_concurrent = max_concurrent
        self._inflight: set[str] = set()
        self._available_slots = max_concurrent
        # Initial readiness will be triggered
        # explicitly via start() on app startup
        self._ready_lock = asyncio.Lock()

    def inflight_count(self) -> int:
        return len(self._inflight)

    def capacity(self) -> int:
        return max(0, self.max_concurrent - self.inflight_count())

    async def start(self) -> None:
        # Advertise readiness with retry/backoff until the broker is reachable.
        if self._available_slots <= 0:
            return
        async with self._ready_lock:
            # Re-check after acquiring the lock to avoid double-advertising.
            if self._available_slots <= 0:
                return
            backoff_seconds = 0.5
            max_backoff_seconds = 10.0
            while True:
                try:
                    await self.broker.ready()
                    self._available_slots -= 1
                    return
                except Exception as exc:
                    logging.warning(
                        "Task broker not ready; retrying in %.1fs: %s",
                        backoff_seconds,
                        exc,
                    )
                    try:
                        await asyncio.sleep(backoff_seconds)
                    except asyncio.CancelledError:
                        raise
                    backoff_seconds = min(
                        max_backoff_seconds, backoff_seconds * 2
                    )

    async def execute_task(
        self, task_payload: dict, work: Callable[[dict], Awaitable[dict]]
    ) -> dict:
        """
        Execute a single task asynchronously using provided `work` coroutine.
        Manages slot tracking and ACK/NACK/FAIL.
        Returns a small acceptance payload for the HTTP handler.
        """
        task_id = task_payload["task_id"]
        if self.capacity() <= 0:
            await self.broker.nack(task_id)
            return {"accepted": False, "reason": "no-capacity"}
        self._inflight.add(task_id)

        # If we still have unused tokens after taking this task,
        # advertise another slot
        if self._available_slots > 0:
            asyncio.create_task(self.start())
        try:
            output = await work(task_payload)
            await self.broker.ack(task_id, output=output)
        except Exception as e:
            # Optionally distinguish RecoverableError; for now,
            # fail on unexpected exceptions
            await self.broker.fail(task_id, status={"error": str(e)})
        finally:
            self._inflight.discard(task_id)
            # Free a slot and advertise readiness again
            self._available_slots = min(
                self._available_slots + 1,
                self.max_concurrent - self.inflight_count(),
            )
            asyncio.create_task(self.start())
        return {"accepted": True}

    async def stop(self) -> None:
        try:
            await self.broker.deregister()
        finally:
            await self.broker.aclose()
