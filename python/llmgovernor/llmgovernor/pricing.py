"""LLM model pricing database and cost calculator for the Blaze SDK."""

from typing import Dict


# Model pricing in USD per 1M tokens (input_price, output_price)
MODEL_PRICING: Dict[str, Dict[str, float]] = {
    # OpenAI GPT models
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "o1": {"input": 15.00, "output": 60.00},
    "o1-mini": {"input": 1.10, "output": 4.40},
    "o3-mini": {"input": 1.10, "output": 4.40},
    # Claude models (Anthropic)
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    "claude-opus-4-20250514": {"input": 15.00, "output": 75.00},
    "claude-haiku-3-20250307": {"input": 0.25, "output": 1.25},
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.00},
    # Claude aliases
    "claude-sonnet-4": {"input": 3.00, "output": 15.00},
    "claude-opus-4": {"input": 15.00, "output": 75.00},
    "claude-haiku-3.5": {"input": 0.80, "output": 4.00},
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-5-haiku": {"input": 0.80, "output": 4.00},
    # AWS Bedrock models (with Anthropic prefix)
    "anthropic.claude-opus-4-v1": {"input": 15.00, "output": 75.00},
    "anthropic.claude-sonnet-4-v1": {"input": 3.00, "output": 15.00},
    "anthropic.claude-sonnet-4-v1:0": {"input": 3.00, "output": 15.00},  # Bedrock versioned model
    "anthropic.claude-haiku-3.5-v1": {"input": 0.80, "output": 4.00},
    # Google Gemini models
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    # Free models
    "gpt-4o:free": {"input": 0.0, "output": 0.0},
    "gpt-4o-mini:free": {"input": 0.0, "output": 0.0},
    "claude-sonnet-4:free": {"input": 0.0, "output": 0.0},
    "claude-opus-4:free": {"input": 0.0, "output": 0.0},
    "claude-haiku-3.5:free": {"input": 0.0, "output": 0.0},
    "claude-3-5-sonnet:free": {"input": 0.0, "output": 0.0},
    "claude-3-5-haiku:free": {"input": 0.0, "output": 0.0},
    "anthropic.claude-opus-4-v1:free": {"input": 0.0, "output": 0.0},
    "anthropic.claude-sonnet-4-v1:free": {"input": 0.0, "output": 0.0},
    "anthropic.claude-sonnet-4-v1:0:free": {"input": 0.0, "output": 0.0},
    "anthropic.claude-haiku-3.5-v1:free": {"input": 0.0, "output": 0.0},
    "gemini-1.5-flash:free": {"input": 0.0, "output": 0.0},
    "gemini-1.5-pro:free": {"input": 0.0, "output": 0.0},
    "gemini-2.0-flash:free": {"input": 0.0, "output": 0.0},
}


def _normalize_model(model: str) -> str:
    """
    Normalize model name by stripping provider prefixes and :free suffixes.

    Args:
        model: Model name to normalize

    Returns:
        Normalized model name
    """
    # Strip provider prefixes
    if "/" in model:
        model = model.split("/", 1)[1]

    # Strip :free suffix
    if model.endswith(":free"):
        model = model[:-5]

    return model


def get_model_pricing(model: str) -> Dict[str, float]:
    """
    Get pricing information for a model.

    Args:
        model: Model name (can include provider prefix)

    Returns:
        Dict with "input" and "output" pricing in USD per 1M tokens
    """
    # First try the model as-is (to handle :free versions)
    if model in MODEL_PRICING:
        return MODEL_PRICING[model].copy()

    # Check if it's a :free model (even with provider prefix)
    if model.endswith(":free"):
        # Try to find the :free version in our pricing
        free_model = model
        if "/" in free_model:
            # Strip provider prefix but keep :free
            free_model = free_model.split("/", 1)[1]

        if free_model in MODEL_PRICING:
            return MODEL_PRICING[free_model].copy()

        # If we don't have explicit :free pricing, return zero
        return {"input": 0.0, "output": 0.0}

    # Then try normalized version (strips both prefix and :free)
    normalized_model = _normalize_model(model)
    if normalized_model in MODEL_PRICING:
        return MODEL_PRICING[normalized_model].copy()

    # Default to zero cost for unknown models
    return {"input": 0.0, "output": 0.0}


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """
    Calculate the cost of using a model based on token counts.

    Args:
        model: Model name (can include provider prefix)
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        Total cost in USD
    """
    pricing = get_model_pricing(model)

    # Convert from per 1M tokens to per token and calculate cost
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]

    return input_cost + output_cost
