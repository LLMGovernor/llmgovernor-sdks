"""LLMGovernor ↔ Helicone adapter.

Mirrors LLM call traces from Helicone (https://helicone.ai) into LLMGovernor's
anomaly engine so you can keep your existing Helicone setup AND get
per-agent cost anomaly detection on top.

Status: SKELETON — full adapter logic ships before public launch.
See: https://github.com/LLMGovernor/llmgovernor-sdks/issues
"""
from __future__ import annotations

__version__ = "0.1.0"

from .adapter import HeliconeAdapter  # noqa: F401

__all__ = ["HeliconeAdapter"]
