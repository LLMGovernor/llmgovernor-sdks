"""
Field-mapping, processor, and HTTP contract tests for llmgovernor-otel.

Contract tests feed synthetic spans through LLMGovSpanProcessor, mock the
/v1/events ingest endpoint, and assert the forwarded payload shape and auth.
"""

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from llmgovernor_otel import LLMGovSpanProcessor, from_otel_span, is_llm_span
from llmgovernor_otel._mapper import _span_id_to_event_id

_FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> dict[str, Any]:
    return json.loads((_FIXTURES / name).read_text())


# -- Fixtures ------------------------------------------------------------------


@pytest.fixture
def llm_span():
    return _load("otel_span_llm.json")


@pytest.fixture
def non_llm_span():
    return _load("otel_span_non_llm.json")


@pytest.fixture
def error_span():
    return _load("otel_span_error.json")


# -- is_llm_span ---------------------------------------------------------------


def test_llm_span_detected(llm_span):
    assert is_llm_span(llm_span) is True


def test_non_llm_span_rejected(non_llm_span):
    assert is_llm_span(non_llm_span) is False


def test_span_without_attributes_is_not_llm():
    assert is_llm_span({"name": "something", "attributes": {}}) is False


# -- Field mappings ------------------------------------------------------------


def test_event_id_from_span_id(llm_span):
    result = from_otel_span(llm_span)
    assert result["event_id"] == "51581bf3cb55c13"


def test_event_id_strips_only_literal_0x_prefix():
    assert _span_id_to_event_id("0x051581bf3cb55c13") == "51581bf3cb55c13"
    assert _span_id_to_event_id("0xabcd1234") == "abcd1234"
    assert _span_id_to_event_id("xabc123") == "xabc123"  # no 0x prefix -> untouched


def test_model_from_request_model(llm_span):
    assert from_otel_span(llm_span)["model"] == "gpt-4o"


def test_model_fallback_to_response_model():
    span = _load("otel_span_llm.json")
    del span["attributes"]["gen_ai.request.model"]
    assert from_otel_span(span)["model"] == "gpt-4o-2024-08-06"


def test_provider_from_gen_ai_system(llm_span):
    assert from_otel_span(llm_span)["provider"] == "openai"


def test_provider_anthropic(error_span):
    assert from_otel_span(error_span)["provider"] == "anthropic"


def test_agent_from_llmgovernor_attribute(llm_span):
    assert from_otel_span(llm_span)["agent"] == "support-bot"


def test_agent_fallback_to_service_name():
    span = _load("otel_span_llm.json")
    del span["attributes"]["llmgovernor.agent"]
    assert from_otel_span(span)["agent"] == "my-api"


def test_agent_fallback_to_span_name():
    span = _load("otel_span_llm.json")
    del span["attributes"]["llmgovernor.agent"]
    del span["attributes"]["service.name"]
    assert from_otel_span(span)["agent"] == "openai.chat"


def test_tokens_in(llm_span):
    assert from_otel_span(llm_span)["tokens_in"] == 517


def test_tokens_out(llm_span):
    assert from_otel_span(llm_span)["tokens_out"] == 183


def test_latency_ms(llm_span):
    assert from_otel_span(llm_span)["latency_ms"] == 1234


def test_status_ok(llm_span):
    assert from_otel_span(llm_span)["status"] == "ok"


def test_status_error(error_span):
    assert from_otel_span(error_span)["status"] == "error"


def test_status_unset_is_ok(llm_span):
    # UNSET is OTel's default ("no status set") and must NOT be treated as an
    # error — otherwise the majority of successful spans inflate error_rate.
    llm_span["status"] = {"status_code": "UNSET"}
    assert from_otel_span(llm_span)["status"] == "ok"


def test_status_missing_is_ok(llm_span):
    llm_span.pop("status", None)
    assert from_otel_span(llm_span)["status"] == "ok"


def test_ts_is_timezone_aware(llm_span):
    assert from_otel_span(llm_span)["ts"].tzinfo is not None


def test_metadata_contains_trace_id(llm_span):
    meta = from_otel_span(llm_span)["metadata"]
    assert meta["trace_id"] == "0x5b8aa5a2d2c872e8321cf37308d69df2"


def test_metadata_contains_span_name(llm_span):
    assert from_otel_span(llm_span)["metadata"]["span_name"] == "openai.chat"


# -- Metadata-only contract ----------------------------------------------------


def test_no_prompt_response_in_payload(llm_span):
    result = from_otel_span(llm_span)
    for key in result:
        assert "prompt" not in key.lower()
        assert "response" not in key.lower()
        assert "message" not in key.lower()
    for key in result.get("metadata", {}):
        assert "prompt" not in key.lower()
        assert "response" not in key.lower()


def test_result_has_all_required_kwargs(llm_span):
    required = {
        "event_id", "agent", "model", "provider", "ts",
        "tokens_in", "tokens_out", "cost_usd", "latency_ms", "status", "metadata",
    }
    assert required <= from_otel_span(llm_span).keys()


# -- Validation ----------------------------------------------------------------


def test_missing_span_id_raises():
    span = _load("otel_span_llm.json")
    span["context"] = {}
    with pytest.raises(ValueError, match="span_id"):
        from_otel_span(span)


def test_missing_model_raises():
    span = _load("otel_span_llm.json")
    del span["attributes"]["gen_ai.request.model"]
    del span["attributes"]["gen_ai.response.model"]
    with pytest.raises(ValueError, match="model"):
        from_otel_span(span)


def test_missing_start_time_raises():
    span = _load("otel_span_llm.json")
    del span["start_time"]
    with pytest.raises(ValueError, match="start_time"):
        from_otel_span(span)


# -- LLMGovSpanProcessor (mock client) ----------------------------------------


