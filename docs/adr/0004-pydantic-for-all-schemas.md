# ADR-0004: Pydantic for All Schemas

**Status:** Accepted
**Date:** 2026-08-07

## Context

Pydantic is used as the universal validation and serialization layer across the project:

- **DTO schemas** (`app.schemas.dto.v1/`) — `WidgetCreate`, `WidgetRead`, `WidgetUpdate`, etc.
- **ORM schemas** (`app.schemas.orm.v1/`) — SQLAlchemy model definitions use Pydantic `model_validate()` for DTO conversion
- **Application settings** (`app.core.v1.settings`) — `AppSettings` extends `pydantic_settings.BaseSettings`
- **Task metadata** — `WidgetZapTask` and related schemas are Pydantic models
- **nmtfast schemas** — `SectionACL`, `AuthSettings`, `LoggingSettings`, etc. are Pydantic models

Pydantic provides validation, serialization (`model_dump`), deserialization (`model_validate`), and OpenAPI schema generation in a single framework.

## Decision

All data contracts — request/response DTOs, configuration schemas, and task metadata — use Pydantic models. No alternative validation frameworks (e.g., Marshmallow, Cerberus, dataclasses with manual validation).

## Consequences

**Positive:**
- Single validation framework across the entire stack — consistent error messages, serialization, and type hints
- Automatic OpenAPI schema generation from Pydantic models — Swagger UI stays in sync with code
- `model_validate()` with `from_attributes=True` enables clean ORM-to-DTO conversion
- `pydantic-settings` provides seamless YAML-to-settings binding with validation at startup

**Negative:**
- Pydantic version upgrades (v1 to v2, future v3) can require breaking changes across all schemas
- Serialization overhead for high-volume endpoints compared to plain dicts
- Tight coupling to Pydantic's API — migrating to another framework requires touching every schema file

**Reversal cost:** High. Every DTO, settings model, and schema conversion would need rewriting.
