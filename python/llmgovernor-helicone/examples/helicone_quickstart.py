"""helicone_quickstart.py — runnable quickstart for llmgovernor-helicone.

Shows the three patterns for bridging Helicone → LLMGovernor:
  A. Built-in webhook receiver (simplest, zero infra)
  B. Drop-in inside your own FastAPI/Flask webhook handler
  C. One-shot CLI call (for testing / CI smoke checks)

Run this file directly (pattern C) to validate your API key:
    python helicone_quickstart.py --api-key llg_... --smoke-test

Prerequisites:
    pip install llmgovernor-helicone
    export LLMGOVERNOR_API_KEY=llg_...
"""
from __future__ import annotations

import os
import sys
from typing import Optional

from llmgovernor.adapters.helicone import forward, map_webhook, process_webhook


# ---------------------------------------------------------------------------
# Pattern A — built-in webhook server (blocks until Ctrl-C)
# ---------------------------------------------------------------------------

def run_webhook_server(api_key: str, port: int = 8765) -> None:
    """Start the built-in webhook receiver.

    Point Helicone's webhook at http://<your-host>:8765 and every
    event will flow to LLMGovernor automatically.
    """
    print(f"[llmgovernor-helicone] Starting webhook server on port {port}")
    forward(
        api_key=api_key,
        helicone_endpoint=f"http://0.0.0.0:{port}",
        port=port,
        block=True,          # blocks; use block=False to run in a thread
    )


# ---------------------------------------------------------------------------
# Pattern B — drop-in inside your own webhook handler (FastAPI example)
# ---------------------------------------------------------------------------

def make_fastapi_app(api_key: str):
    """Return a FastAPI app with a /helicone-webhook endpoint.

    Usage:
        uvicorn helicone_quickstart:app --port 8000
        # then configure Helicone to POST to http://localhost:8000/helicone-webhook
    """
    try:
        from fastapi import FastAPI, Request, Response
    except ImportError:
        print("FastAPI not installed. Run: pip install fastapi uvicorn")
        return None

    app = FastAPI(title="Helicone → LLMGovernor bridge")

    @app.post("/helicone-webhook")
    async def helicone_webhook(request: Request) -> dict:
        payload = await request.json()
        process_webhook(payload, api_key=api_key)
        return {"ok": True}

    return app


# ---------------------------------------------------------------------------
# Pattern C — smoke test / one-shot validation
# ---------------------------------------------------------------------------

def smoke_test(api_key: str, ingest_url: str = "https://api.llmgovernor.ai/v1/events") -> bool:
    """Send a synthetic Helicone event and verify it reaches LLMGovernor."""
    import json
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    payload = {
        "request": {
            "id": "req_quickstart_001",
            "model": "gpt-4o",
            "provider": "OPENAI",
            "created_at": now.isoformat(),
            "properties": {"Helicone-Property-Agent": "quickstart-test"},
        },
        "response": {
            "status": 200,
            "created_at": (now + timedelta(milliseconds=340)).isoformat(),
        },
        "usage": {
            "prompt_tokens": 18,
            "completion_tokens": 12,
            "cost": 0.0004,
        },
    }
    event = map_webhook(payload)

    print("[llmgovernor-helicone] Mapped event:")
    print(json.dumps(event, indent=2, default=str))

    try:
        process_webhook(payload, api_key=api_key, ingest_url=ingest_url)
        print("[llmgovernor-helicone] smoke test ✓ — event delivered")
        return True
    except Exception as exc:
        print(f"[llmgovernor-helicone] smoke test ✗ — {exc}")
        return False


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="llmgovernor-helicone quickstart")
    parser.add_argument("--api-key", default=os.environ.get("LLMGOVERNOR_API_KEY", ""))
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--smoke-test", action="store_true", help="Send one synthetic event and exit")
    parser.add_argument("--ingest-url", default="https://api.llmgovernor.ai/v1/events")
    args = parser.parse_args()

    if not args.api_key:
        print("ERROR: set LLMGOVERNOR_API_KEY or pass --api-key", file=sys.stderr)
        sys.exit(1)

    if args.smoke_test:
        ok = smoke_test(args.api_key, ingest_url=args.ingest_url)
        sys.exit(0 if ok else 1)
    else:
        run_webhook_server(args.api_key, port=args.port)
