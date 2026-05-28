"""Adapter shim — pulls traces from Helicone → LLMGovernor."""
from __future__ import annotations

import os
from typing import Any


class HeliconeAdapter:
    """Forward Helicone trace events to LLMGovernor.

    Usage::

        from llmgovernor_helicone import HeliconeAdapter
        adapter = HeliconeAdapter(
            llmgovernor_api_key=os.environ["LLMGOVERNOR_API_KEY"],
            helicone_api_key=os.environ["HELICONE_API_KEY"],
            agent_name="my-agent",
        )
        adapter.start()  # begins forwarding in background

    This package keeps your existing Helicone setup AND adds LLMGovernor's
    anomaly engine on top. No code-level instrumentation needed in your app.
    """

    def __init__(
        self,
        llmgovernor_api_key: str,
        helicone_api_key: str,
        agent_name: str = "default",
        llmgovernor_endpoint: str = "https://api.llmgovernor.ai",
        **kwargs: Any,
    ) -> None:
        self.llmgovernor_api_key = llmgovernor_api_key
        self.helicone_api_key = helicone_api_key
        self.agent_name = agent_name
        self.llmgovernor_endpoint = llmgovernor_endpoint
        self._extra = kwargs

    def start(self) -> None:
        """Begin streaming traces. Implementation pending — see issue tracker."""
        raise NotImplementedError(
            "Helicone adapter scaffolding — full implementation lands before "
            "the LLMGovernor public launch. Track progress at "
            "https://github.com/LLMGovernor/llmgovernor-sdks/issues"
        )

    def stop(self) -> None:
        """Stop the background forwarder."""
        pass
