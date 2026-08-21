# CONTEXT.md

## Project Identity

**nmt-fastapi-reference** is the backend API reference and architectural model for the "nmt" (not-mt) ecosystem of FastAPI microservices. It serves a dual role:

1. **Scaffolding template** — meant to be forked or copied, then customized with project-specific domain entities.
2. **Living reference** — a 100% functional backend that powers downstream apps (e.g., `nmt-fastapi-reference-web`) and demonstrates the canonical patterns all derived projects should follow.

Shared cross-app infrastructure lives in the **nmtfast** library (`../nmt-fastapi-library`). Boundary rule: **if two or more nmt projects need it, it belongs in nmtfast.**

---

## Glossary

### Widget

**SQL exemplar entity.** Demonstrates the relational data-store pattern using SQLAlchemy with async support. Integer primary keys, Alembic-managed migrations, bulk operations, and optional Kafka event publishing.

> When cloning this scaffold, rename `Widget` to your domain entity and adapt the SQLAlchemy models, repository, service, and router accordingly.

### Gadget

**MongoDB exemplar entity.** Demonstrates the document data-store pattern using Motor (async PyMongo). String `ObjectId` keys, flexible schema, bulk operations.

> When cloning this scaffold, rename `Gadget` to your domain entity and adapt the MongoDB collection, repository, service, and router accordingly.

### BackgroundTask

A long-running operation initiated via POST, returning `202 Accepted` with a task UUID. Clients poll a dedicated status endpoint for runtime, errors, and completion state. Task history is persisted for auditability.

- **Exemplar:** `Zap` on Widget and Gadget.
- **Implementation:** Huey task queue. Broker is configurable — SQLite for development, Redis for production.
- **When cloning:** replace "Zap" with your domain's async action (e.g., "GenerateReport", "ProcessUpload").

### ExternalApiIntegration

Pattern for calling external HTTP APIs with proper error handling and service discovery. Demonstrates that **repositories can live in the nmtfast library** and be reused across microservices, avoiding per-service API client duplication.

- **Exemplar:** `/v1/upstream` router uses `nmtfast.repositories.widgets.v1.api.WidgetApiRepository`.
- **When cloning:** add shared API repositories to nmtfast when multiple services need the same external client.

### VerbScopedACL

The access control primitive is a **(section_regex, permissions)** pair. Permissions are CRUD-scoped verb lists (`create`, `read`, `update`, `delete`, or `*`). Sections are regex-matched route prefixes. ACLs attach to authenticated clients or API keys, consumed by the Service layer before operations execute.

- **Infrastructure:** Auth mechanisms (OAuth 2.0 for human clients, API Keys for machine clients) are provided by nmtfast. The microservice controls wiring and ACL configuration.

### LayeredYAMLConfig

Configuration is declarative YAML, merged in priority order: shared defaults → environment overrides → local secrets. The merge order is an architectural invariant — derived projects must follow it. SOPS encryption is supported as an optional capability for secrets management.

- **Consumer:** `AppSettings` (Pydantic model in `app.core.v1.settings`) is the type-safe view of merged configuration.

### CacheAside

Cache is a read-optimization layer. Services check the cache before data stores; misses populate the cache. Writes invalidate. Cache-backed behavior must degrade gracefully when caching is disabled — correctness never depends on the cache.

- **Interface:** `AppCacheBase` from nmtfast, injected into every Service.

### EventPublishing

Optional cross-cutting concern. Services publish domain events to Kafka when mutations occur. The Kafka producer is injected as `Optional` — if Kafka is not configured, events are silently skipped.

- **When cloning:** enable Kafka event publishing only if your deployment topology includes event consumers.

### KubernetesHealth

Health endpoints follow Kubernetes conventions:

- **Liveness** — is the process alive?
- **Readiness** — are all dependencies initialized (DB schema, Kafka consumers/producer)?

Health endpoints are infrastructure-only — they are exempt from the three-layer rule.

### CentralizedExceptionHandlers

All HTTP error responses flow through FastAPI exception handlers registered at startup. Services raise typed, domain-specific exceptions; they never construct HTTP responses directly. Handlers map exceptions to consistent JSON error responses.

### OptionalAIIntegration

Services can expose endpoints as MCP (Model Context Protocol) tools for AI agent consumption via `fastmcp`. Endpoints use `operation_id` annotations for tool discovery.

> **Caution:** MCP introduces overhead and security considerations. It is an opt-in capability — derived projects should evaluate whether AI agent exposure is necessary.

---

## Architectural Rules

### Three-Layer Pattern

```
Router (FastAPI endpoints)
  → Service (business logic, ACL checks, cache, Kafka)
    → Repository (data access: SQLAlchemy, MongoDB, or external API)
```

- **Mandatory for business-logic endpoints.** Every feature involving domain operations MUST follow Router → Service → Repository.
- **Optional for infrastructure endpoints.** Health checks, pure pass-through proxies, and similar non-business endpoints may collapse layers.

### Dependency Injection

Dependencies flow through FastAPI's `Depends()`. Services receive their dependencies (DB sessions, ACLs, settings, cache, optional Kafka) via factory functions in the Router layer.

### Data Migrations

Alembic is the authoritative migration tool for SQLAlchemy models. `Base.metadata.create_all()` in the lifespan function is a **development convenience only** — it creates missing tables but does not apply structured migrations.

> **WARNING:** Relying on `Base.metadata.create_all()` in production without following up with `alembic upgrade head` creates a gap: tables exist but lack migration history. This causes deployment surprises when future migrations assume prior migration state. Always ensure Alembic migrations are the source of truth for schema changes.

### nmtfast Boundary

| Belongs in nmtfast | Stays in this repo |
|--------------------|-------------------|
| Auth & authorization machinery | Domain entities (Widget, Gadget) |
| Logging configuration | Router, Service, Repository implementations |
| Middleware (RequestID, RequestDuration) | `AppSettings` and local configuration |
| Cache interface (`AppCacheBase`) | Alembic migrations |
| Shared API repositories (used by 2+ services) | Huey task definitions |
| Error base classes (`UpstreamApiException`) | Event definitions |
| Settings schemas (`SectionACL`) | |

---

## Bounded Contexts

This is a **single-context repository**. The bounded context is the **nmt-fastapi-reference service** — a FastAPI microservice demonstrating data access, authentication, caching, event publishing, and async task patterns.

Related contexts exist in sibling repositories:
- **nmtfast** — shared infrastructure library
- **nmt-fastapi-reference-web** — frontend consumer of this service's API
