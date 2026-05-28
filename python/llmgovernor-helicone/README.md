# llmgovernor-helicone

Bridge **Helicone** traces into the **LLMGovernor** anomaly engine.

## Why

You already log to Helicone. You want per-agent cost anomaly detection on top
without ripping out what works. This package mirrors your existing Helicone
traces into LLMGovernor and surfaces anomalies (cost spikes, error bursts, latency
regressions) in the LLMGovernor dashboard or as Slack/email alerts.

> **Status:** v0.1.0 — package scaffolding. Full adapter logic lands before public launch.

## Install

```bash
pip install llmgovernor-helicone
```

## Usage

```python
from llmgovernor_helicone import HeliconeAdapter

adapter = HeliconeAdapter(
    llmgovernor_api_key="lg_...",
    helicone_api_key="...",
    agent_name="my-agent",
)
adapter.start()
```

## License

Apache-2.0 © EarlyBright Global LLC
