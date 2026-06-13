"""otel_quickstart.py — runnable OTel integration example.

Demonstrates how to wire LLMGovernorSpanProcessor into an OpenTelemetry
TracerProvider so that every LLM span is automatically forwarded to
LLMGovernor /v1/events.

Usage::

    export LLMGOVERNOR_API_KEY=llg_...
    python examples/otel_quickstart.py
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# Allow running directly from the package root without installing.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from llmgovernor.adapters.otel import LLMGovernorSpanProcessor

API_KEY = os.environ.get("LLMGOVERNOR_API_KEY", "llg_demo_key")
ENDPOINT = os.environ.get("LLMGOVERNOR_ENDPOINT", "https://api.llmgovernor.ai")

# 1. Create the LLMGovernorSpanProcessor.
llg_processor = LLMGovernorSpanProcessor(api_key=API_KEY, endpoint=ENDPOINT)

# 2. Add it to a TracerProvider.
#    Wrap with BatchSpanProcessor for production; SimpleSpanProcessor is fine
#    for demos/testing.
provider = TracerProvider()
provider.add_span_processor(llg_processor)
trace.set_tracer_provider(provider)

tracer = trace.get_tracer(__name__)

# 3. Emit a fake LLM span — in real usage, your instrumented LLM client
#    creates these automatically (e.g. via opentelemetry-instrumentation-openai).
print("Emitting a synthetic LLM span...")
with tracer.start_as_current_span("llm-call") as span:
    span.set_attribute("llm.provider", "openai")
    span.set_attribute("llm.model", "gpt-4o")
    span.set_attribute("llm.input_tokens", 120)
    span.set_attribute("llm.output_tokens", 64)
    print(f"  span_id  : {span.get_span_context().span_id:#x}")
    print(f"  trace_id : {span.get_span_context().trace_id:#x}")
    # Simulate a 200ms LLM call.
    time.sleep(0.2)

print("Span closed — LLMGovernor received the event (if API key is valid).")
print("Done.")
