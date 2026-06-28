# Changelog

All notable changes to this project are recorded here. Versions and tags are
created automatically on `main` by the `tag:auto` CI job from commit subject
prefixes (`(Major)` / `(Minor)` / `(Patch)`); this file is a curated, human-
readable companion that highlights user-facing changes.

## Unreleased

### Added

- **Automated release pipeline.** Pushes to `main` are linted, tested, and
  auto-versioned by Dagger: the `tag:auto` GitLab CI job computes the next
  semantic version from `(Major)/(Minor)/(Patch)` commit subjects, commits the
  version bump, and tags via the GitLab API. The GitHub mirror's
  `release.yaml` workflow then publishes a GitHub Release per tag (which is
  what HACS reads to detect new versions).

## 0.1.0

Initial release. Bridges the Home Assistant Assist conversation agent to a
Discord bot: selected channels, `@mentions`, and direct messages route to a
configured conversation agent and the reply is posted back. Includes
per-channel/per-DM conversation context with idle reset, a typing indicator,
Discord-to-Home-Assistant user mapping with a least-privilege fallback user, a
config and options flow, and reauthentication.
