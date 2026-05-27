from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Transport:
    api_key: Optional[str] = None
    endpoint: Optional[str] = None
    events: List[Dict[str, Any]] = field(default_factory=list)

    def enqueue(self, event: Dict[str, Any]) -> None:
        # In a real implementation this would POST to the endpoint.
        # For now, append for inspection/testing.
        self.events.append(event)


_global_transport: Optional[Transport] = None


def init(api_key: Optional[str] = None, endpoint: Optional[str] = None, **_: Any) -> Transport:
    global _global_transport
    if _global_transport is None:
        _global_transport = Transport(api_key=api_key, endpoint=endpoint)
    else:
        if api_key is not None:
            _global_transport.api_key = api_key
        if endpoint is not None:
            _global_transport.endpoint = endpoint
    return _global_transport


def get_transport() -> Optional[Transport]:
    return _global_transport


def reset_transport() -> None:
    global _global_transport
    _global_transport = None
