"""Pytest bootstrap: load pytest-homeassistant-custom-component and expose the
component to HA's integration loader via a symlink into testing_config.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

_REPO_ROOT = Path(__file__).resolve().parent.parent
_COMPONENT_DIR = _REPO_ROOT / "custom_components" / "discord_conversation"

if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _ensure_component_symlink_in_testing_config() -> None:
    try:
        import pytest_homeassistant_custom_component as phcc
    except ImportError:
        return

    target = (
        Path(phcc.__file__).resolve().parent
        / "testing_config"
        / "custom_components"
        / "discord_conversation"
    )
    if target.is_symlink():
        try:
            if target.resolve() == _COMPONENT_DIR.resolve():
                return
        except OSError:
            pass
        target.unlink()
    elif target.exists():
        print(
            f"[discord_conversation conftest] warning: {target} exists and is "
            "not a symlink; skipping auto-link.",
            file=sys.stderr,
        )
        return

    target.parent.mkdir(parents=True, exist_ok=True)
    os.symlink(_COMPONENT_DIR, target)


_ensure_component_symlink_in_testing_config()

pytest_plugins = ["pytest_homeassistant_custom_component"]


@pytest.fixture
async def setup_core_components(hass: HomeAssistant) -> None:
    """Set up the homeassistant component so the conversation dependency can load.

    Adding ``"dependencies": ["conversation"]`` to manifest.json causes HA's loader
    to set up the conversation component before loading discord_conversation.  The
    conversation component's default agent calls async_should_expose during startup,
    which requires homeassistant.exposed_entities to be registered in hass.data.
    Setting up the homeassistant component here satisfies that requirement.
    """
    await async_setup_component(hass, "homeassistant", {})
