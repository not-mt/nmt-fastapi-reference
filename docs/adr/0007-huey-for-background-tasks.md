# ADR-0007: Huey for Background Tasks

**Status:** Accepted
**Date:** 2026-08-07

## Context

The project uses Huey as the background task framework for the BackgroundTask pattern (exemplar: "Zap"). Huey is configured with a configurable broker — SQLite for development, Redis for production.

Key integration points:
- `app.core.v1.tasks` — Huey app initialization
- `app.tasks.v1/` — Task definitions (e.g., `widget_zap_task`)
- `app.task_loader.py` — Task discovery and registration
- `nmtfast.tasks.v1.huey` — Shared utilities (`store_task_metadata`, `fetch_task_result`, `fetch_task_metadata`)
- Service layer schedules tasks via `task.schedule()` and stores metadata in Huey's storage

## Decision

Huey is the background task framework. Task definitions live in `app.tasks.v1/`. Task metadata is stored in Huey's storage for polling. The broker is configurable (SQLite dev, Redis prod).

## Consequences

**Positive:**
- Lightweight — Huey has minimal overhead compared to Celery
- Simple API — `@huey.task()` decorator, `.schedule()`, `.get()` are straightforward
- SQLite broker eliminates external dependencies for development
- Redis broker integrates with the existing Redis cache infrastructure in production
- Synchronous and async task execution supported

**Negative:**
- Smaller ecosystem than Celery — fewer third-party integrations and monitoring tools
- Huey-specific APIs are baked into task definitions, metadata storage, and the polling endpoints
- Scaling Huey workers requires separate process management (not handled by the FastAPI server)

**Reversal cost:** High. Switching to Celery or RQ would require:
1. Rewriting all task definitions with the new framework's decorators
2. Replacing Huey metadata storage with the new framework's result backend
3. Updating the Service layer's task scheduling and polling logic
4. Replacing `nmtfast.tasks.v1.huey` utilities with framework-agnostic equivalents
