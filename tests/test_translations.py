import json
from pathlib import Path


def _load(name):
    base = (
        Path(__file__).resolve().parent.parent
        / "custom_components"
        / "discord_conversation"
    )
    return json.loads((base / name).read_text())


def test_strings_and_en_translation_match():
    assert _load("strings.json") == _load("translations/en.json")


def test_config_steps_have_titles():
    strings = _load("strings.json")
    for step in ("user", "config", "reauth_confirm"):
        assert step in strings["config"]["step"]
    for step in ("init", "settings", "add_user_map", "remove_user_map"):
        assert step in strings["options"]["step"]
    assert "invalid_auth" in strings["config"]["error"]
