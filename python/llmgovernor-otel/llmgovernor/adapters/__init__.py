"""LLMGovernor adapters namespace package — supports namespace merging."""
from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)  # type: ignore[name-defined]
