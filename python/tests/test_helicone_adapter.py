"""Contract tests for llmgovernor-helicone adapter.

Covers:
1. Field mapping from Helicone webhook payload -> LLMGovernor /v1/events schema.
2. HTTP POST to LLMGovernor ingest endpoint — correct payload shape and auth header.
3. process_webhook() end-to-end with mocked HTTP.
"""

import json
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from llmgovernor_helicone._mapper import map_webhook
from llmgovernor_helicone.adapter import process_webhook, send_event

_FIXTURES = Path(__file__).parent / "helicone_fixtures"


def _load(name: str) -> dict:
    return json.loads((_FIXTURES / name).read_text())


@pytest.fixture
def webhook():
    return _load("helicone_webhook.json")


@pytest.fixture
def error_webhook():
    return _load("helicone_webhook_error.json")


# ── Mapper: field mapping ──────────────────────────────────────────────────────


def test_event_id_mapped_from_request_id(webhook):
    result = map_webhook(webhook)
    assert result["event_id"] == "3c90c3cc-0d44-4b50-8888-8dd25736052a"


def test_model_mapped(webhook):
    result = map_webhook(webhook)
    assert result["model"] == "gpt-4o"


def test_provider_normalised_to_lowercase(webhook):
    result = map_webhook(webhook)
    assert result["provider"] == "openai"


def test_agent_from_helicone_property(webhook):
    result = map_webhook(webhook)
    assert result["agent"] == "support-bot"


def test_agent_fallback_to_plain_agent_key(error_webhook):
    result = map_webhook(error_webhook)
    assert result["agent"] == "billing-bot"


def test_agent_unknown_when_no_properties():
    payload = _load("helicone_webhook.json")
    payload["request"]["properties"] = {}
    result = map_webhook(payload)
    assert result["agent"] == "unknown"


def test_tokens_in_mapped(webhook):
    result = map_webhook(webhook)
    assert result["tokens_in"] == 517


def test_tokens_out_mapped(webhook):
    result = map_webhook(webhook)
    assert result["tokens_out"] == 183


def test_cost_usd_mapped(webhook):
    result = map_webhook(webhook)
    assert abs(result["cost_usd"] - 0.005175) < 1e-9


def test_latency_ms_calculated_from_timestamps(webhook):
    result = map_webhook(webhook)
    # response 2024-01-15T10:30:01.234Z − request 2024-01-15T10:30:00.000Z = 1234 ms
    assert result["latency_ms"] == 1234


def test_status_ok_on_200(webhook):
    result = map_webhook(webhook)
    assert result["status"] == "ok"


def test_status_error_on_4xx(error_webhook):
    result = map_webhook(error_webhook)
    assert result["status"] == "error"


def test_ts_is_iso_string_and_utc(webhook):
    result = map_webhook(webhook)
    ts = result["ts"]
    assert isinstance(ts, str)
    assert "+00:00" in ts or "Z" in ts or ts.endswith("00:00")


def test_ts_value(webhook):
    from datetime import datetime
    result = map_webhook(webhook)
    dt = datetime.fromisoformat(result["ts"])
    assert dt.year == 2024
    assert dt.month == 1
    assert dt.day == 15


# ── Mapper: metadata privacy ───────────────────────────────────────────────────


def test_metadata_does_not_contain_prompt_or_response(webhook):
    result = map_webhook(webhook)
    meta = result["metadata"]
    for key in meta:
        lower = key.lower()
        assert "prompt" not in lower
        assert "response" not in lower
        assert "message" not in lower
        assert "content" not in lower
        assert "body" not in lower


def test_metadata_contains_safe_properties(webhook):
    result = map_webhook(webhook)
    assert "session_id" in result["metadata"]
    assert "environment" in result["metadata"]


def test_helicone_cost_not_in_canonical_payload(webhook):
    result = map_webhook(webhook)
    assert "helicone_cost" not in result


def test_zero_usage_fields_are_safe(error_webhook):
    result = map_webhook(error_webhook)
    assert result["tokens_in"] == 0
    assert result["tokens_out"] == 0
    assert result["cost_usd"] == 0.0


# ── Mapper: required output keys ──────────────────────────────────────────────


def test_result_has_all_required_ingest_keys(webhook):
    required = {
        "event_id", "agent", "model", "provider", "ts",
        "tokens_in", "tokens_out", "cost_usd", "latency_ms", "status", "metadata",
    }
    result = map_webhook(webhook)
    assert required <= result.keys()


# ── Mapper: validation ────────────────────────────────────────────────────────


def test_missing_request_raises():
    with pytest.raises(ValueError, match="request"):
        map_webhook({"usage": {}})


def test_missing_request_id_raises():
    payload = _load("helicone_webhook.json")
    del payload["request"]["id"]
    payload.pop("id", None)
    with pytest.raises(ValueError, match="request.id"):
        map_webhook(payload)


