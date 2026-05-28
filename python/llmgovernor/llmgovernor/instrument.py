"""Auto-instrumentation for AI SDKs.

`instrument()` monkey-patches the chat/completion methods on OpenAI,
Anthropic, and Bedrock client *classes*. After it runs, every client
instance — including ones constructed after the call — will report cost
events to LLMGovernor automatically.

Idempotent: calling instrument() twice returns the existing client and
does not re-patch (each provider check has its own guard flag too).

Why class-level patching: the `wrap_*_client(instance)` helpers in
llmgovernor.patches.* patch a single instance. instrument() patches the
class method so all instances inherit the wrap. Same observability with
zero per-construction wiring.
"""

import functools
import logging
import os
import sys
import threading
import time
from typing import Optional

from .client import LLMGovernorClient
from .metadata import get_metadata
from .pricing import calculate_cost
from .types import CostEvent

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_state: dict = {
    "client": None,
    "patched": set(),  # {"openai", "anthropic", "bedrock"}
}


def _current_client() -> Optional[LLMGovernorClient]:
    return _state["client"]


def _default_fleet_name() -> str:
    """Best-effort process name (argv[0] basename), fallback to 'agent'."""
    try:
        argv0 = sys.argv[0] or ""
        return os.path.basename(argv0).split(".")[0] or "agent"
    except Exception:
        return "agent"


def _resolve_agent_name(default: str) -> str:
    md = get_metadata()
    return str(md.get("agent_id") or md.get("agent_name") or default)


def instrument(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    fleet_name: Optional[str] = None,
) -> LLMGovernorClient:
    """Globally auto-instrument all installed LLM SDKs.

    Args:
        api_key: LLMGovernor API key. Defaults to LLMGOVERNOR_API_KEY env var.
        base_url: Override the API base (mostly for staging / testing).
        fleet_name: Default agent_name for events that don't have one set
                    via set_metadata({"agent_id": ...}). Defaults to the
                    process name.

    Returns:
        The LLMGovernorClient. Call .flush() before process exit if your
        run is short-lived (the buffer flushes lazily otherwise).
    """
    with _lock:
        existing = _state["client"]
        if existing is not None:
            return existing

        api_key = api_key or os.environ.get("LLMGOVERNOR_API_KEY")
        if not api_key:
            raise RuntimeError(
                "LLMGOVERNOR_API_KEY not set. Pass api_key= explicitly or export "
                "LLMGOVERNOR_API_KEY in your environment."
            )

        client = LLMGovernorClient(
            api_key=api_key,
            base_url=base_url or "https://api.llmgovernor.ai",
            default_agent_name=fleet_name or _default_fleet_name(),
        )
        _state["client"] = client

        for provider, patcher in (
            ("openai", _patch_openai),
            ("anthropic", _patch_anthropic),
            ("bedrock", _patch_bedrock),
        ):
            try:
                patcher()
                _state["patched"].add(provider)
                logger.info("llmgovernor: instrumented %s", provider)
            except ImportError:
                pass  # provider library not installed — skip silently
            except Exception as e:
                logger.warning("llmgovernor: failed to instrument %s: %s", provider, e)

        return client


# ── Provider-specific class patches ────────────────────────────────


def _patch_openai() -> None:
    """Patch openai.resources.chat.completions.Completions.create."""
    from openai.resources.chat.completions import Completions  # type: ignore

    if getattr(Completions, "_llmgovernor_patched", False):
        return

    original_create = Completions.create

    @functools.wraps(original_create)
    def patched(self, *args, **kwargs):
        client = _current_client()
        if client is None:
            return original_create(self, *args, **kwargs)

        agent = _resolve_agent_name(client.default_agent_name)
        meta = get_metadata()
        meta.pop("agent_id", None)
        meta.pop("agent_name", None)
        start = time.time()
        try:
            response = original_create(self, *args, **kwargs)
            latency_ms = (time.time() - start) * 1000.0
            model = getattr(response, "model", "") or kwargs.get("model", "")
            usage = getattr(response, "usage", None)
            in_t = getattr(usage, "prompt_tokens", 0) if usage else 0
            out_t = getattr(usage, "completion_tokens", 0) if usage else 0
            total_t = getattr(usage, "total_tokens", in_t + out_t) if usage else in_t + out_t

            client.queue_event(
                CostEvent(
                    agent_name=agent,
                    model=model,
                    provider="openai",
                    input_tokens=in_t,
                    output_tokens=out_t,
                    total_tokens=total_t,
                    cost_usd=calculate_cost(model, in_t, out_t),
                    latency_ms=latency_ms,
                    status="ok",
                    metadata=meta or None,
                )
            )
            return response
        except Exception as e:
            latency_ms = (time.time() - start) * 1000.0
            client.queue_event(
                CostEvent(
                    agent_name=agent,
                    model=kwargs.get("model", ""),
                    provider="openai",
                    input_tokens=0,
                    output_tokens=0,
                    total_tokens=0,
                    cost_usd=0.0,
                    latency_ms=latency_ms,
                    status="error",
                    metadata={**meta, "error": str(e)},
                )
            )
            raise

    Completions.create = patched  # type: ignore[assignment]
    Completions._llmgovernor_patched = True  # type: ignore[attr-defined]


