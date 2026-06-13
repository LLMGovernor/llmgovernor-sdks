# Changelog

All notable changes to LLMGovernor SDKs are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [llmgovernor-litellm 0.1.2] — 2026-06-13

### Fixed
- Moved `llmgovernor>=0.3.0` and `litellm>=1.37.8,<2` from optional extras to core
  `dependencies` so that `pip install llmgovernor-litellm` auto-installs both and the
  package is importable without the `[litellm]` extra flag.

### Note
This package is deprecated. Prefer `pip install "llmgovernor[litellm]"` which ships
the same callback as part of the core SDK.

## [llmgovernor 0.3.0] — 2026-06-13

### Added
- Superset merge: all 0.2.0 public symbols preserved (instrument, Fleet, CostEvent,
  LLMGovernorClient, BlazeClient, agent/agent_context/get_current_agent, set_metadata,
  get_metadata, clear_metadata, calculate_cost, get_model_pricing, wrap_openai_client,
  wrap_anthropic_client, wrap_bedrock_client).
- New transport layer: `Transport`, `init()`, `get_transport()`, `reset_transport()` —
  required by llmgovernor-litellm and the lean adapter pattern.
- Dropped hard deps on httpx and pydantic (stdlib-only core, optional extras pinned).

### Migration
No migration needed from 0.2.0. All existing import patterns continue to work.

## [0.1.0] — 2026-05-27

### Added
- Initial release of the LLMGovernor SDK monorepo.
- `llmgovernor` — core SDK with auto-patching for OpenAI / Anthropic / LiteLLM.
- `llmgovernor-helicone` — adapter scaffolding (full impl pre-launch).
- `llmgovernor-langfuse` — adapter scaffolding (full impl pre-launch).
- `llmgovernor-otel` — OpenTelemetry GenAI span exporter.
- `llmgovernor-litellm` — legacy package; prefer `pip install llmgovernor[litellm]`.
- GitHub Actions publish workflow using PyPI Trusted Publisher (OIDC).
