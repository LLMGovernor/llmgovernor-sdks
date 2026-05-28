# LLMGovernor SDKs

Official client libraries for [**LLMGovernor**](https://llmgovernor.ai) — the anomaly
engine for LLM apps. Detects cost spikes, error bursts, and latency regressions across
your agents in production.

## Packages

| Package | Description |
|---|---|
| [`llmgovernor`](python/llmgovernor) | Core SDK — auto-patches OpenAI / Anthropic / LiteLLM |
| [`llmgovernor-helicone`](python/llmgovernor-helicone) | Mirror Helicone traces → LLMGovernor anomaly engine |
| [`llmgovernor-langfuse`](python/llmgovernor-langfuse) | Mirror Langfuse traces → LLMGovernor anomaly engine |
| [`llmgovernor-otel`](python/llmgovernor-otel) | Forward OpenTelemetry GenAI spans → LLMGovernor |
| [`llmgovernor-litellm`](python/llmgovernor-litellm) | LiteLLM callback (alt to `llmgovernor[litellm]`) |

## Quick start

```bash
pip install llmgovernor
```

```python
import llmgovernor
llmgovernor.init(api_key="lg_...", agent_name="checkout-agent")

# Your existing OpenAI / Anthropic / LiteLLM calls are now traced.
# Anomalies show up at https://app.llmgovernor.ai/anomalies
```

## Integrate, don't replace

LLMGovernor sits **on top of** your existing observability stack:

- Already on Helicone? `pip install llmgovernor-helicone` — keep Helicone, add anomaly detection.
- Already on Langfuse? `pip install llmgovernor-langfuse` — same idea.
- On OpenTelemetry? `pip install llmgovernor-otel` — point your collector at us.

## Releasing (maintainers)

Trusted Publisher (OIDC) is configured in `.github/workflows/publish.yml`. No API tokens.

```bash
# 1. Bump versions in all 5 python/*/pyproject.toml files
# 2. Tag + push
git tag v0.1.0
git push --tags
# 3. GitHub Actions matrix builds + publishes all 5 packages
```

Prerequisites (one-time setup on PyPI side):

1. Reserve package names on https://pypi.org (one-time): create projects for
   `llmgovernor`, `llmgovernor-helicone`, `llmgovernor-langfuse`,
   `llmgovernor-otel`, `llmgovernor-litellm`.
2. For each project, go to **Manage → Publishing → Add a new pending publisher**:
   - Owner: `LLMGovernor`
   - Repository: `llmgovernor-sdks`
   - Workflow: `publish.yml`
   - Environment: `pypi`
3. Create the `pypi` environment in GitHub repo settings (Settings → Environments → New environment).

After that, every `git tag v*.*.*` ships all 5 packages.

## License

Apache-2.0 © [EarlyBright Global LLC](https://earlybrightglobal.com)