def test_processor_calls_track_for_llm_span(llm_span):
    client = MagicMock()
    proc = LLMGovSpanProcessor(client)
    proc.on_end(llm_span)
    client.track.assert_called_once()
    kwargs = client.track.call_args[1]
    assert kwargs["model"] == "gpt-4o"


def test_processor_ignores_non_llm_span(non_llm_span):
    client = MagicMock()
    proc = LLMGovSpanProcessor(client)
    proc.on_end(non_llm_span)
    client.track.assert_not_called()


def test_processor_swallows_mapping_errors():
    client = MagicMock()
    proc = LLMGovSpanProcessor(client)
    proc.on_end({"attributes": {"gen_ai.system": "openai"}})  # missing span_id
    client.track.assert_not_called()


def test_processor_swallows_client_exceptions(llm_span):
    client = MagicMock()
    client.track.side_effect = RuntimeError("network down")
    proc = LLMGovSpanProcessor(client)
    proc.on_end(llm_span)  # must not raise


def test_processor_on_start_is_noop(llm_span):
    client = MagicMock()
    proc = LLMGovSpanProcessor(client)
    proc.on_start(llm_span)
    client.track.assert_not_called()


# -- HTTP contract tests (stdlib HTTPServer) -----------------------------------
#
# Spin up a real HTTP server on localhost, create a real llmgovernor.Client,
# wire it through LLMGovSpanProcessor, and assert:
#   1. The correct HTTP method and path are called.
#   2. The Authorization header carries the API key.
#   3. The payload matches the IngestRequest schema fields.
#   4. No prompt/response content appears in the payload.


class _RecordingHandler(BaseHTTPRequestHandler):
    """Captures requests into a shared list; always returns 202."""

    captured: list[dict[str, Any]] = []

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        _RecordingHandler.captured.append({
            "path": self.path,
            "auth": self.headers.get("Authorization", ""),
            "body": json.loads(body) if body else {},
        })
        self.send_response(202)
        self.end_headers()
        self.wfile.write(b'{"id":"00000000-0000-0000-0000-000000000001","event_id":"x","duplicate":false}')

    def log_message(self, *args: Any) -> None:  # suppress output
        pass


@pytest.fixture(scope="module")
def mock_ingest_server():
    """Start a local HTTP server that records /v1/events calls."""
    _RecordingHandler.captured = []
    server = HTTPServer(("127.0.0.1", 0), _RecordingHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}", _RecordingHandler.captured
    server.shutdown()


def test_contract_payload_shape_and_auth(mock_ingest_server, llm_span):
    """Full round-trip: processor -> real HTTP -> assert schema and auth."""
    import importlib
    try:
        llmgovernor = importlib.import_module("llmgovernor")
    except ImportError:
        pytest.skip("llmgovernor package not installed")

    base_url, captured = mock_ingest_server
    api_key = "llmgov_test_key"
    client = llmgovernor.Client(api_key=api_key, base_url=base_url, flush_on_exit=False)
    proc = LLMGovSpanProcessor(client)

    proc.on_end(llm_span)
    client.flush(timeout=5.0)

    assert len(captured) >= 1, "No request received by mock server"
    req = captured[-1]

    # Path: POST /v1/events
    assert req["path"] == "/v1/events", f"Unexpected path: {req['path']}"

    # Auth header carries the API key as Bearer token
    assert req["auth"] == f"Bearer {api_key}", f"Bad auth: {req['auth']}"

    body = req["body"]

    # IngestRequest required fields (matching api/app/schemas/event.py)
    for field in ("event_id", "agent", "model", "provider", "ts",
                  "tokens_in", "tokens_out", "cost_usd", "latency_ms", "status"):
        assert field in body, f"Missing required field: {field}"

    # Correct values mapped from the span fixture
    assert body["model"] == "gpt-4o"
    assert body["provider"] == "openai"
    assert body["agent"] == "support-bot"
    assert body["tokens_in"] == 517
    assert body["tokens_out"] == 183
    assert body["status"] == "ok"
    assert body["latency_ms"] == 1234

    # Metadata-only: no prompt or response text
    for key in body:
        assert "prompt" not in key.lower()
        assert "response" not in key.lower()
        assert "message" not in key.lower()

    client.close(timeout=2.0)


def test_contract_non_llm_span_not_forwarded(mock_ingest_server, non_llm_span):
    """Non-LLM spans must not produce any HTTP call."""
    import importlib
    try:
        llmgovernor = importlib.import_module("llmgovernor")
    except ImportError:
        pytest.skip("llmgovernor package not installed")

    base_url, captured = mock_ingest_server
    before = len(captured)
    api_key = "llmgov_test_key"
    client = llmgovernor.Client(api_key=api_key, base_url=base_url, flush_on_exit=False)
    proc = LLMGovSpanProcessor(client)

    proc.on_end(non_llm_span)
    client.flush(timeout=2.0)

    assert len(captured) == before, "Non-LLM span should not produce an HTTP call"
    client.close(timeout=2.0)


def test_contract_error_span_status_field(mock_ingest_server, error_span):
    """Error spans must carry status='error' in the forwarded payload."""
    import importlib
    try:
        llmgovernor = importlib.import_module("llmgovernor")
    except ImportError:
        pytest.skip("llmgovernor package not installed")

    base_url, captured = mock_ingest_server
    api_key = "llmgov_test_key"
    client = llmgovernor.Client(api_key=api_key, base_url=base_url, flush_on_exit=False)
    proc = LLMGovSpanProcessor(client)

    proc.on_end(error_span)
    client.flush(timeout=5.0)

    assert len(captured) >= 1
    req = captured[-1]
    assert req["body"]["status"] == "error"
    client.close(timeout=2.0)
