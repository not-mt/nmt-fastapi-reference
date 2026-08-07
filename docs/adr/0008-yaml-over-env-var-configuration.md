# ADR-0008: YAML-Over-Env-Var Configuration

**Status:** Accepted
**Date:** 2026-08-07

## Context

The project uses YAML files as the primary configuration format, consumed by Pydantic Settings. Configuration is merged in layers:

1. **Shared defaults** — `nmtfast-config-default.yaml` (or library defaults)
2. **Environment overrides** — environment-specific YAML files
3. **Local secrets** — `nmtfast-config-local.yaml` (git-ignored)

The `APP_CONFIG_FILES` environment variable specifies which YAML files to load. The `nmtfast.settings.v1.config_files` module handles file discovery and merging. `AppSettings` (a Pydantic `BaseSettings` subclass) is the type-safe consumer of merged configuration.

This contrasts with the 12-factor "env-var-only" approach, where all configuration lives in environment variables.

## Decision

Configuration is YAML-first with layered merging. Environment variables supplement YAML (via `APP_CONFIG_FILES`), but the primary configuration surface is structured YAML files. Pydantic Settings provides validation and type safety at the consumption boundary.

## Consequences

**Positive:**
- **Structured configuration** — YAML files are human-readable, versionable, and support nested structures naturally
- **Layered merging** — defaults, overrides, and secrets compose cleanly without duplication
- **Validation at startup** — Pydantic catches configuration errors before the app starts serving
- **Secrets isolation** — `nmtfast-config-local.yaml` is git-ignored; SOPS encryption is supported as an optional capability
- **Complex config made simple** — ACLs, service discovery, Kafka settings are verbose in env vars but natural in YAML

**Negative:**
- Deviates from 12-factor "config in env" convention
- File-based config requires careful management in containerized deployments (volume mounts, ConfigMaps)
- Merge order is an architectural invariant — getting it wrong causes subtle configuration bugs

**Reversal cost:** Medium-high. Switching to env-var-only would require:
1. Flattening all YAML config into environment variable names
2. Removing the YAML merge engine from `nmtfast`
3. Rewriting `AppSettings` to consume env vars directly
4. Updating deployment pipelines to pass config via env vars instead of file mounts
