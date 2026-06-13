"""Example: receive Helicone webhooks and forward to LLMGovernor.

This example shows two patterns:

1. Standalone webhook server  — one call, blocks until Ctrl-C.
2. FastAPI integration        — mount the adapter inside your existing app.

Run the standalone server::

    LLMGOVERNOR_API_KEY=llg_... python helicone_webhook_receiver.py

Then point your Helicone dashboard webhook to::

    http://your-server:8765/
"""

import os

# ── Pattern 1: Built-in standalone server ─────────────────────────────────────
# Zero-dependency server powered by stdlib http.server.
# Point Helicone's webhook at http://your-server:8765/ and you're done.

from llmgovernor.adapters.helicone import forward  # noqa: E402

API_KEY = os.environ.get("LLMGOVERNOR_API_KEY", "llg_replace_me")
HELICONE_ENDPOINT = os.environ.get(
    "HELICONE_ENDPOINT",
    "https://your-domain.example.com/webhooks/helicone",
)

if __name__ == "__main__":
    # Block until Ctrl-C — suitable for a dedicated webhook worker process.
    forward(
        api_key=API_KEY,
        helicone_endpoint=HELICONE_ENDPOINT,
        port=8765,
    )
