"""Fleet — main entry point for the Blaze SDK."""

from .client import BlazeClient
from .patches.openai_patch import wrap_openai_client
from .decorator import agent


class Fleet:
    """Manages cost tracking for a fleet of AI agents.

    Usage:
        fleet = Fleet(api_key="blz_your_key")
        client = fleet.wrap_openai(openai.OpenAI(), agent_name="researcher")
        # All calls through `client` are now tracked
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.blazeagents.dev",
        batch_size: int = 50,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.client = BlazeClient(
            api_key=api_key,
            base_url=base_url,
            batch_size=batch_size,
        )
        self._agents: dict = {}  # Track registered agent names

    def wrap_openai(self, openai_client, agent_name: str = "default"):
        """Wrap an OpenAI client for cost tracking.

        Args:
            openai_client: An OpenAI() client instance
            agent_name: Name to attribute costs to

        Returns:
            The same client, monkey-patched for cost tracking
        """
        self._agents[agent_name] = {"provider": "openai"}
        return wrap_openai_client(openai_client, self.client, agent_name)

    def agent(self, name: str):
        """Decorator to tag a function with an agent name.

        Usage:
            @fleet.agent("researcher")
            def do_research(query):
                ...
        """
        self._agents[name] = {"provider": "auto"}
        return agent(name)

    @property
    def registered_agents(self) -> list:
        """List all registered agent names."""
        return list(self._agents.keys())

    @property
    def stats(self) -> dict:
        """Return fleet-level send statistics."""
        return {
            "agents": self.registered_agents,
            "agent_count": len(self._agents),
            **self.client.stats,
        }

    def flush(self):
        """Flush all pending events."""
        self.client.flush()

    def close(self):
        """Flush and close the client."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
