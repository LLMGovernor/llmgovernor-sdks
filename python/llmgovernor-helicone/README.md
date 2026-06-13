# llmgovernor-helicone

Bridge **Helicone** traces into the **LLMGovernor** anomaly engine — no code changes
to your existing LLM-calling code.

## Why

You already log to Helicone. You want per-agent cost anomaly detection on top without
ripping out what works. This package mirrors your existing Helicone traces into
LLMGovernor and surfaces anomalies (cost spikes, error bursts, latency regressions)
in the LLMGovernor dashboard or as email/webhook alerts.

## Quickstart (3 lines)

```python
from llmgovernor.adapters.helicone import forward
forward(api_key="llg_...", helicone_endpoint="https://yourdomain.com/hooks/helicone")
# ^^ starts a webhook server on :8765 — point Helicone's webhook here
```

## Install

```bash
pip install llmgovernor llmgovernor-helicone
```

## How it works

Helicone supports [outbound webhooks](https://docs.helicone.ai/features/webhooks) that
fire for every LLM request. This package:

1. Receives the JSON webhook payload from Helicone.
2. Maps it to LLMGovernor's canonical event schema (tokens, cost, latency, status).
3. POSTs the event to `POST /v1/events` with your API key as `Bearer` auth.

No prompt or response content is ever forwarded — only billing-safe metadata.

## Usage

### Option A — Built-in webhook server (no extra dependencies)

```python
from llmgovernor.adapters.helicone import forward

forward(
    api_key="llg_...",                  # your LLMGovernor API key
    helicone_endpoint="https://...",    # informational — what Helicone is pointed at
    port=8765,                          # default
)
```

This starts an HTTP server on `0.0.0.0:8765`. Point your Helicone webhook dashboard to
`http://your-ip:8765/`.

Non-blocking (background thread) variant:

```python
server = forward(api_key="llg_...", block=False)
# ... later ...
server.shutdown()
```

### Option B — Integrate into your own web framework

```python
from llmgovernor.adapters.helicone import process_webhook

# FastAPI / Starlette:
@app.post("/webhooks/helicone")
async def helicone_hook(request: Request):
    payload = await request.json()
    event = process_webhook(payload, api_key="llg_...")
    return {"ok": True, "event_id": event["event_id"]}
```

### Option C — Map only (no HTTP call)

```python
from llmgovernor.adapters.helicone import map_webhook

event = map_webhook(helicone_payload)
# event is a dict ready for Client.track(**event) or POST /v1/events
```

## Helicone webhook payload reference

Helicone sends a JSON body shaped like:

```json
{
  "request": {
    "id": "3c90c3cc-...",
    "created_at": "2024-01-15T10:30:00.000Z",
    "model": "gpt-4o",
    "provider": "OPENAI",
    "properties": { "Helicone-Property-Agent": "support-bot" }
  },
  "response": {
    "created_at": "2024-01-15T10:30:01.234Z",
    "status": 200
  },
  "usage": {
    "prompt_tokens": 517,
    "completion_tokens": 183,
    "cost": 0.005175
  }
}
```

## Agent tagging

Use Helicone's [custom properties](https://docs.helicone.ai/features/custom-properties)
to tag which agent issued the call:

```python
openai_client.chat.completions.create(
    model="gpt-4o",
    messages=[...],
    extra_headers={
        "Helicone-Property-Agent": "support-bot",   # <- LLMGovernor reads this
    },
)
```

## Examples

See the [`examples/`](examples/) directory:

- `helicone_webhook_receiver.py` — standalone server, zero extra deps
- `fastapi_integration.py` — mount inside an existing FastAPI app

## License

Apache-2.0 © EarlyBright Global LLC
