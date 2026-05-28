# llmgovernor-langfuse

Bridge **Langfuse** traces into the **LLMGovernor** anomaly engine.

## Why

You already log to Langfuse. You want per-agent cost anomaly detection on top
without ripping out what works. This package mirrors your existing Langfuse
traces into LLMGovernor and surfaces anomalies (cost spikes, error bursts, latency
regressions) in the LLMGovernor dashboard or as Slack/email alerts.

> **Status:** v0.1.0 — package scaffolding. Full adapter logic lands before public launch.

## Install

```bash
pip install llmgovernor-langfuse
```

## Usage

```python
from llmgovernor_langfuse import LangfuseAdapter

adapter = LangfuseAdapter(
    llmgovernor_api_key="lg_...",
    langfuse_api_key="...",
    agent_name="my-agent",
)
adapter.start()
```

## License

Apache-2.0 © EarlyBright Global LLC
