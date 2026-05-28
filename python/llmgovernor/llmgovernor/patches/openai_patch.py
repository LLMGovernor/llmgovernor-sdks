"""OpenAI client monkey-patch for cost tracking in the Blaze SDK."""

import time
import functools

from ..types import CostEvent
from ..pricing import calculate_cost


def wrap_openai_client(openai_client, blaze_client, agent_name: str = "default"):
    """
    Monkey-patch an OpenAI client to capture cost events for chat completions.

    Args:
        openai_client: OpenAI client instance to wrap
        blaze_client: BlazeClient instance to queue events to
        agent_name: Name of the agent making the requests (default: 'default')

    Returns:
        The same openai_client instance, now patched
    """
    # Store original method
    original_create = openai_client.chat.completions.create

    @functools.wraps(original_create)
    def patched_create(*args, **kwargs):
        start_time = time.time()

        try:
            # Call the original method
            response = original_create(*args, **kwargs)

            # Measure latency
            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000

            # Extract model and usage information
            model = response.model if hasattr(response, "model") else ""
            usage = getattr(response, "usage", None)

            input_tokens = 0
            output_tokens = 0
            total_tokens = 0

            if usage:
                input_tokens = getattr(usage, "prompt_tokens", 0)
                output_tokens = getattr(usage, "completion_tokens", 0)
                total_tokens = getattr(usage, "total_tokens", input_tokens + output_tokens)

            # Calculate cost
            cost_usd = calculate_cost(model, input_tokens, output_tokens)

            # Create and queue cost event
            event = CostEvent(
                agent_name=agent_name,
                model=model,
                provider="openai",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                status="ok",
            )

            blaze_client.queue_event(event)

            # Return the original response unmodified
            return response

        except Exception as e:
            # Measure latency even on error
            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000

            # Extract model from kwargs if available
            model = kwargs.get("model", "")

            # Create error event
            error_event = CostEvent(
                agent_name=agent_name,
                model=model,
                provider="openai",
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                cost_usd=0.0,
                latency_ms=latency_ms,
                status="error",
                metadata={"error": str(e)},
            )

            blaze_client.queue_event(error_event)

            # Re-raise the original exception
            raise

    # Replace the original method
    openai_client.chat.completions.create = patched_create

    return openai_client
