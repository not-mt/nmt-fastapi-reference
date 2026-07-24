# Agent Instructions

## Purpose
- This repo is the backend API reference implementation and the architectural model for related FastAPI apps.
- Reuse the nmtfast package for shared authentication, caching, middleware, retry, settings, and other cross-app infrastructure.
- Follow the router, service, repository split used throughout src/app/layers/.

## Primary Goal
- Find the smallest owning slice for the requested behavior and edit there first.
- Keep transport concerns in routers, business rules in services, and persistence or external I/O in repositories.
- Mirror behavior changes with tests in the corresponding tests/ path.

## Python Standards
- PEP 8: Ensure code follows standard conventions for indention, line length, naming, imports, blank lines, etc.
- PEP 420 (implicit namespace packages): NEVER create `__init__.py` files. The project uses implicit namespace packages. Package directories exist without `__init__.py`.
- PEP 585 (built-in generic types): Use `list[str]`, `dict[str, int]`, etc. instead of `typing.List`, `typing.Dict`.
- PEP 484 (type hints): All non-test code must have PEP 484 compliant type hints.
- PEP 257 (Google style docstrings): All functions and classes must have Google-style docstrings with `"""` on their own lines.

## Hard Rules
- Start in the layer that owns the behavior, not the first file that references it.
- Do not leave business logic in routers, schemas, or dependency wiring.
- Do not put shared cross-app infrastructure here when it belongs in nmt-fastapi-library.
- Prefer extending an existing v1 module over creating a parallel abstraction.
- Keep migrations in alembic/versions/ only when a schema or persistence change requires them.
- Do not move frontend or HTMX page behavior into this repo.

## Key Paths
- pyproject.toml: Poetry dependencies and tool configuration.
- src/app/main.py: FastAPI application entrypoint.
- src/app/mcp.py: MCP integration surface.
- src/app/task_loader.py: Task discovery and registration.
- src/app/core/v1/: Foundational app modules such as auth, cache, settings, and resource wiring.
- src/app/dependencies/: Shared dependency injection helpers.
- src/app/errors/: App-specific error definitions and handling.
- src/app/events/v1/: Application event modules.
- src/app/schemas/dto/: Request and response transfer models.
- src/app/schemas/orm/: ORM models.
- src/app/tasks/v1/: Task modules and handlers.
- src/app/utils/: Shared helpers.
- src/app/layers/router/v1/: HTTP endpoints.
- src/app/layers/service/v1/: Business logic and orchestration.
- src/app/layers/repository/v1/: Persistence and external API access.
- alembic/: Migration environment and revision history.
- tests/: Test tree mirrors src/app/.
- tests/core/: Core tests.
- tests/dependencies/: Dependency tests.
- tests/errors/: Error-handling tests.
- tests/layers/router/v1/: Router tests.
- tests/layers/service/v1/: Service tests.
- tests/layers/repository/v1/: Repository tests.
- tests/tasks/: Task tests.
- tests/test_main.py: Application entrypoint tests.
- tests/test_mcp.py: MCP integration tests.
- tests/test_task_loader.py: Task loader tests.

## How To Route Changes
- New API endpoint: start in src/app/layers/router/v1/, then update service, repository, and schemas as needed.
- Business rule or orchestration change: start in src/app/layers/service/v1/.
- Persistence, database, or external API change: start in src/app/layers/repository/v1/.
- Shared dependency wiring or app resource setup: start in src/app/dependencies/ or src/app/core/v1/.
- App-specific error handling: start in src/app/errors/.
- Background or startup task registration: start in src/app/task_loader.py and src/app/tasks/v1/.
- API contracts and persistence models: start in src/app/schemas/.
- MCP behavior: start in src/app/mcp.py and update tests/test_mcp.py.
- Database schema changes: update the owning ORM or repository code and add or update the corresponding alembic revision.

## Test Mapping
- src/app/main.py -> tests/test_main.py
- src/app/mcp.py -> tests/test_mcp.py
- src/app/task_loader.py -> tests/test_task_loader.py
- src/app/core/ -> tests/core/
- src/app/dependencies/ -> tests/dependencies/
- src/app/errors/ -> tests/errors/
- src/app/layers/router/v1/ -> tests/layers/router/v1/
- src/app/layers/service/v1/ -> tests/layers/service/v1/
- src/app/layers/repository/v1/ -> tests/layers/repository/v1/
- src/app/tasks/ -> tests/tasks/
- Add new tests for new behavior and update existing tests when behavior changes.

## Workspace Boundaries
- nmt-fastapi-reference/: Backend API behavior and reference architecture belong here.
- ../nmt-fastapi-library/: Shared reusable infrastructure belongs there.
- ../nmt-fastapi-reference-web/: HTMX pages, templates, and web UI behavior belong there.
- Do not move shared primitives into this repo when they can live in the library.

## Conventions That Matter Most
- Keep routers thin. They should translate HTTP requests into service calls and response models.
- Keep services responsible for orchestration and business decisions.
- Keep repositories responsible for persistence and external I/O.
- Keep schemas focused on data contracts rather than business logic.
- Prefer versioned modules under v1/ for new router, service, repository, core, event, and task work unless the existing structure requires otherwise.
- Tool-driven formatting and lint behavior are defined by pyproject.toml and the commands below.

## Validation Workflow
- Prefer poetry run commands instead of relying on shell activation state.
- During iteration, run the narrowest relevant pytest target for the touched area first.
- After the first passing focused test, run the full project test suite.
- If you add or change Python code, also run coverage, lint, and type checks before finishing.
- If you only change Markdown or other documentation files, file-level validation is sufficient.

## Commands
- Activate local environment: source .venv/Scripts/activate || source .venv/bin/activate
- Focused tests: poetry run pytest tests/path/to/test_file.py -k expression
- Full tests: poetry run pytest
- Coverage: poetry run pytest --cov=app --cov-report term-missing tests
- Lint: poetry run invoke lint
- Fix formatting and imports: poetry run invoke fixers
- Type hints: poetry run invoke mypy
