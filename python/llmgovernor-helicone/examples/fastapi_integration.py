"""Example: integrate llmgovernor-helicone into a FastAPI application.

Shows how to mount a Helicone webhook handler inside an existing FastAPI app
using ``process_webhook()`` — ideal when you already have a running web server.

Requires::

    pip install fastapi uvicorn llmgovernor-helicone

Run::

    LLMGOVERNOR_API_KEY=llg_... uvicorn fastapi_integration:app --port 8000
"""

import os

from fastapi import FastAPI, HTTPException, Request, Response

from llmgovernor.adapters.helicone import process_webhook

app = FastAPI(title="My LLM App + LLMGovernor Helicone Adapter")

_API_KEY = os.environ.get("LLMGOVERNOR_API_KEY", "llg_replace_me")


@app.post("/webhooks/helicone")
async def helicone_webhook(request: Request) -> dict:
    """Receive a Helicone webhook and forward it to LLMGovernor."""
    try:
        payload = await request.json()
        event = process_webhook(payload, api_key=_API_KEY)
        return {"ok": True, "event_id": event["event_id"]}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/healthz")
def health() -> dict:
    return {"status": "ok"}
