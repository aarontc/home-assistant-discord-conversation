# Contributing

## Development setup

Requires Python 3.14 and [uv](https://docs.astral.sh/uv/). Install dependencies:

```bash
uv sync
```

## Running tests

```bash
uv run pytest
```

## Linting

```bash
uv run ruff check .
```

Fix auto-fixable issues:

```bash
uv run ruff check --fix .
```

## CI

GitLab CI (`.gitlab-ci.yml`) runs `ruff` and `pytest` on every push using the official `ghcr.io/astral-sh/uv:python3.14-bookworm-slim` image. The GitHub mirror runs HACS validation and `hassfest` via `.github/workflows/validate.yaml`.
