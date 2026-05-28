"""AWS Bedrock client monkey-patch for cost tracking in the Blaze SDK."""

import time
import functools
import json

from ..types import CostEvent
from ..pricing import calculate_cost


def wrap_bedrock_client(bedrock_client, blaze_client, agent_name: str = "default"):
    """
    Monkey-patch a Bedrock runtime client to capture cost events for model invocations.

    Args:
        bedrock_client: Bedrock runtime client instance to wrap
        blaze_client: BlazeClient instance to queue events to
        agent_name: Name of the agent making the requests (default: 'default')

    Returns:
        The same bedrock_client instance, now patched
    """
    # Store original method
    original_invoke = bedrock_client.invoke_model

    @functools.wraps(original_invoke)
    def patched_invoke_model(*args, **kwargs):
        start_time = time.time()

        try:
            # Call the original method
            response = original_invoke(*args, **kwargs)

            # Measure latency
            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000

            # Extract model ID from kwargs
            model_id = kwargs.get("modelId", "")

            # Parse response body for usage information
            input_tokens = 0
            output_tokens = 0
            total_tokens = 0

            try:
                # Read the response body (streaming body)
                body = response.get("body")
                if body:
                    # Read the stream and parse JSON
                    body_content = body.read()
                    response_data = json.loads(body_content)

                    # Try to create a new readable stream for the caller
                    # This is a best-effort attempt to maintain compatibility
                    try:
                        # Create a simple mock that returns the data
                        class MockBody:
                            def __init__(self, data):
                                self._data = data

                            def read(self):
                                return self._data

                            def __iter__(self):
                                yield self._data

                        response["body"] = MockBody(body_content)
                    except Exception:
                        # If we can't replace the body, continue anyway
                        pass

                    # Extract usage information from the response
                    # Different providers structure this differently
                    usage = response_data.get("usage")
                    if usage:
                        input_tokens = usage.get("input_tokens", 0)
                        output_tokens = usage.get("output_tokens", 0)
                        total_tokens = input_tokens + output_tokens
                    else:
                        # Try alternative structures
                        if "inputTokenCount" in response_data:
                            input_tokens = response_data.get("inputTokenCount", 0)
                            output_tokens = response_data.get("outputTokenCount", 0)
                            total_tokens = input_tokens + output_tokens
                        elif "inputTokens" in response_data:
                            input_tokens = response_data.get("inputTokens", 0)
                            output_tokens = response_data.get("outputTokens", 0)
                            total_tokens = input_tokens + output_tokens
            except (json.JSONDecodeError, AttributeError, Exception):
                # If we can't parse usage, continue with zeros
                pass

            # Calculate cost
            cost_usd = calculate_cost(model_id, input_tokens, output_tokens)

            # Create and queue cost event
            event = CostEvent(
                agent_name=agent_name,
                model=model_id,
                provider="bedrock",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                status="ok",
            )

            blaze_client.queue_event(event)

            # Return the original response
            return response

        except Exception as e:
            # Measure latency even on error
            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000

            # Extract model ID from kwargs if available
            model_id = kwargs.get("modelId", "")

            # Create error event
            error_event = CostEvent(
                agent_name=agent_name,
                model=model_id,
                provider="bedrock",
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
    bedrock_client.invoke_model = patched_invoke_model

    return bedrock_client
