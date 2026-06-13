# llmgovernor-otel

OpenTelemetry `SpanProcessor` adapter for the [LLMGov Anomaly Engine](https://llmgovernor.ai).

Filters spans carrying [GenAI semantic conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/)
(`gen_ai.*` attributes) and forwards them to LLMGovernor `/v1/events`. All other spans are ignored.
No prompt or response content is ever transmitted.

## Quickstart

```python
from opentelemetry.sdk.trace import TracerProvider
from llmgovernor import Client
from llmgovernor_otel import LLMGovSpanProcessor

provider = TracerProvider()
provider.add_span_processor(LLMGovSpanProcessor(Client(api_key="llmgov_...")))
```

That's it. Wire `provider` as the global OTel tracer and every LLM call
instrumented with the standard GenAI conventions (opentelemetry-instrumentation-openai,
opentelemetry-instrumentation-anthropic, etc.) flows to LLMGovernor automatically.

## Installation

```
pip install llmgovernor-otel
```

The `opentelemetry-sdk` dependency is optional — install it separately or pull
it in via the `otel` extra:

```
pip install "llmgovernor-otel[otel]"
```

## API key

Pass your key directly or set the `LLMGOV_API_KEY` environment variable:

```python
import os
from llmgovernor import Client
from llmgovernor_otel import LLMGovSpanProcessor

client = Client(api_key=os.environ["LLMGOV_API_KEY"])
```

## LLM span detection

A span is forwarded when it carries at least one of these attributes:

- `gen_ai.system`
- `gen_ai.request.model`
- `gen_ai.response.model`
- `gen_ai.operation.name`

Set `llmgovernor.agent` on your spans to group events by agent name in the dashboard.
Falls back to `service.name` then the span name.

## Manual mapping

```python
from llmgovernor_otel import from_otel_span, is_llm_span

if is_llm_span(span_dict):
    client.track(**from_otel_span(span_dict))
```

## License

Apache 2.0 — see [LICENSE](LICENSE).
