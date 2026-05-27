from .callback import LLMGovernorHandler

__all__ = ["LLMGovernorHandler", "register"]
__version__ = "0.1.0"


def register(api_key: str | None = None, endpoint: str | None = None, **kwargs):
    """Init transport (if not already inited) and register handler with litellm.callbacks."""
    import litellm
    import llmgovernor

    if api_key or endpoint:
        llmgovernor.init(api_key=api_key, endpoint=endpoint, **kwargs)

    handler = LLMGovernorHandler()
    # idempotent: avoid duplicates
    if not any(isinstance(cb, LLMGovernorHandler) for cb in getattr(litellm, "callbacks", [])):
        litellm.callbacks = [*getattr(litellm, "callbacks", []), handler]
    return handler
