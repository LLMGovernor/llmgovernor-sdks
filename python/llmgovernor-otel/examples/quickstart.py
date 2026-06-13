"""
Minimal example: wire LLMGovSpanProcessor into an OTel TracerProvider.

Run with:
    LLMGOV_API_KEY=llmgov_xxxxx python examples/quickstart.py

The script simulates a single LLM call span using the GenAI semantic conventions
and flushes it to LLMGovernor before exiting.
"""

import os

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

from llmgovernor import Client
from llmgovernor_otel import LLMGovSpanProcessor

# --- 3-line setup ----------------------------------------------------------------

client = Client(api_key=os.environ.get("LLMGOV_API_KEY", "llmgov_demo_key"))
provider = TracerProvider()
provider.add_span_processor(LLMGovSpanProcessor(client))

# Set as the global tracer provider
trace.set_tracer_provider(provider)

# --- Simulate an LLM call --------------------------------------------------------

tracer = trace.get_tracer("my-app")

with tracer.start_as_current_span("openai.chat") as span:
    # GenAI semantic conventions (these are the attributes the processor reads)
    span.set_attribute("gen_ai.system", "openai")
    span.set_attribute("gen_ai.request.model", "gpt-4o")
    span.set_attribute("gen_ai.usage.input_tokens", 350)
    span.set_attribute("gen_ai.usage.output_tokens", 120)
    span.set_attribute("gen_ai.operation.name", "chat")
    span.set_attribute("llmgovernor.agent", "my-agent")
    span.set_attribute("service.name", "my-app")

    # Simulate work...
    import time
    time.sleep(0.05)

# Flush before exit so the event reaches LLMGovernor
client.flush(timeout=10.0)
print("Event forwarded to LLMGovernor.")
