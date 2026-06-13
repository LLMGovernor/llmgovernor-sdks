"""Monorepo-level contract tests for the OTel span processor.

These run from the repo root via conftest.py sys.path inserts.
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict
from unittest.mock import MagicMock, patch

from llmgovernor_otel import LLMGovernorSpanProcessor


class DummySpanContext:
    def __init__(self, trace_id, span_id):
        self.trace_id = trace_id
        self.span_id = span_id


class DummySpan:
    def __init__(self, attributes=None, start_time=None, end_time=None, status_ok=True):
        self.attributes = attributes or {}
        self.start_time = start_time
        self.end_time = end_time
        self.status = SimpleNamespace(is_ok=status_ok)
        self.context = DummySpanContext(trace_id="t1", span_id="s1")


def _make_processor(**kwargs):
    """Return (processor, mock_post) with httpx.Client patched."""
    mock_post = MagicMock(return_value=MagicMock(status_code=200))
    mock_client = MagicMock()
    mock_client.post = mock_post
    with patch("llmgovernor.adapters.otel.httpx.Client", return_value=mock_client):
        proc = LLMGovernorSpanProcessor(api_key="llg_test", **kwargs)
    return proc, mock_post


def test_on_end_enqueues_metadata():
    proc, mock_post = _make_processor()

    span = DummySpan(
        attributes={
            "llm.provider": "openai",
            "llm.model": "gpt-4o",
            "llm.input_tokens": 10,
            "llm.output_tokens": 5,
        },
        start_time=0,
        end_time=10_000_000,  # 10ms in nanoseconds
        status_ok=True,
    )

    proc.on_end(span)

    mock_post.assert_called_once()
    payload = mock_post.call_args[1]["json"]
    event = payload["events"][0]
    assert event["provider"] == "openai"
    assert event["model"] == "gpt-4o"
    assert event["input_tokens"] == 10
    assert event["output_tokens"] == 5
    assert event["error"] is False
    assert event["span_id"] == "s1"
    assert event["trace_id"] == "t1"


def test_ignore_flag():
    proc, mock_post = _make_processor()

    span = DummySpan(attributes={"llmgovernor.ignore": True})
    proc.on_end(span)

    assert mock_post.call_count == 0
