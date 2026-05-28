"""Per-request metadata via ContextVar.

`set_metadata({"feature": "summarize", ...})` attaches arbitrary tags to
every cost event generated in the current context (thread + asyncio task).
The auto-instrumenter (and the explicit wrap_* helpers) read this dict
and merge it into the event's `metadata` field before queuing.

Why ContextVar instead of threadlocal: works across `await` boundaries
in asyncio so a coroutine that's suspended and resumed on a different
thread still sees its own metadata.
"""

from contextvars import ContextVar
from typing import Any, Dict, Optional

_metadata_ctx: ContextVar[Optional[Dict[str, Any]]] = ContextVar(
    "llmgovernor_metadata", default=None
)


def set_metadata(metadata: Dict[str, Any]) -> None:
    """Replace the current context's metadata dict.

    The new dict applies to all events generated until the next call to
    set_metadata() or clear_metadata() in this context.
    """
    _metadata_ctx.set(dict(metadata))


def get_metadata() -> Dict[str, Any]:
    """Return the current context's metadata dict (a copy, safe to mutate)."""
    md = _metadata_ctx.get()
    return dict(md) if md else {}


def clear_metadata() -> None:
    """Drop the current context's metadata."""
    _metadata_ctx.set(None)
