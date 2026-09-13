"""Tests for converting supported Lovelace YAML into Butler panels."""

import importlib.util
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[1] / "custom_components/biofects_butler/lovelace_yaml.py"
SPEC = importlib.util.spec_from_file_location("butler_lovelace_yaml", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
LovelaceYamlError = MODULE.LovelaceYamlError
convert_lovelace_yaml = MODULE.convert_lovelace_yaml


MEALIE_CARD = """
type: custom:mealie-recipe-browser
view_layout:
  grid-column: 1 / -1
results_entity: sensor.recipe_search_results
search_entity: input_text.recipe_search_query
selected_entity: input_text.recipe_selected_id
detail_entity: sensor.selected_recipe
default_image: /local/images/recipe-default.jpg
"""


def test_converts_mealie_card() -> None:
    """A pasted Mealie card maps every helper to its native Butler role."""
    result = convert_lovelace_yaml(MEALIE_CARD)

    assert result["type"] == "recipe_browser"
    assert result["full_page"] is True
    assert result["default_image"] == "/local/images/recipe-default.jpg"
    assert [binding["role"] for binding in result["bindings"]] == [
        "recipe_results",
        "recipe_search",
        "recipe_selected",
        "recipe_detail",
    ]


def test_converts_card_from_dashboard_view() -> None:
    """Users may paste the entire view rather than extracting its card."""
    card_lines = MEALIE_CARD.strip().splitlines()
    result = convert_lovelace_yaml(
        "views:\n  - title: Cookbook\n    path: cookbook\n    cards:\n"
        + f"      - {card_lines[0]}\n"
        + "\n".join(f"        {line}" for line in card_lines[1:])
    )

    assert result["title"] == "Cookbook"
    assert result["bindings"][0]["target_id"] == "sensor.recipe_search_results"


def test_rejects_unsupported_card() -> None:
    """Unsupported custom cards fail clearly instead of producing a broken panel."""
    with pytest.raises(LovelaceYamlError, match="cannot be converted automatically"):
        convert_lovelace_yaml("type: custom:unknown-card\nentity: sensor.example")


def test_rejects_wrong_helper_domain() -> None:
    """Role-specific helper domains are validated during conversion."""
    with pytest.raises(LovelaceYamlError, match="search_entity must use the input_text domain"):
        convert_lovelace_yaml(MEALIE_CARD.replace("input_text.recipe_search_query", "sensor.recipe_search_query"))


def test_converts_standard_entities_card() -> None:
    """Standard entity cards retain entities and infer the native panel type."""
    result = convert_lovelace_yaml(
        """type: entities
title: Entry
entities:
  - lock.front_door
  - entity: sensor.front_door_battery
"""
    )

    assert result["type"] == "security"
    assert result["title"] == "Entry"
    assert [binding["target_id"] for binding in result["bindings"]] == [
        "lock.front_door",
        "sensor.front_door_battery",
    ]


def test_converts_button_stack_actions() -> None:
    """Nested button actions become editable native Quick Commands."""
    result = convert_lovelace_yaml(
        """type: horizontal-stack
cards:
  - type: button
    name: Dinner
    icon: mdi:food
    tap_action:
      action: perform-action
      perform_action: script.dinner_time
  - type: button
    name: Lights
    entity: light.kitchen
    tap_action:
      action: toggle
"""
    )

    assert result["type"] == "entity_controls"
    assert result["bindings"] == [{"kind": "entity", "target_id": "light.kitchen"}]
    assert result["actions"][0] == {
        "gesture": "tap",
        "name": "Dinner",
        "icon": "mdi:food",
        "type": "call_service",
        "domain": "script",
        "service": "dinner_time",
    }
    assert result["actions"][1]["type"] == "toggle"


def test_rejects_standard_card_without_convertible_content() -> None:
    """Cards without native entities or actions receive a useful error."""
    with pytest.raises(LovelaceYamlError, match="no entities or actions"):
        convert_lovelace_yaml("type: markdown\ncontent: Hello")