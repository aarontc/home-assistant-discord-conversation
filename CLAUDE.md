# CLAUDE.md

Guidance for Claude Code working in this repository.

## Before pushing

CI runs `dagger call all`, which includes both `ruff check` AND
`ruff format --check`. Running only one locally is not sufficient.

Quick path (no Dagger needed), from the repo root:

```sh
uv run ruff check . && uv run ruff format --check . && uv run pytest
```

CI-equivalent path (slower, requires Docker):

```sh
dagger call all
```

A `pre-commit` hook in `hooks/pre-commit` runs `dagger call lint`
automatically, but only after a one-time `git config core.hooksPath hooks`.
If the hook isn't installed in this clone, the local commands above are the
safety net.

## Commit subjects

Every commit subject must start with `(Major)`, `(Minor)`, or `(Patch)`
(enforced by `hooks/commit-msg` when hooks are enabled, and required by the
`tag:auto` CI job that computes the next version). For example:

- `(Patch) bot: ignore webhook messages`
- `(Minor) config_flow: add per-guild channel filtering`

Avoid the literal string `skip ci` anywhere in subject or body — GitLab
treats it as a pipeline suppressor and `tag:auto` won't run.

No em dashes in commit messages: use commas, colons, or parentheses.

## Versioning

The `tag:auto` CI job on `main` reads commit subjects, computes the next
version, writes `(Patch) release: bump version to X.Y.Z` as its own commit,
and tags. The bump commit rewrites **only** `pyproject.toml` and
`custom_components/discord_conversation/manifest.json` — so **don't manually
edit those version strings** in content commits (it makes the bot's bump
redundant). It does **not** touch `uv.lock`, whose project version therefore
lags after releases; that's a known gap — run `uv lock` separately if you
need it aligned.

## Test layout

Tests live at the repo root under `tests/` and run with
`pytest-homeassistant-custom-component`. `tests/conftest.py` puts the repo
root on `sys.path`, loads the phcc plugin, symlinks the component into the
harness's `testing_config/`, and sets up the `homeassistant` core component
(needed because the integration declares `dependencies: ["conversation"]`).
Config-flow, options-flow, and setup/unload tests declare an autouse
`auto_enable_custom_integrations(enable_custom_integrations)` fixture so HA
loads the custom integration; pure-unit tests do not.

## See also

- `CONTRIBUTING.md` — Dagger setup, hook installation, versioning policy,
  manual tag creation, GitHub release publishing
- `README.md` — user-facing description and HACS install
