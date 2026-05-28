"""Agent context manager and decorator for Blaze SDK.

This module provides context management for tracking the current agent
across function calls and async operations.
"""

from contextvars import ContextVar
from typing import Callable
from functools import wraps
import asyncio


# Context variable to track the current agent name
_current_agent: ContextVar[str] = ContextVar("current_agent", default="default")


def get_current_agent() -> str:
    """Get the current agent name from context.

    Returns:
        str: The current agent name, defaults to 'default' if no context is set.
    """
    return _current_agent.get()


class agent_context:
    """Context manager for setting an agent name within a specific scope.

    Usage:
        with agent_context('my_agent'):
            # Current agent is 'my_agent' within this block
            print(get_current_agent())  # 'my_agent'
        # Current agent is restored to previous value
    """

    def __init__(self, name: str):
        """Initialize the context manager.

        Args:
            name: The agent name to set within the context.
        """
        self.name = name
        self.token = None

    def __enter__(self):
        """Enter the context and set the agent name."""
        self.token = _current_agent.set(self.name)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context and restore the previous agent name."""
        _current_agent.reset(self.token)


def agent(name: str):
    """Decorator for automatically setting agent context around function calls.

    Works with both synchronous and asynchronous functions.

    Args:
        name: The agent name to set during function execution.

    Usage:
        @agent('my_agent')
        def my_function():
            return get_current_agent()  # Returns 'my_agent'

        @agent('async_agent')
        async def my_async_function():
            return get_current_agent()  # Returns 'async_agent'
    """

    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                with agent_context(name):
                    return await func(*args, **kwargs)

            return async_wrapper
        else:

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                with agent_context(name):
                    return func(*args, **kwargs)

            return sync_wrapper

    return decorator
