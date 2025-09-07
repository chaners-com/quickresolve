"""
Task Broker Client
Minimal API to announce readiness for one task
at a time (single-slot), acknowledge success or failure,
and deregister on shutdown.
"""

import os
from typing import Optional

import httpx


class TaskBrokerClient:
    """HTTP client for the task broker in task-service."""

    def __init__(
        self,
        *,
        endpoint_url: str,
        health_url: str,
        topic: str,
        base_url: Optional[str] = None,
    ) -> None:
        self.base_url = base_url or os.getenv(
            "TASK_BROKER_URL", "http://task-service:8010"
        )
        self.endpoint_url = endpoint_url
        self.health_url = health_url
        self.topic = topic
        self._client = httpx.AsyncClient()

    async def ready(self) -> None:
        body = {
            "endpoint_url": self.endpoint_url,
            "health_url": self.health_url,
            "topic": self.topic,
            "ready": True,
        }
        r = await self._client.put(f"{self.base_url}/consumer", json=body)
        r.raise_for_status()

    async def deregister(self) -> None:
        r = await self._client.delete(
            f"{self.base_url}/consumer",
            json={"endpoint_url": self.endpoint_url},
        )
        r.raise_for_status()

    async def ack(self, task_id: str, output: Optional[dict] = None) -> None:
        payload = {"status_code": 2}
        if output is not None:
            payload["output"] = output
        r = await self._client.put(
            f"{self.base_url}/task/{task_id}", json=payload
        )
        r.raise_for_status()

    async def nack(self, task_id: str) -> None:
        payload = {"status_code": 0}
        r = await self._client.put(
            f"{self.base_url}/task/{task_id}", json=payload
        )
        r.raise_for_status()

    async def fail(self, task_id: str, status: Optional[dict] = None) -> None:
        payload = {"status_code": 3}
        if status is not None:
            payload["status"] = status
        r = await self._client.put(
            f"{self.base_url}/task/{task_id}", json=payload
        )
        r.raise_for_status()

    async def update_state(self, task_id: str, state: dict) -> None:
        payload = {"state": state}
        r = await self._client.put(
            f"{self.base_url}/task/{task_id}", json=payload
        )
        r.raise_for_status()

    async def reschedule(
        self, task_id: str, scheduled_start_timestamp: int
    ) -> None:
        payload = {
            "status_code": 0,
            "scheduled_start_timestamp": scheduled_start_timestamp,
        }
        r = await self._client.put(
            f"{self.base_url}/task/{task_id}", json=payload
        )
        r.raise_for_status()

    async def get_task(self, task_id: str) -> dict:
        r = await self._client.get(f"{self.base_url}/task/{task_id}")
        r.raise_for_status()
        return r.json()

    async def aclose(self) -> None:
        await self._client.aclose()
