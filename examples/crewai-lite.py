import os
import litellm
import llmgovernor
import llmgovernor_litellm

# Mock endpoint (e.g., http://localhost:8765)
endpoint = os.environ.get("LLMG_ENDPOINT", "http://localhost:8765")

llmgovernor.init(api_key="test", endpoint=endpoint)
llmgovernor_litellm.register()

# Minimal LiteLLM completion call (mocked server expected)
response = litellm.completion(
    model="gpt-3.5-turbo-0125",
    messages=[{"role": "user", "content": "Hello"}],
    api_base=endpoint,
    api_key="test",
)

print("Completion response:", response)
print("Registered callbacks:", litellm.callbacks)
