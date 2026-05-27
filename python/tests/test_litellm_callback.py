import json
import time
from pathlib import Path
from unittest.mock import MagicMock

import anyio
import pytest

from llmgovernor_litellm.callback import LLMGovernorHandler


FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str):
    return json.loads((FIXTURES / name).read_text())


class DummyTransport:
    def __init__(self):
        self.events = []

    def enqueue(self, event):
        self.events.append(event)


@pytest.fixture
def handler():
    return LLMGovernorHandler(transport=DummyTransport())


def test_success_handler_emits_event(handler):
    kwargs = {"model": "gpt-3.5-turbo-0125"}
    response = MagicMock()
    usage = MagicMock()
    usage.prompt_tokens = 10
    usage.completion_tokens = 5
    response.usage = usage
    start = time.time()
    end = start + 0.1

    handler.log_success_event(kwargs, response, start, end)

    assert len(handler.transport.events) == 1
    event = handler.transport.events[0]
    assert event["model"] == "gpt-3.5-turbo-0125"
    assert event["input_tokens"] == 10
    assert event["output_tokens"] == 5
    assert event["error"] is False
    assert "messages" not in event
    assert "content" not in event


def test_failure_handler_emits_event(handler):
    kwargs = {"model": "claude-3-opus-20240229"}
    response = MagicMock()
    usage = MagicMock()
    usage.prompt_tokens = 12
    usage.completion_tokens = 7
    response.usage = usage
    start = time.time()
    end = start + 0.2

    handler.log_failure_event(kwargs, response, start, end)

    assert len(handler.transport.events) == 1
    event = handler.transport.events[0]
    assert event["model"] == "claude-3-opus-20240229"
    assert event["input_tokens"] == 12
    assert event["output_tokens"] == 7
    assert event["error"] is True
    assert "messages" not in event
    assert "content" not in event


def test_no_content_in_event(handler):
    kwargs = {"model": "gpt-3.5-turbo-0125", "messages": [{"role": "user", "content": "secret"}]}
    response = MagicMock()
    response.usage = None
    start = time.time()
    end = start + 0.05

    handler.log_success_event(kwargs, response, start, end)

    event = handler.transport.events[0]
    assert "messages" not in event
    assert "content" not in event


@pytest.mark.anyio
async def test_async_success_handler():
    transport = DummyTransport()
    handler = LLMGovernorHandler(transport=transport)
    kwargs = {"model": "gpt-3.5-turbo-0125"}
    response = MagicMock()
    usage = MagicMock()
    usage.prompt_tokens = 9
    usage.completion_tokens = 4
    response.usage = usage
    start = time.time()
    end = start + 0.15

    await handler.async_log_success_event(kwargs, response, start, end)

    assert len(transport.events) == 1
    event = transport.events[0]
    assert event["model"] == "gpt-3.5-turbo-0125"
    assert event["input_tokens"] == 9
    assert event["output_tokens"] == 4
    assert event["error"] is False
    assert "messages" not in event
    assert "content" not in event
