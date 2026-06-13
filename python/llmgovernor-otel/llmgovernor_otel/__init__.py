"""llmgovernor-otel — re-export for flat-import convenience.

Both import styles work after installing this package:

    from llmgovernor_otel import LLMGovernorSpanProcessor
    from llmgovernor.adapters.otel import LLMGovernorSpanProcessor
"""
from llmgovernor.adapters.otel import LLMGovernorSpanProcessor  # noqa: F401

__all__ = ["LLMGovernorSpanProcessor"]
__version__ = "0.1.0"
