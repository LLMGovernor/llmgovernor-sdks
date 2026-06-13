"""OpenTelemetry SpanProcessor that forwards LLM spans to LLMGovernor /v1/events.

Usage::

    from llmgovernor.adapters.otel import LLMGovernorSpanProcessor
    tracer_provider.add_span_processor(LLMGovernorSpanProcessor(api_key="llg_..."))
    # Done — LLM spans now forward to LLMGovernor
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import httpx
from opentelemetry.context import Context
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace import SpanProcessor

__all__ = ["LLMGovernorSpanProcessor"]

_DEFAULT_ENDPOINT = "https://api.llmgovernor.ai"

logger = logging.getLogger(__name__)

# OpenTelemetry semantic convention attribute names for LLM / GenAI spans.
# Covers both the legacy llm.* convention and the newer gen_ai.* convention.
_LLM_ATTRIBUTE_KEYS = frozenset(
    [
        "llm.model",
        "llm.provider",
        "llm.prompt",
        "llm.completion",
        "llm.token_count.prompt",
        "llm.token_count.completion",
        "llm.token_count.total",
        "llm.input_tokens",
        "llm.output_tokens",
        # GenAI semantic conventions (newer)
        "gen_ai.request.model",
        "gen_ai.system",
        "gen_ai.usage.prompt_tokens",
        "gen_ai.usage.completion_tokens",
    ]
)


def _is_llm_span(attrs: Dict[str, Any]) -> bool:
    """Return True when the span carries any known LLM-specific attribute."""
    return bool(_LLM_ATTRIBUTE_KEYS & attrs.keys())


def _to_ms(nanoseconds: int) -> float:
    """Convert nanoseconds (OTel standard) to milliseconds."""
    return nanoseconds / 1_000_000


class LLMGovernorSpanProcessor(SpanProcessor):
    """Forwards completed LLM spans to LLMGovernor.

    Constructor args:
        api_key: LLMGovernor API key (``llg_...``).
        endpoint: Base URL of the LLMGovernor ingest API.
            Defaults to ``https://api.llmgovernor.ai``.

    Example::

        from llmgovernor.adapters.otel import LLMGovernorSpanProcessor
        tracer_provider.add_span_processor(
            LLMGovernorSpanProcessor(api_key="llg_...")
        )
    """

    def __init__(
        self,
        api_key: str,
        endpoint: str = _DEFAULT_ENDPOINT,
    ) -> None:
        self._api_key = api_key
        self._endpoint = endpoint.rstrip("/")
        self._client = httpx.Client(
            base_url=self._endpoint,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=5.0,
        )

    # ------------------------------------------------------------------
    # SpanProcessor interface
    # ------------------------------------------------------------------

    def on_start(
        self,
        span: ReadableSpan,
        parent_context: Optional[Context] = None,
    ) -> None:
        """Called when a span starts — nothing to do here."""

    def on_end(self, span: ReadableSpan) -> None:
        """Called when a span ends. Forwards LLM spans to LLMGovernor."""
        attrs: Dict[str, Any] = dict(span.attributes or {})

        # Skip spans explicitly marked to ignore.
        if attrs.get("llmgovernor.ignore"):
            return

        # Only forward spans that carry LLM-specific attributes.
        if not _is_llm_span(attrs):
            return

        try:
            self._forward(span, attrs)
        except Exception as exc:  # never raise; processors must be fault-tolerant
            logger.debug("LLMGovernorSpanProcessor: forward failed: %s", exc)

    def shutdown(self) -> None:
        """Flush and close the HTTP client."""
        try:
            self._client.close()
        except Exception:
            pass

    def force_flush(self, timeout_millis: int = 30_000) -> bool:
        """Synchronous flush — httpx sends synchronously, so this is a no-op."""
        return True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_payload(
        self,
        span: ReadableSpan,
        attrs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Serialize a span into the LLMGovernor event payload schema."""
        latency_ms: Optional[float] = None
        if span.start_time is not None and span.end_time is not None:
            latency_ms = _to_ms(span.end_time - span.start_time)

        # Resolve token counts across both semantic convention families.
        input_tokens = (
            attrs.get("llm.input_tokens")
            or attrs.get("llm.token_count.prompt")
            or attrs.get("gen_ai.usage.prompt_tokens")
        )
        output_tokens = (
            attrs.get("llm.output_tokens")
            or attrs.get("llm.token_count.completion")
            or attrs.get("gen_ai.usage.completion_tokens")
        )
        model = attrs.get("llm.model") or attrs.get("gen_ai.request.model")
        provider = (
            attrs.get("llm.provider")
            or attrs.get("gen_ai.system")
            or "otel"
        )

        return {
            "provider": provider,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "latency_ms": latency_ms,
            "error": not span.status.is_ok if span.status is not None else False,
            "span_id": str(span.context.span_id) if span.context else None,
            "trace_id": str(span.context.trace_id) if span.context else None,
        }

    def _forward(self, span: ReadableSpan, attrs: Dict[str, Any]) -> None:
        payload = self._build_payload(span, attrs)
        self._client.post("/v1/events", json={"events": [payload]})
