# ADR-0006: Tenacity Retry at Repository Layer

**Status:** Accepted
**Date:** 2026-08-07

## Context

Repository methods use Tenacity's `@retry` decorator to handle transient database errors:

```python
@retry(
    reraise=True,
    stop=stop_after_attempt(5),
    wait=wait_fixed(0.2),
    after=tenacity_retry_log(logger),
)
async def get_by_id(self, widget_id: int) -> Widget:
    ...
```

The retry configuration is applied at the Repository layer — the lowest level of data access. The `nmtfast` library provides `tenacity_retry_log` for structured retry logging.

## Decision

Retry logic lives at the Repository layer with a consistent strategy: up to 5 attempts, 200ms fixed delay between attempts, re-raise on final failure, log each retry. The Service and Router layers do not implement retry — they rely on the Repository to either succeed or raise.

## Consequences

**Positive:**
- Transient database errors (connection drops, lock timeouts) are handled automatically without Service-layer awareness
- Consistent retry behavior across all data access operations
- Retry logging provides visibility into transient failures without cluttering business logic
- Failures propagate cleanly — Service layer sees either success or definitive failure

**Negative:**
- Retry parameters are hardcoded in decorators — changing retry policy requires touching every repository method
- Non-transient errors (e.g., constraint violations) are also retried unnecessarily before failing
- Retry adds latency to failure paths (5 attempts × 200ms = 1s of delay before giving up)

**Guidance:** If retry policy needs to be centralized, consider a wrapper or mixin that applies `@retry` with configurable parameters, rather than removing retry from the Repository layer entirely.
