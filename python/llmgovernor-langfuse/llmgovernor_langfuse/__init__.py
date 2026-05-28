"""LLMGovernor ↔ Langfuse adapter.

Mirrors LLM call traces from Langfuse (https://langfuse.com) into LLMGovernor's
anomaly engine so you can keep your existing Langfuse setup AND get
per-agent cost anomaly detection on top.

Status: SKELETON — full adapter logic ships before public launch.
See: https://github.com/LLMGovernor/llmgovernor-sdks/issues
"""
from __future__ import annotations

__version__ = "0.1.0"

from .adapter import LangfuseAdapter  # noqa: F401

__all__ = ["LangfuseAdapter"]
