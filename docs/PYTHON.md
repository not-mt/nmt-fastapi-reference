# Python Standards

- PEP 8: Ensure code follows standard conventions for indention, line length, naming, imports, blank lines, etc.
- PEP 420 (implicit namespace packages): NEVER create `__init__.py` files. The project uses implicit namespace packages. Package directories exist without `__init__.py`.
- PEP 585 (built-in generic types): Use `list[str]`, `dict[str, int]`, etc. instead of `typing.List`, `typing.Dict`.
- PEP 484 (type hints): All non-test code must have PEP 484 compliant type hints.
- PEP 257 (Google style docstrings): All functions and classes must have Google-style docstrings with `"""` on their own lines.
