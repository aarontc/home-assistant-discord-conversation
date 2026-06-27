import pytest

from custom_components.discord_conversation.text_utils import (
    chunk_message,
    strip_self_mention,
)


def test_chunk_short_message_single_chunk():
    assert chunk_message("hello") == ["hello"]


def test_chunk_empty_returns_single_empty():
    assert chunk_message("") == [""]


def test_chunk_splits_on_line_boundaries_under_limit():
    text = "\n".join(["line"] * 10)
    chunks = chunk_message(text, limit=12)
    assert all(len(c) <= 12 for c in chunks)
    assert "".join(chunks) == text


def test_chunk_hard_splits_overlong_single_line():
    chunks = chunk_message("x" * 5000, limit=2000)
    assert [len(c) for c in chunks] == [2000, 2000, 1000]
    assert "".join(chunks) == "x" * 5000


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("<@123> hello", "hello"),
        ("<@!123> hello", "hello"),
        ("hey <@123> there", "hey  there".strip()),
        ("no mention", "no mention"),
        ("<@999> keep other", "<@999> keep other"),
    ],
)
def test_strip_self_mention(content, expected):
    assert strip_self_mention(content, 123) == expected
