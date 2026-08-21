# ADR-0003: Versioned Module Directories

**Status:** Accepted
**Date:** 2026-08-07

## Context

All application code lives under versioned directories:

```
src/app/
├── core/v1/
├── dependencies/v1/
├── errors/v1/
├── events/v1/
├── layers/
│   ├── repository/v1/
│   ├── router/v1/
│   └── service/v1/
├── schemas/
│   ├── dto/v1/
│   └── orm/v1/
└── tasks/v1/
```

Every module path includes `v1/` as a version segment. The same pattern is mirrored in the `nmtfast` library.

## Decision

Module directories are versioned (`v1/`, future `v2/`, etc.) to enable parallel API versions during migrations. New major versions of internal interfaces coexist alongside older versions rather than replacing them in-place.

## Consequences

**Positive:**
- **Slow internal migration** — code can migrate from `v1` to `v2` incrementally, module by module, without breaking consumers still on `v1`
- **Backwards compatibility** — routers, services, and repositories for different API versions can coexist in the same codebase
- **Clear version boundaries** — imports explicitly reference the version, making dependency versions visible at the call site
- **Safe deprecation** — old versions remain functional while new versions are tested and adopted

**Negative:**
- Deeper import paths (`from app.layers.repository.v1.widgets import WidgetRepository`)
- Duplicate code during migration periods when both `v1` and `v2` exist
- New developers may be confused about when to create `v2` vs. modify `v1`

**Guidance for derived projects:** Retain the versioned directory structure. Do not flatten `v1/` into its parent — the cost of re-adding versioning later outweighs the initial depth.
