"""Convert supported Lovelace YAML cards into native Butler panels."""

from __future__ import annotations

import re
from typing import Any

import yaml

MAX_YAML_LENGTH = 20_000
MEALIE_CARD_TYPE = "custom:mealie-recipe-browser"
ENTITY_PATTERN = re.compile(r"^[a-z0-9_]+\.[a-z0-9_]+$")
CONTAINER_CARD_TYPES = frozenset(
    {"grid", "horizontal-stack", "vertical-stack"}
)


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

    card, title = _find_card(value)
    if card is None:
        raise LovelaceYamlError("No Lovelace card was found in the pasted YAML.")
    if card.get("type") == MEALIE_CARD_TYPE:
        return _convert_mealie_card(card, title)
    return _convert_standard_card(card, title)


def _convert_mealie_card(card: dict[str, Any], title: str | None) -> dict[str, Any]:
    """Convert the custom Mealie browser using its role-specific fields."""

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


def _convert_standard_card(card: dict[str, Any], title: str | None) -> dict[str, Any]:
    """Convert a standard Lovelace card or stack into a native Butler panel."""
    card_type = card.get("type")
    if not isinstance(card_type, str):
        raise LovelaceYamlError("Each Lovelace card must have a type.")
    if card_type.startswith("custom:"):
        raise LovelaceYamlError(
            f"Custom card {card_type!r} cannot be converted automatically."
        )

    entity_ids = list(dict.fromkeys(_entities_from_card(card)))
    actions = _actions_from_card(card)
    if not entity_ids and not actions:
        raise LovelaceYamlError(
            f"The {card_type!r} card has no entities or actions Butler can convert."
        )

    section_type = _section_type(card_type, entity_ids, actions)
    bindings = [
        {
            "kind": "entity",
            "target_id": entity_id,
            **({"role": "weather_source"} if section_type == "weather" else {}),
        }
        for entity_id in entity_ids
    ]
    view_layout = card.get("view_layout")
    return {
        "type": section_type,
        "title": str(title or card.get("name") or card.get("title") or _card_title(card_type))[:80],
        "bindings": bindings,
        "actions": actions,
        "full_page": isinstance(view_layout, dict)
        and view_layout.get("grid-column") == "1 / -1",
    }


def _find_card(value: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """Find the first card in a card, cards wrapper, or dashboard view wrapper."""
    title = value.get("title") if isinstance(value.get("title"), str) else None
    if isinstance(value.get("type"), str):
        return value, title
    cards = value.get("cards")
    if isinstance(cards, list):
        for card in cards:
            if isinstance(card, dict) and isinstance(card.get("type"), str):
                return card, title
    views = value.get("views")
    if isinstance(views, list):
        for view in views:
            if isinstance(view, dict):
                card, view_title = _find_card(view)
                if card is not None:
                    return card, view_title
    return None, title


def _entities_from_card(value: Any) -> list[str]:
    """Collect valid entity IDs from standard card fields and nested cards."""
    found: list[str] = []
    if isinstance(value, list):
        for item in value:
            found.extend(_entities_from_card(item))
        return found
    if not isinstance(value, dict):
        return found
    for key, item in value.items():
        if key in {"entity", "entity_id"} and isinstance(item, str):
            if ENTITY_PATTERN.fullmatch(item):
                found.append(item)
        elif key == "entities" and isinstance(item, list):
            for entity in item:
                entity_id = entity if isinstance(entity, str) else entity.get("entity") if isinstance(entity, dict) else None
                if isinstance(entity_id, str) and ENTITY_PATTERN.fullmatch(entity_id):
                    found.append(entity_id)
                if isinstance(entity, dict):
                    found.extend(_entities_from_card(entity))
        elif key in {"cards", "card"}:
            found.extend(_entities_from_card(item))
    return found


def _actions_from_card(card: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert supported tap actions from a card and cards nested in stacks."""
    cards = card.get("cards")
    if card.get("type") in CONTAINER_CARD_TYPES and isinstance(cards, list):
        return [action for nested in cards if isinstance(nested, dict) for action in _actions_from_card(nested)]

    tap_action = card.get("tap_action")
    if not isinstance(tap_action, dict):
        return []
    action_type = tap_action.get("action")
    entity_id = tap_action.get("entity") or card.get("entity")
    base = {
        "gesture": "tap",
        **({"name": str(card["name"])[:80]} if isinstance(card.get("name"), str) else {}),
        **({"icon": str(card["icon"])[:100]} if isinstance(card.get("icon"), str) else {}),
    }
    if action_type in {"toggle", "more-info"} and isinstance(entity_id, str) and ENTITY_PATTERN.fullmatch(entity_id):
        return [{**base, "type": action_type.replace("-", "_"), "target_id": entity_id}]
    if action_type in {"call-service", "perform-action"}:
        service = tap_action.get("service") or tap_action.get("perform_action")
        if isinstance(service, str) and service.count(".") == 1:
            domain, service_name = service.split(".", 1)
            target = tap_action.get("target")
            target_id = target.get("entity_id") if isinstance(target, dict) else entity_id
            return [{
                **base,
                "type": "call_service",
                "domain": domain,
                "service": service_name,
                **({"target_id": target_id} if isinstance(target_id, str) and ENTITY_PATTERN.fullmatch(target_id) else {}),
                **({"data": tap_action["data"]} if isinstance(tap_action.get("data"), dict) else {}),
            }]
    return []


def _section_type(card_type: str, entity_ids: list[str], actions: list[dict[str, Any]]) -> str:
    """Choose the closest native Butler section for converted card content."""
    domains = {entity_id.split(".", 1)[0] for entity_id in entity_ids}
    if card_type == "weather-forecast" or "weather" in domains:
        return "weather"
    if card_type in {"calendar"} or "calendar" in domains:
        return "events"
    if card_type == "thermostat" or "climate" in domains:
        return "climate"
    if card_type == "media-control" or "media_player" in domains:
        return "media"
    if card_type in {"picture-entity", "picture-glance"} and "camera" in domains:
        return "cameras"
    if domains & {"alarm_control_panel", "lock"}:
        return "security"
    if domains & {"energy", "power"}:
        return "power"
    if actions and not entity_ids:
        return "quick_commands"
    return "entity_controls"


def _card_title(card_type: str) -> str:
    return card_type.replace("-", " ").title()