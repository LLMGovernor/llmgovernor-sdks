# Changelog

All notable changes to LLMGovernor SDKs are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] — 2026-05-27

### Added
- Initial release of the LLMGovernor SDK monorepo.
- `llmgovernor` — core SDK with auto-patching for OpenAI / Anthropic / LiteLLM.
- `llmgovernor-helicone` — adapter scaffolding (full impl pre-launch).
- `llmgovernor-langfuse` — adapter scaffolding (full impl pre-launch).
- `llmgovernor-otel` — OpenTelemetry GenAI span exporter.
- `llmgovernor-litellm` — legacy package; prefer `pip install llmgovernor[litellm]`.
- GitHub Actions publish workflow using PyPI Trusted Publisher (OIDC).
