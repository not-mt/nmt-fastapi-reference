## Testing Commands

- Activate local environment: source .venv/Scripts/activate || source .venv/bin/activate
- Focused tests: poetry run pytest tests/path/to/test_file.py -k expression
- Full tests: poetry run pytest
- Coverage: poetry run pytest --cov --cov-report term-missing tests
- Lint: poetry run invoke lint
- Fix formatting and imports: poetry run invoke fixers
- Type hints: poetry run invoke mypy
