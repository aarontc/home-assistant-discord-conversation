"""Smoke test: the component imports and the test harness is wired up."""

import json
from pathlib import Path

from custom_components.discord_conversation.const import DOMAIN


def test_domain_constant():
    assert DOMAIN == "discord_conversation"


def test_manifest_is_valid():
    manifest_path = (
        Path(__file__).resolve().parent.parent
        / "custom_components"
        / "discord_conversation"
        / "manifest.json"
    )
    manifest = json.loads(manifest_path.read_text())
    assert manifest["domain"] == DOMAIN
    assert manifest["config_flow"] is True
    assert manifest["requirements"] == ["discord.py==2.7.1"]
    assert manifest["codeowners"] == ["@aarontc"]
