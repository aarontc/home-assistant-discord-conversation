package main

import (
	"context"

	"dagger/discord-conversation/internal/dagger"

	"golang.org/x/sync/errgroup"
)

// New creates a DiscordConversation CI module.
func New(
	// Project source directory.
	// +defaultPath="."
	// +ignore=[".dagger","*.gen.go",".git",".venv","__pycache__",".pytest_cache",".mypy_cache",".ruff_cache"]
	source *dagger.Directory,
) *DiscordConversation {
	return &DiscordConversation{Source: source}
}

// DiscordConversation provides CI functions for the discord_conversation HA component.
type DiscordConversation struct {
	Source *dagger.Directory
}

// base returns a Python 3.14 container with uv and dev dependencies installed.
func (m *DiscordConversation) base() *dagger.Container {
	return dag.Container().
		From("ghcr.io/astral-sh/uv:python3.14-bookworm").
		WithMountedCache("/root/.cache/uv", dag.CacheVolume("uv-cache")).
		WithDirectory("/src", m.Source).
		WithWorkdir("/src").
		WithExec([]string{"uv", "sync"})
}

// Lint runs ruff check and ruff format --check.
func (m *DiscordConversation) Lint(ctx context.Context) (string, error) {
	return m.base().
		WithExec([]string{"uv", "run", "ruff", "check", "."}).
		WithExec([]string{"uv", "run", "ruff", "format", "--check", "."}).
		Stdout(ctx)
}

// Test runs the full pytest suite.
func (m *DiscordConversation) Test(ctx context.Context) (string, error) {
	return m.base().
		WithExec([]string{"uv", "run", "pytest", "-v", "--tb=short"}).
		Stdout(ctx)
}

// TestLatest runs tests against the newest pytest-homeassistant-custom-component
// (and therefore the latest HA core). Used for nightly CI.
func (m *DiscordConversation) TestLatest(ctx context.Context) (string, error) {
	return dag.Container().
		From("ghcr.io/astral-sh/uv:python3.14-bookworm").
		WithMountedCache("/root/.cache/uv", dag.CacheVolume("uv-cache")).
		WithDirectory("/src", m.Source).
		WithWorkdir("/src").
		WithExec([]string{
			"uv", "lock", "--upgrade-package", "pytest-homeassistant-custom-component",
		}).
		WithExec([]string{"uv", "sync"}).
		WithExec([]string{"uv", "run", "pytest", "-v", "--tb=short"}).
		Stdout(ctx)
}

// All runs lint, test, and the versioning-helper tests concurrently.
func (m *DiscordConversation) All(
	ctx context.Context,
	// +defaultPath="./.dagger/versioning"
	versioningSource *dagger.Directory,
) error {
	eg, ctx := errgroup.WithContext(ctx)
	eg.Go(func() error { _, err := m.Lint(ctx); return err })
	eg.Go(func() error { _, err := m.Test(ctx); return err })
	eg.Go(func() error { _, err := m.TestVersioning(ctx, versioningSource); return err })
	return eg.Wait()
}
