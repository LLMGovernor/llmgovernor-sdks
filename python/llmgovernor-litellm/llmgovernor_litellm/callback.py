from __future__ import annotations

import time
from typing import Any, Dict, Optional

import llmgovernor
from llmgovernor._transport import Transport
from litellm.integrations.custom_logger import CustomLogger


def _extract_usage(response_obj: Any) -> Dict[str, Optional[int]]:
    usage = getattr(response_obj, "usage", None)
    if usage is None:
        return {"input_tokens": None, "output_tokens": None}
    prompt_tokens = getattr(usage, "prompt_tokens", None)
    completion_tokens = getattr(usage, "completion_tokens", None)
    return {"input_tokens": prompt_tokens, "output_tokens": completion_tokens}


def _extract_model(kwargs: Dict[str, Any], response_obj: Any) -> Optional[str]:
    # Prefer explicit model kwarg, fallback to response model attr
    model = kwargs.get("model")
    if model:
        return model
    return getattr(response_obj, "model", None)


def _extract_latency_ms(start_time: float, end_time: float) -> float:
    return (end_time - start_time) * 1000.0


class LLMGovernorHandler(CustomLogger):
    """LiteLLM CustomLogger that forwards metadata-only events to LLMGovernor."""

    def __init__(self, transport: Optional[Transport] = None):
        super().__init__()
        self.transport = transport or llmgovernor.get_transport()

    def _enqueue_event(
        self,
        kwargs: Dict[str, Any],
        response_obj: Any,
        start_time: float,
        end_time: float,
        error: bool,
    ) -> None:
        if self.transport is None:
            return
        usage = _extract_usage(response_obj)
        model = _extract_model(kwargs, response_obj)
        event: Dict[str, Any] = {
            "provider": "litellm",
            "model": model,
            "input_tokens": usage["input_tokens"],
            "output_tokens": usage["output_tokens"],
            "latency_ms": _extract_latency_ms(start_time, end_time),
            "error": error,
        }
        # Explicitly avoid adding prompt/response content or messages
        self.transport.enqueue(event)

    def log_success_event(self, kwargs: Dict[str, Any], response_obj: Any, start_time: float, end_time: float):
        self._enqueue_event(kwargs, response_obj, start_time, end_time, error=False)

    def log_failure_event(self, kwargs: Dict[str, Any], response_obj: Any, start_time: float, end_time: float):
        self._enqueue_event(kwargs, response_obj, start_time, end_time, error=True)

    async def async_log_success_event(self, kwargs: Dict[str, Any], response_obj: Any, start_time: float, end_time: float):
        self._enqueue_event(kwargs, response_obj, start_time, end_time, error=False)

    async def async_log_failure_event(self, kwargs: Dict[str, Any], response_obj: Any, start_time: float, end_time: float):
        self._enqueue_event(kwargs, response_obj, start_time, end_time, error=True)
