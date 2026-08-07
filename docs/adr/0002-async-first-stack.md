# ADR-0002: Async-First Stack

**Status:** Accepted
**Date:** 2026-08-07

## Context

This project uses an end-to-end asynchronous stack:

- **FastAPI** — async route handlers
- **SQLAlchemy 2.0** — `ext.asyncio` with `AsyncSession`
- **Motor** — async MongoDB driver
- **aiokafka** — async Kafka producer and consumer
- **aiosqlite** / **asyncpg** / **aiomysql** — async database adapters
- **Huey** — async-compatible task queue

Every layer — Router, Service, and Repository — is built on `async/await`. There are no synchronous fallbacks.

## Decision

All I/O-bound operations use async drivers and async handlers. No synchronous endpoints, no synchronous database sessions, no blocking calls within the event loop.

## Consequences

**Positive:**
- High throughput under concurrent load — non-blocking I/O across the entire request pipeline
- Single-threaded event loop handles many concurrent connections efficiently
- Consistent mental model — every data access call is `await`

**Negative:**
- Refactoring to a sync stack (or hybrid sync/async) would require rewriting every layer: route handlers, service methods, repository methods, and dependency injection
- CPU-bound work still blocks the event loop — requires offloading to thread/process pools
- Some libraries lack mature async drivers

**Reversal cost:** Very high. Moving away from async-first would require:
1. Replacing all async drivers with sync equivalents
2. Converting every `async def` to `def` across Routers, Services, and Repositories
3. Rewriting dependency injection to provide sync sessions/connections
4. Replacing Huey's async task integration with sync equivalents
5. Updating all tests from `pytest-asyncio` to synchronous fixtures
