"""LLMGovernor ↔ Helicone adapter.

Mirrors LLM call traces from Helicone (https://helicone.ai) into LLMGovernor's
anomaly engine so you can keep your existing Helicone setup AND get per-agent
cost anomaly detection on top.

Quickstart (webhook server)::

    from llmgovernor.adapters.helicone import forward
    forward(api_key="llg_...", helicone_endpoint="https://yourdomain.com/webhooks/helicone")

Quickstart (integrate into your own webhook handler)::

    from llmgovernor.adapters.helicone import process_webhook

    # FastAPI / Starlette:
    @app.post("/webhooks/helicone")
    async def helicone_webhook(request: Request):
        payload = await request.json()
        process_webhook(payload, api_key="llg_...")
        return {"ok": True}
"""

from __future__ import annotations

from llmgovernor_helicone._mapper import map_webhook
from llmgovernor_helicone.adapter import forward, process_webhook, send_event

__version__ = "0.1.0"

__all__ = [
    "forward",
    "process_webhook",
    "send_event",
    "map_webhook",
]