def _patch_anthropic() -> None:
    """Patch anthropic.resources.messages.Messages.create."""
    from anthropic.resources.messages import Messages  # type: ignore

    if getattr(Messages, "_llmgovernor_patched", False):
        return

    original_create = Messages.create

    @functools.wraps(original_create)
    def patched(self, *args, **kwargs):
        client = _current_client()
        if client is None:
            return original_create(self, *args, **kwargs)

        agent = _resolve_agent_name(client.default_agent_name)
        meta = get_metadata()
        meta.pop("agent_id", None)
        meta.pop("agent_name", None)
        start = time.time()
        try:
            response = original_create(self, *args, **kwargs)
            latency_ms = (time.time() - start) * 1000.0
            model = getattr(response, "model", "") or kwargs.get("model", "")
            usage = getattr(response, "usage", None)
            in_t = getattr(usage, "input_tokens", 0) if usage else 0
            out_t = getattr(usage, "output_tokens", 0) if usage else 0

            client.queue_event(
                CostEvent(
                    agent_name=agent,
                    model=model,
                    provider="anthropic",
                    input_tokens=in_t,
                    output_tokens=out_t,
                    total_tokens=in_t + out_t,
                    cost_usd=calculate_cost(model, in_t, out_t),
                    latency_ms=latency_ms,
                    status="ok",
                    metadata=meta or None,
                )
            )
            return response
        except Exception as e:
            latency_ms = (time.time() - start) * 1000.0
            client.queue_event(
                CostEvent(
                    agent_name=agent,
                    model=kwargs.get("model", ""),
                    provider="anthropic",
                    input_tokens=0,
                    output_tokens=0,
                    total_tokens=0,
                    cost_usd=0.0,
                    latency_ms=latency_ms,
                    status="error",
                    metadata={**meta, "error": str(e)},
                )
            )
            raise

    Messages.create = patched  # type: ignore[assignment]
    Messages._llmgovernor_patched = True  # type: ignore[attr-defined]


def _patch_bedrock() -> None:
    """Patch botocore at the operation level so every bedrock-runtime
    invoke_model goes through us. boto3 generates client classes
    dynamically, so we hook BaseClient._make_api_call instead.
    """
    import botocore.client  # type: ignore

    BaseClient = botocore.client.BaseClient
    if getattr(BaseClient, "_llmgovernor_bedrock_patched", False):
        return

    original_make_api_call = BaseClient._make_api_call

    @functools.wraps(original_make_api_call)
    def patched(self, operation_name, kwarg):  # noqa: D401
        # Only intercept Bedrock runtime calls; everything else passes through.
        service = getattr(self.meta, "service_model", None)
        service_id = getattr(service, "service_name", "") if service else ""
        if service_id != "bedrock-runtime" or operation_name not in {
            "InvokeModel",
            "InvokeModelWithResponseStream",
        }:
            return original_make_api_call(self, operation_name, kwarg)

        client = _current_client()
        if client is None:
            return original_make_api_call(self, operation_name, kwarg)

        agent = _resolve_agent_name(client.default_agent_name)
        meta = get_metadata()
        meta.pop("agent_id", None)
        meta.pop("agent_name", None)
        model_id = kwarg.get("modelId", "")
        start = time.time()
        try:
            response = original_make_api_call(self, operation_name, kwarg)
            latency_ms = (time.time() - start) * 1000.0
            # Bedrock returns usage in the response body for most models,
            # but parsing it requires reading the StreamingBody. Cost
            # estimation falls back to 0 tokens if we can't parse — at
            # least we still record the call happened.
            in_t = out_t = 0
            client.queue_event(
                CostEvent(
                    agent_name=agent,
                    model=model_id,
                    provider="bedrock",
                    input_tokens=in_t,
                    output_tokens=out_t,
                    total_tokens=in_t + out_t,
                    cost_usd=calculate_cost(model_id, in_t, out_t),
                    latency_ms=latency_ms,
                    status="ok",
                    metadata=meta or None,
                )
            )
            return response
        except Exception as e:
            latency_ms = (time.time() - start) * 1000.0
            client.queue_event(
                CostEvent(
                    agent_name=agent,
                    model=model_id,
                    provider="bedrock",
                    input_tokens=0,
                    output_tokens=0,
                    total_tokens=0,
                    cost_usd=0.0,
                    latency_ms=latency_ms,
                    status="error",
                    metadata={**meta, "error": str(e)},
                )
            )
            raise

    BaseClient._make_api_call = patched  # type: ignore[assignment]
    BaseClient._llmgovernor_bedrock_patched = True  # type: ignore[attr-defined]
