"""Map a Helicone webhook payload to the LLMGovernor /v1/events schema."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

# Keys Helicone may use to identify the calling agent.
_AGENT_KEYS = ("Helicone-Property-Agent", "agent", "helicone-property-agent")

# Normalise provider strings (Helicone uppercases them).
_PROVIDER_MAP = {
    "OPENAI": "openai",
    "ANTHROPIC": "anthropic",
    "AZURE": "azure",
    "GOOGLE": "google",
    "COHERE": "cohere",
    "MISTRAL": "mistral",
    "TOGETHER": "together",
}


def _parse_iso(ts_str: str) -> datetime:
    """Parse an ISO-8601 timestamp that may end with 'Z' or a UTC offset."""
    if ts_str.endswith("Z"):
        ts_str = ts_str[:-1] + "+00:00"
    return datetime.fromisoformat(ts_str)


def _latency_ms(req_ts: str, resp_ts: str) -> int:
    try:
        delta = _parse_iso(resp_ts) - _parse_iso(req_ts)
        return max(0, int(delta.total_seconds() * 1000))
    except Exception:
        return 0


def _agent(properties: dict[str, Any]) -> str:
    for key in _AGENT_KEYS:
        value = properties.get(key)
        if value:
            return str(value)
    return "unknown"


def _safe_metadata(properties: dict[str, Any]) -> dict[str, Any]:
    """Strip request/response content; surface only user-defined properties."""
    result: dict[str, Any] = {}
    for k, v in properties.items():
        lower = k.lower()
        if any(word in lower for word in ("prompt", "response", "message", "content", "body")):
            continue
        result[k] = v
    return result


def map_webhook(payload: dict[str, Any]) -> dict[str, Any]:
    """Convert a Helicone webhook POST body to the LLMGovernor /v1/events schema.

    Returns a dict ready to POST to ``POST /v1/events``.

    Raises ``ValueError`` if the payload is missing required fields.
    """
    request = payload.get("request")
    if not isinstance(request, dict):
        raise ValueError("payload missing 'request' object")
    response = payload.get("response") or {}
    usage = payload.get("usage") or {}

    req_id: str = request.get("id") or payload.get("id") or ""
    if not req_id:
        raise ValueError("payload missing request.id")

    model: str = request.get("model") or payload.get("model") or ""
    if not model:
        raise ValueError("payload missing model")

    req_ts: str = request.get("created_at", "")
    if not req_ts:
        raise ValueError("payload missing request.created_at")

    resp_ts: str = response.get("created_at", req_ts)
    http_status: int = response.get("status", 200)

    raw_provider: str = request.get("provider") or ""
    provider = _PROVIDER_MAP.get(raw_provider.upper(), raw_provider.lower() or "unknown")

    properties: dict[str, Any] = request.get("properties") or {}

    ts = _parse_iso(req_ts)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)

    return {
        "event_id": req_id,
        "agent": _agent(properties),
        "model": model,
        "provider": provider,
        "ts": ts.isoformat(),
        "tokens_in": int(usage.get("prompt_tokens") or 0),
        "tokens_out": int(usage.get("completion_tokens") or 0),
        "cost_usd": float(usage.get("cost") or 0.0),
        "latency_ms": _latency_ms(req_ts, resp_ts),
        "status": "ok" if 200 <= http_status < 300 else "error",
        "metadata": _safe_metadata(properties),
    }
