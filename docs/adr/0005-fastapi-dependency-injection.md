# ADR-0005: FastAPI Dependency Injection (No DI Container)

**Status:** Accepted
**Date:** 2026-08-07

## Context

The project uses FastAPI's built-in dependency injection system (`Depends()`) for wiring components:

```python
# Router layer — factory function creates Service with all dependencies
def get_widget_service(
    db: AsyncSession = Depends(get_sql_db),
    acls: list[SectionACL] = Depends(get_acls),
    settings: AppSettings = Depends(get_settings),
    cache: AppCacheBase = Depends(get_cache),
    kafka: Optional[AIOKafkaProducer] = Depends(get_kafka_producer),
) -> WidgetService:
    return WidgetService(WidgetRepository(db), acls, settings, cache, kafka)

# Endpoint consumes the factory
async def widget_create(
    widget: WidgetCreate,
    widget_service: WidgetService = Depends(get_widget_service),
) -> WidgetRead:
    ...
```

Dependencies flow: endpoint → service factory → service → repository. No external DI container (e.g., dependency-injector, Inject) is used.

## Decision

FastAPI's `Depends()` is the sole dependency injection mechanism. Services are instantiated via factory functions in the Router layer. No external DI container manages object lifecycles or injection graphs.

## Consequences

**Positive:**
- Zero additional dependencies — DI is a framework feature, not a library
- Declarative dependency graphs are visible in function signatures
- FastAPI handles lifecycle management (per-request, per-app, cached dependencies)
- Testable — dependencies are overridden with `app.dependency_overrides`

**Negative:**
- Service instantiation logic lives in Router modules, not a centralized configuration
- Complex dependency graphs become harder to trace than explicit container wiring
- Moving to a different web framework would require a new DI strategy
- No compile-time validation of dependency graphs — missing dependencies surface at runtime

**Reversal cost:** Medium-high. Introducing a DI container later would require:
1. Extracting all `Depends()` signatures into container provider definitions
2. Rewiring service instantiation from factory functions to container resolution
3. Updating test overrides to use container mocking instead of `dependency_overrides`
