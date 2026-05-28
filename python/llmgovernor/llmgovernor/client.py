"""LLMGovernor SDK client — sync batching, posts to /v1/events with X-API-Key."""

import logging
import os
import threading
from typing import List, Optional

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore

from .types import CostEvent

logger = logging.getLogger(__name__)


class LLMGovernorClient:
    """Buffers cost events locally, flushes in batches to the LLMGovernor API.

    Auth: uses X-API-Key (matches the backend's `get_current_account`
    dependency). Authorization: Bearer is reserved for dashboard session
    JWTs and will be rejected for raw API keys.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.llmgovernor.ai",
        batch_size: int = 50,
        flush_interval: float = 5.0,
        default_agent_name: str = "default",
    ):
        self.api_key = api_key or os.environ.get("LLMGOVERNOR_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "LLMGovernorClient needs an api_key — pass it explicitly or "
                "set LLMGOVERNOR_API_KEY in the environment."
            )
        self.base_url = base_url.rstrip("/")
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.default_agent_name = default_agent_name
        self._buffer: List[CostEvent] = []
        self._lock = threading.Lock()
        self._total_events_sent: int = 0
        self._total_events_failed: int = 0

    def queue_event(self, event: CostEvent) -> None:
        """Add a cost event to the send buffer."""
        with self._lock:
            self._buffer.append(event)
            if len(self._buffer) >= self.batch_size:
                self._flush_locked()

    def _flush_locked(self) -> None:
        if not self._buffer:
            return
        events = self._buffer[:]
        self._buffer.clear()
        self._send_batch(events)

    def _send_batch(self, events: List[CostEvent]) -> None:
        if not httpx:
            self._total_events_failed += len(events)
            return
        try:
            payload = [e.to_dict() for e in events]
            with httpx.Client(timeout=10) as client:
                resp = client.post(
                    f"{self.base_url}/v1/events",
                    json={"events": payload},
                    headers={
                        "X-API-Key": self.api_key,
                        "Content-Type": "application/json",
                    },
                )
                if resp.status_code < 300:
                    self._total_events_sent += len(events)
                else:
                    self._total_events_failed += len(events)
                    # Re-queue on server error so we retry on next flush.
                    # 4xx errors (auth, quota) won't fix themselves — drop.
                    if resp.status_code >= 500:
                        with self._lock:
                            self._buffer.extend(events)
                    else:
                        logger.warning(
                            "llmgovernor: dropping %d events (status %d): %s",
                            len(events),
                            resp.status_code,
                            resp.text[:200],
                        )
        except Exception as e:
            self._total_events_failed += len(events)
            logger.warning("llmgovernor: send failed (%s), re-queuing", e)
            with self._lock:
                self._buffer.extend(events)

    def flush(self) -> None:
        with self._lock:
            self._flush_locked()

    def close(self) -> None:
        self.flush()

    @property
    def pending_count(self) -> int:
        with self._lock:
            return len(self._buffer)

    @property
    def stats(self) -> dict:
        return {
            "pending": self.pending_count,
            "sent": self._total_events_sent,
            "failed": self._total_events_failed,
        }


# Back-compat alias for any code that still imports BlazeClient.
BlazeClient = LLMGovernorClient
