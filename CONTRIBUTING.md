# Contributing to LLMGovernor SDKs

Thanks for considering a contribution! These SDKs power how LLMGovernor users
integrate the anomaly engine into their LLM apps.

## Repo layout

```
python/
  llmgovernor/              # core SDK
  llmgovernor-helicone/     # adapter
  llmgovernor-langfuse/     # adapter
  llmgovernor-otel/         # otel exporter
  llmgovernor-litellm/      # litellm callback (deprecated alias for llmgovernor[litellm])
typescript/                 # TS SDK (early, not yet published)
examples/                   # runnable examples
```

## Dev setup

```bash
git clone https://github.com/LLMGovernor/llmgovernor-sdks
cd llmgovernor-sdks
cd python/llmgovernor
pip install -e ".[dev]"
pytest
```

## Pull requests

- One feature/fix per PR
- Include tests
- Run `python -m build` in the affected package to verify it still packages
- Update CHANGELOG.md (top of file) under "Unreleased"

## Issues

Bug reports + feature requests: https://github.com/LLMGovernor/llmgovernor-sdks/issues

For LLMGovernor product feedback (anomaly engine, dashboard, pricing): vivek@earlybrightglobal.com

## License

By contributing, you agree your contributions are licensed under Apache-2.0.