def test_missing_model_raises():
    payload = _load("helicone_webhook.json")
    del payload["request"]["model"]
    payload.pop("model", None)
    with pytest.raises(ValueError, match="model"):
        map_webhook(payload)


# ── send_event: HTTP contract (mocked urllib) ──────────────────────────────────


def _mock_urlopen(status: int = 200):
    """Return a context-manager mock that simulates urlopen()."""
    resp_mock = MagicMock()
    resp_mock.__enter__ = lambda s: s
    resp_mock.__exit__ = MagicMock(return_value=False)
    resp_mock.status = status
    return resp_mock


def test_send_event_posts_correct_json(webhook):
    event = map_webhook(webhook)
    captured = {}

    def fake_urlopen(req, timeout=10):
        captured["url"] = req.full_url
        captured["method"] = req.method
        captured["headers"] = dict(req.headers)
        captured["body"] = json.loads(req.data)
        return _mock_urlopen()

    with patch("llmgovernor_helicone.adapter.urlopen", side_effect=fake_urlopen):
        send_event(event, api_key="llg_test_key_123")

    assert captured["method"] == "POST"
    assert captured["url"] == "https://api.llmgovernor.ai/v1/events"


def test_send_event_includes_bearer_auth(webhook):
    event = map_webhook(webhook)
    captured_auth = {}

    def fake_urlopen(req, timeout=10):
        captured_auth["auth"] = req.get_header("Authorization")
        return _mock_urlopen()

    with patch("llmgovernor_helicone.adapter.urlopen", side_effect=fake_urlopen):
        send_event(event, api_key="llg_test_key_abc")

    assert captured_auth["auth"] == "Bearer llg_test_key_abc"


def test_send_event_content_type_is_json(webhook):
    event = map_webhook(webhook)
    captured = {}

    def fake_urlopen(req, timeout=10):
        captured["ct"] = req.get_header("Content-type")
        return _mock_urlopen()

    with patch("llmgovernor_helicone.adapter.urlopen", side_effect=fake_urlopen):
        send_event(event, api_key="llg_k")

    assert captured["ct"] == "application/json"


def test_send_event_payload_contains_event_fields(webhook):
    event = map_webhook(webhook)
    captured_body = {}

    def fake_urlopen(req, timeout=10):
        captured_body["body"] = json.loads(req.data)
        return _mock_urlopen()

    with patch("llmgovernor_helicone.adapter.urlopen", side_effect=fake_urlopen):
        send_event(event, api_key="llg_k")

    body = captured_body["body"]
    assert body["event_id"] == event["event_id"]
    assert body["model"] == "gpt-4o"
    assert body["provider"] == "openai"
    assert body["tokens_in"] == 517
    assert body["tokens_out"] == 183
    assert body["status"] == "ok"


def test_send_event_uses_custom_ingest_url(webhook):
    event = map_webhook(webhook)
    captured = {}

    def fake_urlopen(req, timeout=10):
        captured["url"] = req.full_url
        return _mock_urlopen()

    with patch("llmgovernor_helicone.adapter.urlopen", side_effect=fake_urlopen):
        send_event(event, api_key="k", ingest_url="https://custom.example.com/v1/events")

    assert captured["url"] == "https://custom.example.com/v1/events"


# ── process_webhook: end-to-end ───────────────────────────────────────────────


def test_process_webhook_maps_and_posts(webhook):
    posted_events = []

    def fake_urlopen(req, timeout=10):
        posted_events.append(json.loads(req.data))
        return _mock_urlopen()

    with patch("llmgovernor_helicone.adapter.urlopen", side_effect=fake_urlopen):
        returned = process_webhook(webhook, api_key="llg_k")

    assert len(posted_events) == 1
    posted = posted_events[0]

    # Payload shape check
    assert posted["event_id"] == "3c90c3cc-0d44-4b50-8888-8dd25736052a"
    assert posted["agent"] == "support-bot"
    assert posted["model"] == "gpt-4o"

    # Return value is the mapped event
    assert returned["event_id"] == posted["event_id"]


def test_process_webhook_error_payload(error_webhook):
    posted_events = []

    def fake_urlopen(req, timeout=10):
        posted_events.append(json.loads(req.data))
        return _mock_urlopen()

    with patch("llmgovernor_helicone.adapter.urlopen", side_effect=fake_urlopen):
        result = process_webhook(error_webhook, api_key="llg_k")

    assert result["status"] == "error"
    assert result["agent"] == "billing-bot"
    assert posted_events[0]["status"] == "error"


def test_process_webhook_raises_on_missing_request():
    with pytest.raises(ValueError, match="request"):
        process_webhook({"usage": {}}, api_key="llg_k")
