"""Convert supported Lovelace YAML cards into native Butler panels."""

from __future__ import annotations

import re
from typing import Any

import yaml

MAX_YAML_LENGTH = 20_000
MEALIE_CARD_TYPE = "custom:mealie-recipe-browser"
ENTITY_PATTERN = re.compile(r"^[a-z0-9_]+\.[a-z0-9_]+$")


class LovelaceYamlError(ValueError):
    """Raised when pasted Lovelace YAML cannot be converted."""


def convert_lovelace_yaml(source: str) -> dict[str, Any]:
    """Parse pasted YAML and return one normalized Butler panel definition."""
    if not source.strip():
        raise LovelaceYamlError("Paste a Lovelace card or view before converting.")
    if len(source) > MAX_YAML_LENGTH:
        raise LovelaceYamlError("Pasted YAML is too large. Limit it to one card or view.")
    try:
        value = yaml.safe_load(source)
    except yaml.YAMLError as error:
        raise LovelaceYamlError("The pasted text is not valid YAML.") from error
    if not isinstance(value, dict):
        raise LovelaceYamlError("The YAML must contain a Lovelace card or view object.")

    card, title = _find_mealie_card(value)
    if card is None:
        raise LovelaceYamlError(
            f"No supported card found. Currently supported: {MEALIE_CARD_TYPE}."
        )

    fields = (
        ("results_entity", "recipe_results", "sensor"),
        ("search_entity", "recipe_search", "input_text"),
        ("selected_entity", "recipe_selected", "input_text"),
        ("detail_entity", "recipe_detail", "sensor"),
    )
    bindings = []
    for field, role, domain in fields:
        entity_id = card.get(field)
        if not isinstance(entity_id, str) or not ENTITY_PATTERN.fullmatch(entity_id):
            raise LovelaceYamlError(f"{field} must be a valid Home Assistant entity ID.")
        if not entity_id.startswith(f"{domain}."):
            raise LovelaceYamlError(f"{field} must use the {domain} domain.")
        bindings.append({"kind": "entity", "target_id": entity_id, "role": role})

    view_layout = card.get("view_layout")
    full_page = isinstance(view_layout, dict) and view_layout.get("grid-column") == "1 / -1"
    return {
        "type": "recipe_browser",
        "title": str(title or "Recipes")[:80],
        "bindings": bindings,
        "default_image": str(card.get("default_image") or "/local/images/recipe-default.jpg")[:500],
        "full_page": full_page,
    }


def _find_mealie_card(value: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """Find a Mealie card in a card, cards wrapper, or dashboard view wrapper."""
    title = value.get("title") if isinstance(value.get("title"), str) else None
    if value.get("type") == MEALIE_CARD_TYPE:
        return value, title
    cards = value.get("cards")
    if isinstance(cards, list):
        for card in cards:
            if isinstance(card, dict) and card.get("type") == MEALIE_CARD_TYPE:
                return card, title
    views = value.get("views")
    if isinstance(views, list):
        for view in views:
            if isinstance(view, dict):
                card, view_title = _find_mealie_card(view)
                if card is not None:
                    return card, view_title
    return None, title