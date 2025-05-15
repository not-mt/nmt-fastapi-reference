# nmt-fastapi-reference

A FastAPI-based microservice leveraging the `nmtfast` Python package for structured access control, logging, and caching.

## Features

- **OAuth 2.0 & API Key Authentication**: Secure endpoints using `nmtfast`'s authentication and authorization methods.
- **Role-Based & Resource-Based ACLs**: Fine-grained access control managed via YAML configurations.
- **Asynchronous API Handling**: Fully async support using FastAPI and SQLAlchemy async drivers.
- **Structured Logging**: Custom formatting, control over loggers on a per-module basis, and unique IDs recorded for each request.
- **Docker Examples**: Easily deployable with a provided `Dockerfile` and sample `docker-compose.yaml`
- **Merged Configuration Files**: Configuration settings may be merged from multiple sources using `nmtfast`, allowing secrets to be isolated to separate configuration files.

## Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL, MySQL, or MongoDB database
- Redis

### Prepare Development Environment

Clone the repository and install dependencies using Poetry:

```bash
git clone https://github.com/not-mt/nmt-fastapi-reference.git
cd nmt-fastapi-reference
```

Create a virtual environment and install Poetry:

```bash
test -d .venv || python -m venv .venv
source .venv/Scripts/activate
pip install poetry
cp samples/poetry.toml .
```

Install dependencies:

```bash
poetry install
```

Install pre-commit:

```bash
pre-commit install
```

### OPTIONAL: VS Code (on Windows)

Follow these steps if you are developing on a Windows system and have a bash shell available (most likely from [Git for Windows](https://git-scm.com/downloads/win)).

Copy samples:

```bash
cp -urv samples/{.local,.vscode,*} .
```

These files will be excluded by `.gitignore`, and you may customize however you would like. These are the notable files:

- **.local/activate.env**
  - This file will be sourced in a custom terminal profile (defined in `nmt-fastapi-reference.code-workspace` )
  - Customize `PROJECTS` to reflect the root path to your software projects
- **.vscode/launch.json**
  - Template of how to start the project in VS Code's debugger; adjust if necessary
- **nmt-fastapi-reference.code-workspace**
  - Sensible defaults are specified here and may be customized as necessary
  - A `terminal.integrated.defaultProfile.windows` is set to use the `.local/activate.env` file when starting new terminals

**NOTE:** You can update `PROJECTS` in `.local/activate.env` file manually, or you can use this command to update it for you. This will set the value to the parent directory of your current directory:

```bash
# get the parent directory, and replace /c/path with C:/path
rpd=$(dirname "$(pwd)" | sed -E 's|^/([a-z])|\U\1:|')
sed \
  -e 's|# export PROJECTS=".*FIXME.*$|export PROJECTS="'"$rpd"'"|' \
  -i .local/activate.env
```

Test the activate script:

```bash
source .local/activate.env
```

Once files have been customized, you may re-open VS Code using the `nmt-fastapi-reference.code-workspace` file.

### Configuration

This service is configured using YAML configuration files. You may copy the `nmtfast-config-default.yaml` and update as necessary:

```bash
cp nmtfast-config-default.yaml nmtfast-config-local.yaml
$EDITOR nmtfast-config-local.yaml
```

For local testing, you probably only need to generate an API key. A utility is included with this project to generate password hashes:

```bash
./generate-api-hash.py
```

Place the generated hash in the `nmtfast-config-local.yaml` config file; for example:

```yaml
---
version: 1
sqlalchemy:
  url: sqlite+aiosqlite:///./development.sqlite
  # url: mysql+aiomysql://user:passwd@dbhost:3306/nmtfastdev1?charset=utf8mb4
  # url: postgresql+asyncpg://user:passwd@dbhost:5432/nmtfastdev1
auth:
  swagger_token_url: https://some.domain.tld/api/oidc/token
  id_providers: {}
  clients: {}
  api_keys:
    some_key:
      contact: some.user@domain.tld
      memo: This is just some API key
      algo: argon2
      hash: '$argon2id$v=19$m=65536,t=3,p=4$tWmX...'
      acls:
        - section_regex: '^widgets$'
          #permissions: ['*']
          permissions: ['create', 'read']
logging:
  level: DEBUG
  loggers:
    "aiosqlite":
      level: INFO
    "some.other.module.*":
      level: INFO
```


### Running the Service

You may run the service using a command like this:

```bash
export APP_CONFIG_FILES="./nmtfast-config-local.yaml"
poetry run uvicorn app.main:app --reload
```

**OPTIONAL:** If Docker is available, you may run the service like this:

```bash
cp samples/docker-compose.yaml .
docker-compose build
docker-compose up
```

## Invoke Tasks

Invoke is included with this project so that repetitive tasks such as pytest, mypy, etc. can be bundled into simple task names without requiring complex arguments each time. For example, this will check static type hints for the entire project:

```bash
poetry run invoke mypy
```

Run `poetry run invoke --complete` to see all available tasks.

## Testing

Verify all `pre-commit` checks are working:

```bash
pre-commit run --all-files
```

Verify code coverage and unit tests:

```bash
poetry run invoke coverage
```

## Contributing

Contributions are welcome! Please submit a pull request or open an issue.

## License

This project is licensed under the [MIT License](LICENSE).

Copyright (c) 2025 Alexander Haye
