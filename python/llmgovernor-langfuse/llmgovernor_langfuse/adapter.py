"""Adapter shim — pulls traces from Langfuse → LLMGovernor."""
from __future__ import annotations

import os
from typing import Any


class LangfuseAdapter:
    """Forward Langfuse trace events to LLMGovernor.

    Usage::

        from llmgovernor_langfuse import LangfuseAdapter
        adapter = LangfuseAdapter(
            llmgovernor_api_key=os.environ["LLMGOVERNOR_API_KEY"],
            langfuse_api_key=os.environ["LANGFUSE_API_KEY"],
            agent_name="my-agent",
        )
        adapter.start()  # begins forwarding in background

    This package keeps your existing Langfuse setup AND adds LLMGovernor's
    anomaly engine on top. No code-level instrumentation needed in your app.
    """

    def __init__(
        self,
        llmgovernor_api_key: str,
        langfuse_api_key: str,
        agent_name: str = "default",
        llmgovernor_endpoint: str = "https://api.llmgovernor.ai",
        **kwargs: Any,
    ) -> None:
        self.llmgovernor_api_key = llmgovernor_api_key
        self.langfuse_api_key = langfuse_api_key
        self.agent_name = agent_name
        self.llmgovernor_endpoint = llmgovernor_endpoint
        self._extra = kwargs

    def start(self) -> None:
        """Begin streaming traces. Implementation pending — see issue tracker."""
        raise NotImplementedError(
            "Langfuse adapter scaffolding — full implementation lands before "
            "the LLMGovernor public launch. Track progress at "
            "https://github.com/LLMGovernor/llmgovernor-sdks/issues"
        )

    def stop(self) -> None:
        """Stop the background forwarder."""
        pass
