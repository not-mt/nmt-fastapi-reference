# ADR-0009: Settings as Module-Level Singleton

**Status:** Accepted
**Date:** 2026-08-07

## Context

Application settings are loaded once at import time and exposed as a module-level singleton:

```python
# app/core/v1/settings.py (simplified)
_config_data: dict = load_config(get_config_files())
_settings: AppSettings = AppSettings(**_config_data)

def get_app_settings() -> AppSettings:
    return _settings
```

The `_settings` object is created when the module is first imported. `get_app_settings()` returns the same instance on every call. FastAPI's `Depends(get_app_settings)` injects this singleton into endpoints and services.

Several other dependencies follow the same pattern — they rely on `_settings` being available at import time (e.g., OAuth2 scheme initialization in `app.dependencies.v1.auth`).

## Decision

`AppSettings` is loaded once at module import time and shared as a singleton via `get_app_settings()`. Configuration is immutable after startup — settings are not reloaded at runtime.

## Consequences

**Positive:**
- **Zero per-request overhead** — settings are loaded once, not parsed on every request
- **Simple dependency injection** — `Depends(get_app_settings)` returns a pre-built object
- **Startup validation** — configuration errors surface at import time, not at runtime
- **Consistent state** — all code paths see the same configuration; no risk of stale or divergent settings

**Negative:**
- **No hot-reload** — configuration changes require application restart
- **Import-time side effects** — `_settings` is created during module import, which complicates testing (tests must ensure the module is loaded with test config)
- **Tight coupling to file system** — `load_config(get_config_files())` runs at import, so `APP_CONFIG_FILES` must be set before the app starts
- **OAuth scheme initialization** depends on `_settings` at import time, making it difficult to use `Depends()` for the token URL

**Reversal cost:** Medium. Making settings lazy or per-request would require:
1. Converting `_settings` to a lazy-loaded singleton or cached dependency
2. Deferring OAuth scheme initialization to runtime (breaking current `Security()` declarations)
3. Updating all import-time code that references `_settings` directly
