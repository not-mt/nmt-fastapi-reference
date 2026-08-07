# ADR-0001: Alembic Migrations Over `create_all()`

**Status:** Accepted
**Date:** 2026-08-07
**Context discovered during:** Foundational domain documentation grilling session

## Context

The application lifespan runs `Base.metadata.create_all()` to ensure database tables exist on startup. This is convenient for development — new tables appear automatically without manual migration steps.

However, `create_all()` has a critical limitation: it only **creates missing tables**. It does not:
- Apply column additions or modifications to existing tables
- Create or alter indexes
- Execute data migrations
- Record migration history in `alembic_version`

This creates a deployment trap: a developer adds a column to an ORM model, tests locally (where `create_all()` creates the new table or column), then deploys to production where the table already exists — and the column change never applies.

## Decision

- Alembic migrations are the **authoritative source of truth** for all SQLAlchemy schema changes.
- `Base.metadata.create_all()` is retained as a **development convenience only** — it handles the "first run" case but must not be relied upon for schema correctness in production.
- Every structural change to ORM models (new columns, type changes, indexes, constraints) **must** be captured in an Alembic migration.

## Consequences

**Positive:**
- Clear, reproducible schema evolution across environments
- Migration history is tracked in `alembic_version`
- Deployment pipelines can verify migration state

**Negative:**
- Additional step for developers: every model change requires `alembic revision --autogenerate`
- Risk of skipping migrations if developers rely on `create_all()` locally

**Mitigation:**
- Pre-commit hooks or CI checks could verify that ORM models and Alembic migrations are in sync
- Developer documentation should emphasize the migration workflow
