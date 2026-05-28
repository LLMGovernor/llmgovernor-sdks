"""Blaze SDK — CostEvent and core types."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any
import uuid


@dataclass
class CostEvent:
    """A single LLM API call with cost attribution."""

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    agent_name: str = "default"
    model: str = ""
    provider: str = ""  # openai, anthropic, bedrock, google
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    status: str = "ok"  # ok, error, throttled, blocked
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "agent_name": self.agent_name,
            "model": self.model,
            "provider": self.provider,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "cost_usd": self.cost_usd,
            "latency_ms": self.latency_ms,
            "status": self.status,
            "metadata": self.metadata,
        }
