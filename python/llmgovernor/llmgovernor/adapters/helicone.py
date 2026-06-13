"""Convenience re-export: ``from llmgovernor.adapters.helicone import forward``.

Requires ``llmgovernor-helicone`` to be installed::

    pip install llmgovernor-helicone

Then::

    from llmgovernor.adapters.helicone import forward
    forward(api_key="llg_...", helicone_endpoint="https://...")
"""

try:
    from llmgovernor_helicone import forward, map_webhook, process_webhook, send_event  # noqa: F401
except ImportError as exc:
    raise ImportError(
        "llmgovernor-helicone is not installed. "
        "Run: pip install llmgovernor-helicone"
    ) from exc

__all__ = ["forward", "process_webhook", "send_event", "map_webhook"]
