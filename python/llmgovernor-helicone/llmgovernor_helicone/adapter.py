"""LLMGovernor ↔ Helicone adapter — forward Helicone webhook events to the anomaly engine.

Webhook approach (least customer instrumentation)
-------------------------------------------------
Point Helicone's webhook at any HTTP endpoint you control, then call
``forward(payload, api_key=…)`` to map and POST that event to LLMGovernor.

Or use the built-in convenience server::

    from llmgovernor.adapters.helicone import forward

    forward(api_key="llg_...", helicone_endpoint="https://api.helicone.ai")

That starts a lightweight WSGI server that accepts Helicone webhook POSTs and
forwards each event to the LLMGovernor ingest API — zero changes to your
existing LLM-calling code.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Optional
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from llmgovernor_helicone._mapper import map_webhook

__version__ = "0.1.0"

_DEFAULT_INGEST_URL = "https://api.llmgovernor.ai/v1/events"
_DEFAULT_HOST = "0.0.0.0"
_DEFAULT_PORT = 8765


def send_event(
    event: dict[str, Any],
    api_key: str,
    ingest_url: str = _DEFAULT_INGEST_URL,
    timeout: float = 10.0,
) -> None:
    """POST a single mapped event dict to the LLMGovernor /v1/events endpoint.

    Args:
        event:       Canonical event dict as returned by ``map_webhook()``.
        api_key:     LLMGovernor API key (``llg_...``).
        ingest_url:  Override the ingest endpoint (default: production API).
        timeout:     HTTP request timeout in seconds.

    Raises:
        urllib.error.HTTPError: on 4xx/5xx responses from the API.
    """
    body = json.dumps(event).encode()
    req = Request(
        ingest_url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urlopen(req, timeout=timeout):
        pass


def process_webhook(
    payload: dict[str, Any],
    api_key: str,
    ingest_url: str = _DEFAULT_INGEST_URL,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """Map a Helicone webhook payload and forward it to LLMGovernor.

    This is the low-level building block — use it when you have your own
    webhook endpoint framework (FastAPI, Flask, Django, …).

    Args:
        payload:     Raw JSON body from Helicone's webhook POST.
        api_key:     LLMGovernor API key (``llg_...``).
        ingest_url:  Override the ingest endpoint.
        timeout:     HTTP timeout in seconds.

    Returns:
        The canonical event dict that was forwarded.

    Raises:
        ValueError: if *payload* is missing required Helicone fields.
        urllib.error.HTTPError: on API error.
    """
    event = map_webhook(payload)
    send_event(event, api_key=api_key, ingest_url=ingest_url, timeout=timeout)
    return event


class _WebhookHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler: accept POST, map, forward."""

    api_key: str = ""
    ingest_url: str = _DEFAULT_INGEST_URL

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw)
            process_webhook(payload, api_key=self.api_key, ingest_url=self.ingest_url)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
        except (ValueError, HTTPError) as exc:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(exc)}).encode())

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 — matches base class signature  # silence default stdout noise
        pass


def forward(
    api_key: str,
    helicone_endpoint: str = "",
    ingest_url: str = _DEFAULT_INGEST_URL,
    host: str = _DEFAULT_HOST,
    port: int = _DEFAULT_PORT,
    block: bool = True,
) -> Optional[HTTPServer]:
    """Start the built-in webhook receiver.

    Sets up a local HTTP server that:
    1. Accepts ``POST /`` from Helicone's webhook system.
    2. Maps the payload to LLMGovernor's canonical event schema.
    3. POSTs the event to the LLMGovernor ingest API.

    Typical usage::

        from llmgovernor.adapters.helicone import forward

        # Block the process (e.g. in a standalone webhook worker)
        forward(api_key="llg_...", helicone_endpoint="https://...")

        # Or run in a background thread (e.g. in a longer-running app)
        server = forward(api_key="llg_...", block=False)
        # ... later ...
        server.shutdown()

    Args:
        api_key:            LLMGovernor API key (``llg_...``).
        helicone_endpoint:  Informational — the Helicone webhook URL pointing here
                            (logged on startup; not used programmatically).
        ingest_url:         Override the LLMGovernor ingest URL.
        host:               Interface to bind (default ``0.0.0.0``).
        port:               Port to listen on (default 8765).
        block:              If ``True`` (default), block until Ctrl-C.
                            If ``False``, start in a daemon thread and return the server.

    Returns:
        The ``HTTPServer`` instance when ``block=False``; ``None`` when blocking.
    """
    if not api_key:
        raise ValueError("api_key is required")

    # Bind config onto the handler class (stdlib pattern).
    handler: type[_WebhookHandler] = type(
        "_BoundWebhookHandler",
        (_WebhookHandler,),
        {"api_key": api_key, "ingest_url": ingest_url},
    )

    server = HTTPServer((host, port), handler)
    if helicone_endpoint:
        print(f"[llmgovernor-helicone] Listening on {host}:{port}  "
              f"← Helicone endpoint: {helicone_endpoint}")
    else:
        print(f"[llmgovernor-helicone] Webhook receiver listening on {host}:{port}")

    if block:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        return None
    else:
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        return server
