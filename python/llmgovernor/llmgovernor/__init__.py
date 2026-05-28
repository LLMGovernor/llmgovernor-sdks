"""LLMGovernor SDK — cost intelligence + budget enforcement for AI agent fleets.

Recommended entry points:
    from llmgovernor import instrument, set_metadata
    instrument()                      # auto-patches openai/anthropic/bedrock
    set_metadata({"feature": "foo"})  # tags every event in this context

Explicit control (per-instance wrap, no global patching):
    from llmgovernor import wrap_openai_client, LLMGovernorClient
    client = LLMGovernorClient(api_key=...)
    openai_client = wrap_openai_client(my_openai_client, client, "agent-name")

Decorator-based pattern (for entrypoints):
    from llmgovernor import Fleet
    fleet = Fleet(api_key=...)
    @fleet.agent("researcher")
    def run(): ...
"""

from .client import LLMGovernorClient, BlazeClient
from .decorator import agent, agent_context, get_current_agent
from .fleet import Fleet
from .instrument import instrument
from .metadata import clear_metadata, get_metadata, set_metadata
from .pricing import calculate_cost, get_model_pricing
from .types import CostEvent
from ._transport import Transport, get_transport, init, reset_transport

__version__ = "0.3.0"

__all__ = [
    # Primary auto-instrument API
    "instrument",
    "set_metadata",
    "get_metadata",
    "clear_metadata",
    # Lower-level building blocks
    "LLMGovernorClient",
    "Fleet",
    "CostEvent",
    "agent",
    "agent_context",
    "get_current_agent",
    "calculate_cost",
    "get_model_pricing",
    # Back-compat alias
    "BlazeClient",
    # Transport (lean refactor API)
    "Transport",
    "get_transport",
    "init",
    "reset_transport",
]

# Re-export the explicit wrap_* helpers when their target libs are installed.
try:
    from .patches.openai_patch import wrap_openai_client  # noqa: F401

    __all__.append("wrap_openai_client")
except ImportError:
    pass

try:
    from .patches.anthropic_patch import wrap_anthropic_client  # noqa: F401

    __all__.append("wrap_anthropic_client")
except ImportError:
    pass

try:
    from .patches.bedrock_patch import wrap_bedrock_client  # noqa: F401

    __all__.append("wrap_bedrock_client")
except ImportError:
    pass
