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
    with pytest.raises(LovelaceYamlError, match="No supported card found"):
        convert_lovelace_yaml("type: custom:unknown-card\nentity: sensor.example")


def test_rejects_wrong_helper_domain() -> None:
    """Role-specific helper domains are validated during conversion."""
    with pytest.raises(LovelaceYamlError, match="search_entity must use the input_text domain"):
        convert_lovelace_yaml(MEALIE_CARD.replace("input_text.recipe_search_query", "sensor.recipe_search_query"))