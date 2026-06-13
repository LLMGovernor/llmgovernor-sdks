"""Contract tests for LLMGovernorSpanProcessor.

Tests create mock spans with LLM attributes and assert that:
- payloads are posted to /v1/events with correct structure
- non-LLM spans are silently skipped
- spans with llmgovernor.ignore=True are skipped
- GenAI semantic conventions are also handled
"""
from __future__ import annotations

import sys
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

# Ensure the package root is importable when running from this directory.
_PKG_ROOT = Path(__file__).resolve().parents[1]
if str(_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT))

from llmgovernor.adapters.otel import LLMGovernorSpanProcessor


# ---------------------------------------------------------------------------
# Helpers / fakes
# ---------------------------------------------------------------------------


class _SpanContext:
    def __init__(self, trace_id: str = "trace-abc", span_id: str = "span-123"):
        self.trace_id = trace_id
        self.span_id = span_id


class _Status:
    def __init__(self, is_ok: bool = True):
        self.is_ok = is_ok


class _Span:
    """Minimal ReadableSpan-like object for testing."""

    def __init__(
        self,
        attributes: Dict[str, Any] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        status_ok: bool = True,
        span_id: str = "span-123",
        trace_id: str = "trace-abc",
    ):
        self.attributes = attributes or {}
        self.start_time = start_time
        self.end_time = end_time
        self.status = _Status(is_ok=status_ok)
        self.context = _SpanContext(trace_id=trace_id, span_id=span_id)


def _make_processor(**kwargs) -> tuple[LLMGovernorSpanProcessor, MagicMock]:
    """Return (processor, mock_client.post) with httpx.Client patched."""
    mock_post = MagicMock(return_value=MagicMock(status_code=200))
    mock_client = MagicMock()
    mock_client.post = mock_post
    with patch("llmgovernor.adapters.otel.httpx.Client", return_value=mock_client):
        proc = LLMGovernorSpanProcessor(api_key="llg_test", **kwargs)
    return proc, mock_post


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestLLMGovernorSpanProcessorContract:
    def test_llm_span_posts_to_v1_events(self):
        """LLM spans must POST to /v1/events with correct payload structure."""
        proc, mock_post = _make_processor()
        span = _Span(
            attributes={
                "llm.provider": "openai",
                "llm.model": "gpt-4o",
                "llm.input_tokens": 100,
                "llm.output_tokens": 50,
            },
            start_time=0,
            end_time=1_000_000_000,  # 1 second in nanoseconds
        )
        proc.on_end(span)

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert call_kwargs[0][0] == "/v1/events"
        payload = call_kwargs[1]["json"]
        assert "events" in payload
        event = payload["events"][0]
        assert event["provider"] == "openai"
        assert event["model"] == "gpt-4o"
        assert event["input_tokens"] == 100
        assert event["output_tokens"] == 50
        assert event["latency_ms"] == pytest.approx(1000.0)
        assert event["error"] is False
        assert event["span_id"] == "span-123"
        assert event["trace_id"] == "trace-abc"

    def test_non_llm_span_is_skipped(self):
        """Spans without LLM attributes must not trigger any POST."""
        proc, mock_post = _make_processor()
        span = _Span(
            attributes={"http.method": "GET", "http.url": "https://example.com"},
        )
        proc.on_end(span)
        mock_post.assert_not_called()

    def test_ignore_flag_suppresses_forwarding(self):
        """Spans tagged llmgovernor.ignore=True must be silently dropped."""
        proc, mock_post = _make_processor()
        span = _Span(
            attributes={
                "llm.model": "gpt-4o",
                "llmgovernor.ignore": True,
            }
        )
        proc.on_end(span)
        mock_post.assert_not_called()

    def test_gen_ai_semantic_conventions(self):
        """Newer gen_ai.* attributes are recognized and mapped correctly."""
        proc, mock_post = _make_processor()
        span = _Span(
            attributes={
                "gen_ai.system": "openai",
                "gen_ai.request.model": "gpt-4o-mini",
                "gen_ai.usage.prompt_tokens": 80,
                "gen_ai.usage.completion_tokens": 40,
            },
            start_time=0,
            end_time=500_000_000,
        )
        proc.on_end(span)

        mock_post.assert_called_once()
        event = mock_post.call_args[1]["json"]["events"][0]
        assert event["provider"] == "openai"
        assert event["model"] == "gpt-4o-mini"
        assert event["input_tokens"] == 80
        assert event["output_tokens"] == 40
        assert event["latency_ms"] == pytest.approx(500.0)

    def test_error_span_sets_error_flag(self):
        """Failed spans (status not OK) must have error=True in the payload."""
        proc, mock_post = _make_processor()
        span = _Span(
            attributes={"llm.model": "gpt-4o"},
            status_ok=False,
        )
        proc.on_end(span)

        mock_post.assert_called_once()
        event = mock_post.call_args[1]["json"]["events"][0]
        assert event["error"] is True

    def test_missing_timestamps_yield_null_latency(self):
        """Spans without timestamps should have latency_ms=None."""
        proc, mock_post = _make_processor()
        span = _Span(
            attributes={"llm.model": "gpt-4o"},
            start_time=None,
            end_time=None,
        )
        proc.on_end(span)

        event = mock_post.call_args[1]["json"]["events"][0]
        assert event["latency_ms"] is None

    def test_http_error_does_not_raise(self):
        """Processor must never propagate HTTP errors to the caller."""
        mock_post = MagicMock(side_effect=Exception("network down"))
        mock_client = MagicMock()
        mock_client.post = mock_post
        with patch("llmgovernor.adapters.otel.httpx.Client", return_value=mock_client):
            proc = LLMGovernorSpanProcessor(api_key="llg_test")

        span = _Span(attributes={"llm.model": "gpt-4o"})
        # Must not raise
        proc.on_end(span)

    def test_on_start_is_no_op(self):
        """on_start must return without error (and not post anything)."""
        proc, mock_post = _make_processor()
        span = _Span(attributes={"llm.model": "gpt-4o"})
        proc.on_start(span, parent_context=None)
        mock_post.assert_not_called()

    def test_force_flush_returns_true(self):
        proc, _ = _make_processor()
        assert proc.force_flush() is True

    def test_shutdown_closes_client(self):
        mock_client = MagicMock()
        with patch("llmgovernor.adapters.otel.httpx.Client", return_value=mock_client):
            proc = LLMGovernorSpanProcessor(api_key="llg_test")
        proc.shutdown()
        mock_client.close.assert_called_once()

    def test_custom_endpoint(self):
        """Custom endpoint is used when specified."""
        mock_client_cls = MagicMock()
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        with patch("llmgovernor.adapters.otel.httpx.Client", mock_client_cls):
            LLMGovernorSpanProcessor(
                api_key="llg_test",
                endpoint="https://custom.llmgovernor.ai",
            )
        call_kwargs = mock_client_cls.call_args[1]
        assert "custom.llmgovernor.ai" in call_kwargs["base_url"]
