"""Unit tests for user-facing agent tool labels."""

from agents.constants import FRIENDLY_TOOL_LABELS, get_friendly_label


def test_known_tool_returns_friendly_label() -> None:
    tool_name, expected_label = next(iter(FRIENDLY_TOOL_LABELS.items()))

    assert get_friendly_label(tool_name) == expected_label


def test_unknown_tool_returns_original_name() -> None:
    assert get_friendly_label("custom_tool") == "custom_tool"
