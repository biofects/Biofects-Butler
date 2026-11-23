"""Versioned dashboard profile contract for Biofects Butler."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
import re
from typing import Any

from .const import DASHBOARD_PROFILE_SCHEMA_VERSION

COMPOSITION_SLOTS = {
    "radial_command_overview": frozenset(
        {
            "overview", "left_menu", "reactor", "right_menu", "media", "events",
            "media_events",
        }
    ),
    "security_camera_board": frozenset(
        {"status", "camera_primary", "camera_grid", "controls", "events"}
    ),
    "focused_control": frozenset(
        {"left_instrument", "core", "right_instrument", "footer"}
    ),
    "full_page": frozenset({"full_page"}),
    "freeform_grid": frozenset(),
}
SECTION_TYPES = frozenset(
    {
        "status_overview",
        "orbital_menu",
        "entity_controls",
        "form",
        "security",
        "climate",
        "cameras",
        "media",
        "events",
        "weather",
        "power",
        "quick_commands",
        "calendar_form",
        "recipe_browser",
        "assistant",
        "heading",
        "text",
        "image",
    }
)
BINDING_KINDS = frozenset({"entity", "device", "area"})
ACTION_TYPES = frozenset(
    {"navigate", "more_info", "toggle", "activate", "call_service"}
)
ACTION_GESTURES = frozenset({"tap", "hold"})
PANEL_HEIGHTS = frozenset({"standard", "full_height"})
POPUP_STYLES = frozenset({"standard", "projector"})
GRAPH_TYPES = frozenset({"auto", "line", "bars", "gauge", "none"})
DISPLAY_MODES = frozenset({"row", "tile"})
CARD_SHAPES = frozenset({"cut", "square", "rounded"})
CALENDAR_INITIAL_VIEWS = frozenset({"dayGridMonth", "listWeek"})
WEATHER_FORECAST_TYPES = frozenset({"daily", "hourly", "twice_daily"})
THEMES = frozenset({"pickle_rick", "futurama_bender", "hal_9000", "butler_neon", "holographic_interface", "violet_hologram", "biofects_hud", "companion", "butler", "simpsons_homer", "simpsons_marge", "simpsons_bart", "simpsons_lisa", "simpsons_maggie"})
THEMES = THEMES | frozenset(
    f"simpsons_{character}__{background}"
    for character in ("homer", "marge", "bart", "lisa", "maggie")
    for background in ("house", "kwik_e_mart")
)

THEMES = THEMES | frozenset(f"futurama_bender__{background}" for background in ("planet_express", "new_new_york", "robot_bar"))
THEMES = THEMES | frozenset(f"pickle_rick__{background}" for background in ("garage", "portal_world", "sewer_lab"))

_SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_ENTITY_ID_PATTERN = re.compile(r"^[a-z0-9_]+\.[a-z0-9_]+$")
_SERVICE_PART_PATTERN = re.compile(r"^[a-z0-9_]+$")
_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")


class ProfileValidationError(ValueError):
    """Raised when a dashboard profile does not satisfy the v1 contract."""


class ProfileMigrationError(ProfileValidationError):
    """Raised when a historical dashboard profile cannot be migrated safely."""


@dataclass(frozen=True, slots=True)
class ProfileBinding:
    """Reference a Home Assistant registry object without copying its state."""

    kind: str
    target_id: str
    entity_ids: tuple[str, ...] = ()
    name: str | None = None
    icon: str | None = None
    display_attributes: tuple[str, ...] = ()
    graph_type: str = "auto"
    role: str | None = None
    group: str | None = None
    display_mode: str = "row"
    card_width: int = 1
    card_height: int = 1
    card_shape: str = "cut"


@dataclass(frozen=True, slots=True)
class ProfileAction:
    """Describe one constrained user interaction."""

    gesture: str
    action_type: str
    target_id: str | None = None
    domain: str | None = None
    service: str | None = None
    data: Mapping[str, Any] | None = None
    name: str | None = None
    icon: str | None = None
    icon_height: int | None = None
    role: str | None = None
    source_id: str | None = None


@dataclass(frozen=True, slots=True)
class ProfileSection:
    """Place one registered Butler section in an approved composition slot."""

    section_id: str
    section_type: str
    slot: str
    title: str | None
    secondary_title: str | None
    panel_height: str
    bindings: tuple[ProfileBinding, ...]
    actions: tuple[ProfileAction, ...]
    initial_view: str = "dayGridMonth"
    forecast_type: str = "daily"
    popup_style: str = "standard"
    popup_width: int = 58
    popup_max_width: int = 720
    popup_max_height: int = 580
    content_scale: int = 100
    projection_color: str = "#16D9FF"
    projection_origin: int = 12
    projection_strength: int = 13
    default_image: str | None = None
    column_span: int = 2
    row_span: int = 1
    grid_column: int = 0
    grid_row: int = 0


@dataclass(frozen=True, slots=True)
class ProfileScreen:
    """Represent one navigable dashboard screen."""

    screen_id: str
    title: str
    composition: str
    sections: tuple[ProfileSection, ...]
    font_scale: int = 100
    command_layout: str = "theme_default"
    grid_columns: int = 4
    grid_row_height: int = 240
    grid_gap: int = 10
    show_header: bool = True


@dataclass(frozen=True, slots=True)
class DashboardProfile:
    """Represent one complete, versioned Butler dashboard profile."""

    schema_version: int
    profile_id: str
    name: str
    default_screen_id: str
    screens: tuple[ProfileScreen, ...]
    theme: str = "butler_neon"
    greeting_weather_entity_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible wire representation."""
        data = {
            "schema_version": self.schema_version,
            "profile_id": self.profile_id,
            "name": self.name,
            "default_screen_id": self.default_screen_id,
            "screens": [_screen_as_dict(screen) for screen in self.screens],
        }
        if self.greeting_weather_entity_id is not None:
            data["greeting_weather_entity_id"] = self.greeting_weather_entity_id
        return data


def _screen_as_dict(screen: ProfileScreen) -> dict[str, Any]:
    data = {
        "screen_id": screen.screen_id,
        "title": screen.title,
        "composition": screen.composition,
        "sections": [_section_as_dict(section) for section in screen.sections],
    }
    for field, default in (("grid_columns", 4), ("grid_row_height", 240), ("grid_gap", 10)):
        if getattr(screen, field) != default:
            data[field] = getattr(screen, field)
    if not screen.show_header:
        data["show_header"] = False
    if screen.command_layout != "theme_default":
        data["command_layout"] = screen.command_layout
    if screen.font_scale != 100:
        data["font_scale"] = screen.font_scale
    return data


def parse_dashboard_profile(payload: Mapping[str, Any]) -> DashboardProfile:
    """Validate and parse a dashboard profile payload atomically."""
    data = migrate_dashboard_profile(payload)
    _keys(
        data,
        {"schema_version", "profile_id", "name", "default_screen_id", "screens"},
        {"theme", "greeting_weather_entity_id"},
        "profile",
    )
    if data["schema_version"] != DASHBOARD_PROFILE_SCHEMA_VERSION:
        raise ProfileValidationError(
            f"profile.schema_version must be {DASHBOARD_PROFILE_SCHEMA_VERSION}"
        )

    screens_value = _list(data["screens"], "profile.screens", minimum=1, maximum=20)
    screens = tuple(
        _parse_screen(value, f"profile.screens[{index}]")
        for index, value in enumerate(screens_value)
    )
    _require_unique((screen.screen_id for screen in screens), "screen IDs")

    default_screen_id = _slug(data["default_screen_id"], "profile.default_screen_id")
    screen_ids = {screen.screen_id for screen in screens}
    if default_screen_id not in screen_ids:
        raise ProfileValidationError("profile.default_screen_id references no screen")

    for screen in screens:
        for section in screen.sections:
            for action in section.actions:
                if action.action_type == "navigate" and action.target_id not in screen_ids:
                    raise ProfileValidationError(
                        f"navigate action references unknown screen {action.target_id!r}"
                    )

    greeting_weather_entity_id = (
        _entity_id(data["greeting_weather_entity_id"], "profile.greeting_weather_entity_id")
        if data.get("greeting_weather_entity_id") is not None
        else None
    )
    if greeting_weather_entity_id is not None and not greeting_weather_entity_id.startswith("weather."):
        raise ProfileValidationError(
            "profile.greeting_weather_entity_id must identify a weather entity"
        )

    return DashboardProfile(
        schema_version=DASHBOARD_PROFILE_SCHEMA_VERSION,
        profile_id=_slug(data["profile_id"], "profile.profile_id"),
        name=_text(data["name"], "profile.name", maximum=100),
        default_screen_id=default_screen_id,
        screens=screens,
        theme=_choice(data.get("theme", "butler_neon"), THEMES, "profile.theme"),
        greeting_weather_entity_id=greeting_weather_entity_id,
    )


def migrate_dashboard_profile(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return a current-version copy of a supported historical profile."""
    source = _mapping(payload, "profile")
    version = source.get("schema_version", source.get("version"))
    if not isinstance(version, int) or isinstance(version, bool):
        raise ProfileMigrationError("profile.schema_version is required")
    if version > DASHBOARD_PROFILE_SCHEMA_VERSION:
        raise ProfileMigrationError(
            f"profile.schema_version {version} is newer than supported version "
            f"{DASHBOARD_PROFILE_SCHEMA_VERSION}"
        )
    if version < 0:
        raise ProfileMigrationError("profile.schema_version cannot be negative")

    migrated: Mapping[str, Any] = deepcopy(dict(source))
    while version < DASHBOARD_PROFILE_SCHEMA_VERSION:
        if version == 0:
            migrated = _migrate_v0_to_v1(migrated)
        else:
            raise ProfileMigrationError(
                f"no migration exists for profile schema version {version}"
            )
        version += 1
    return _ensure_primary_home(migrated)


def _ensure_primary_home(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Make concept Home primary while preserving intentionally removed panels."""
    value = deepcopy(dict(payload))
    screens = value.get("screens")
    if not isinstance(screens, list):
        return value
    home_index = next(
        (
            index
            for index, screen in enumerate(screens)
            if isinstance(screen, Mapping) and screen.get("screen_id") == "home"
        ),
        None,
    )
    existing_home = screens.pop(home_index) if home_index is not None else {}
    if existing_home:
        _parse_screen(existing_home, "profile.screens[home]")
        if existing_home.get("composition") == "freeform_grid":
            screens.insert(0, existing_home)
            value["default_screen_id"] = "home"
            return value
    existing_sections = {
        section.get("slot"): section
        for section in existing_home.get("sections", [])
        if isinstance(section, Mapping) and isinstance(section.get("slot"), str)
    }
    if "reactor" not in existing_sections and "core" in existing_sections:
        existing_sections["reactor"] = existing_sections["core"]
    section_definitions = (
        ("home_overview", "status_overview", "overview"),
        ("home_left_menu", "orbital_menu", "left_menu"),
        ("home_reactor", "entity_controls", "reactor"),
        ("home_right_menu", "orbital_menu", "right_menu"),
        ("home_media", "media", "media"),
        ("home_events", "events", "events"),
    )
    legacy_information = existing_sections.pop("media_events", None)
    if legacy_information:
        media = deepcopy(dict(legacy_information))
        events = deepcopy(dict(legacy_information))
        media["bindings"] = [
            binding for binding in media.get("bindings", [])
            if isinstance(binding, Mapping)
            and str(binding.get("target_id", "")).startswith("media_player.")
        ]
        events["bindings"] = [
            binding for binding in events.get("bindings", [])
            if isinstance(binding, Mapping)
            and str(binding.get("target_id", "")).startswith("calendar.")
        ]
        events["title"] = events.pop("secondary_title", None)
        media.pop("secondary_title", None)
        existing_sections["media"] = media
        existing_sections["events"] = events
    preserve_optional_panels = (
        bool(existing_home)
        and existing_home.get("composition") == "radial_command_overview"
        and legacy_information is None
    )
    home_sections = []
    for section_id, section_type, slot in section_definitions:
        if preserve_optional_panels and slot not in existing_sections:
            continue
        section = deepcopy(dict(existing_sections.get(slot, {})))
        section["section_id"] = section_id
        section.setdefault("type", section_type)
        section["slot"] = slot
        if slot in {"left_menu", "right_menu"}:
            section["actions"] = [
                {**action, "gesture": "tap"}
                for action in section.get("actions", [])
                if isinstance(action, Mapping) and action.get("type") == "navigate"
            ][:5]
        home_sections.append(section)
    screens.insert(
        0,
        {
            "screen_id": "home",
            "title": existing_home.get("title", "Home"),
            "composition": "radial_command_overview",
            "sections": home_sections,
            **({"show_header": existing_home["show_header"]} if "show_header" in existing_home else {}),
            **({"command_layout": existing_home["command_layout"]} if "command_layout" in existing_home else {}),
        },
    )
    value["default_screen_id"] = "home"
    return value


def _migrate_v0_to_v1(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Migrate the pre-release v0 field names to the strict v1 contract."""
    allowed = {"version", "id", "name", "default_screen", "screens"}
    _exact_keys(payload, allowed, "profile v0")
    screens = _list(payload["screens"], "profile v0.screens", minimum=1, maximum=20)
    return {
        "schema_version": 1,
        "profile_id": payload["id"],
        "name": payload["name"],
        "default_screen_id": payload["default_screen"],
        "screens": [
            _migrate_v0_screen(screen, f"profile v0.screens[{index}]")
            for index, screen in enumerate(screens)
        ],
    }


def _migrate_v0_screen(value: Any, path: str) -> Mapping[str, Any]:
    data = _mapping(value, path)
    _exact_keys(data, {"id", "title", "layout", "sections"}, path)
    sections = _list(data["sections"], f"{path}.sections", minimum=1, maximum=20)
    return {
        "screen_id": data["id"],
        "title": data["title"],
        "composition": data["layout"],
        "sections": [
            _migrate_v0_section(section, f"{path}.sections[{index}]")
            for index, section in enumerate(sections)
        ],
    }


def _migrate_v0_section(value: Any, path: str) -> Mapping[str, Any]:
    data = _mapping(value, path)
    required = {"id", "type", "region"}
    optional = {"title", "entities", "actions"}
    _keys(data, required, optional, path)
    migrated: dict[str, Any] = {
        "section_id": data["id"],
        "type": data["type"],
        "slot": data["region"],
    }
    if "title" in data:
        migrated["title"] = data["title"]
    if "entities" in data:
        entities = _list(data["entities"], f"{path}.entities", maximum=100)
        migrated["bindings"] = [
            {"kind": "entity", "target_id": entity_id}
            for entity_id in entities
        ]
    if "actions" in data:
        migrated["actions"] = deepcopy(data["actions"])
    return migrated


def _parse_screen(value: Any, path: str) -> ProfileScreen:
    data = _mapping(value, path)
    required = {"screen_id", "title", "composition", "sections"}
    # Accept legacy card-host settings so existing profiles migrate back to native pages.
    optional = {"ha_dashboard_path", "ha_view_path", "ha_card_scale", "font_scale", "command_layout", "grid_columns", "grid_row_height", "grid_gap", "show_header"}
    _keys(data, required, optional, path)
    if not isinstance(data.get("show_header", True), bool):
        raise ProfileValidationError(f"{path}.show_header must be a boolean")
    composition = _choice(data["composition"], COMPOSITION_SLOTS, f"{path}.composition")
    sections_value = _list(data["sections"], f"{path}.sections", maximum=20)
    sections = tuple(
        _parse_section(section, composition, f"{path}.sections[{index}]")
        for index, section in enumerate(sections_value)
    )
    _require_unique((section.section_id for section in sections), f"{path} section IDs")
    _require_unique((section.slot for section in sections), f"{path} slots")
    return ProfileScreen(
        screen_id=_slug(data["screen_id"], f"{path}.screen_id"),
        title=_text(data["title"], f"{path}.title", maximum=80),
        composition=composition,
        sections=sections,
        show_header=data.get("show_header", True),
        grid_columns=_integer_range(data.get("grid_columns", 4), 1, 12, f"{path}.grid_columns"),
        grid_row_height=_integer_range(data.get("grid_row_height", 240), 80, 400, f"{path}.grid_row_height"),
        grid_gap=_integer_range(data.get("grid_gap", 10), 0, 32, f"{path}.grid_gap"),
        command_layout=_choice(data.get("command_layout", "theme_default"), {"theme_default", "console", "orbital", "observatory", "wings", "companion"}, f"{path}.command_layout"),
        font_scale=_integer_range(data.get("font_scale", 100), 75, 175, f"{path}.font_scale"),
    )


def _parse_section(value: Any, composition: str, path: str) -> ProfileSection:
    data = _mapping(value, path)
    required = {"section_id", "type", "slot"}
    optional = {"title", "secondary_title", "panel_height", "bindings", "actions", "initial_view", "forecast_type", "popup_style", "popup_width", "popup_max_width", "popup_max_height", "content_scale", "projection_color", "projection_origin", "projection_strength", "default_image", "column_span", "row_span", "grid_column", "grid_row"}
    _keys(data, required, optional, path)
    slot = _slug(data["slot"], f"{path}.slot") if composition == "freeform_grid" else _choice(data["slot"], COMPOSITION_SLOTS[composition], f"{path}.slot")
    bindings_value = _list(data.get("bindings", []), f"{path}.bindings", maximum=100)
    actions_value = _list(data.get("actions", []), f"{path}.actions", maximum=20)
    return ProfileSection(
        section_id=_slug(data["section_id"], f"{path}.section_id"),
        section_type=_choice(data["type"], SECTION_TYPES, f"{path}.type"),
        slot=slot,
        title=(
            _text(data["title"], f"{path}.title", maximum=80)
            if data.get("title") is not None
            else None
        ),
        secondary_title=(
            _text(data["secondary_title"], f"{path}.secondary_title", maximum=80)
            if data.get("secondary_title") is not None
            else None
        ),
        panel_height=_choice(
            data.get("panel_height", "standard"), PANEL_HEIGHTS, f"{path}.panel_height"
        ),
        bindings=tuple(
            _parse_binding(binding, f"{path}.bindings[{index}]")
            for index, binding in enumerate(bindings_value)
        ),
        actions=tuple(
            _parse_action(action, f"{path}.actions[{index}]")
            for index, action in enumerate(actions_value)
        ),
        initial_view=_choice(data.get("initial_view", "dayGridMonth"), CALENDAR_INITIAL_VIEWS, f"{path}.initial_view"),
        forecast_type=_choice(data.get("forecast_type", "daily"), WEATHER_FORECAST_TYPES, f"{path}.forecast_type"),
        popup_style=_choice(data.get("popup_style", "standard"), POPUP_STYLES, f"{path}.popup_style"),
        popup_width=_integer_range(data.get("popup_width", 58), 30, 100, f"{path}.popup_width"),
        popup_max_width=_integer_range(data.get("popup_max_width", 720), 320, 1600, f"{path}.popup_max_width"),
        popup_max_height=_integer_range(data.get("popup_max_height", 580), 240, 1200, f"{path}.popup_max_height"),
        content_scale=_integer_range(data.get("content_scale", 100), 60, 140, f"{path}.content_scale"),
        projection_color=_color(data.get("projection_color", "#16D9FF"), f"{path}.projection_color"),
        projection_origin=_integer_range(data.get("projection_origin", 12), 0, 100, f"{path}.projection_origin"),
        projection_strength=_integer_range(data.get("projection_strength", 13), 0, 100, f"{path}.projection_strength"),
        default_image=(
            _text(data["default_image"], f"{path}.default_image", maximum=500)
            if data.get("default_image") is not None
            else None
        ),
        grid_column=_integer_range(data.get("grid_column", 0), 0, 12, f"{path}.grid_column"),
        grid_row=_integer_range(data.get("grid_row", 0), 0, 40, f"{path}.grid_row"),
        column_span=_integer_range(data.get("column_span", 2), 1, 12, f"{path}.column_span"),
        row_span=_integer_range(data.get("row_span", 1), 1, 8, f"{path}.row_span"),
    )


def _parse_binding(value: Any, path: str) -> ProfileBinding:
    data = _mapping(value, path)
    _keys(data, {"kind", "target_id"}, {"entity_ids", "name", "icon", "display_attributes", "graph_type", "role", "group", "display_mode", "card_width", "card_height", "card_shape"}, path)
    kind = _choice(data["kind"], BINDING_KINDS, f"{path}.kind")
    target_id = _text(data["target_id"], f"{path}.target_id", maximum=255)
    if kind == "entity" and not _ENTITY_ID_PATTERN.fullmatch(target_id):
        raise ProfileValidationError(f"{path}.target_id must be an entity ID")
    entity_ids = tuple(
        _entity_id(item, f"{path}.entity_ids[{index}]")
        for index, item in enumerate(
            _list(data.get("entity_ids", []), f"{path}.entity_ids", maximum=20)
        )
    )
    if entity_ids and kind != "entity":
        raise ProfileValidationError(f"{path}.entity_ids is only valid for entity bindings")
    if entity_ids and entity_ids[0] != target_id:
        raise ProfileValidationError(f"{path}.entity_ids must begin with target_id")
    _require_unique(entity_ids, f"{path}.entity_ids")
    name = (
        _text(data["name"], f"{path}.name", maximum=100)
        if data.get("name") is not None
        else None
    )
    icon = (
        _text(data["icon"], f"{path}.icon", maximum=100)
        if data.get("icon") is not None
        else None
    )
    if icon is not None and not icon.startswith("mdi:"):
        raise ProfileValidationError(f"{path}.icon must be an mdi icon")
    display_attributes = tuple(
        _text(item, f"{path}.display_attributes[{index}]", maximum=100)
        for index, item in enumerate(
            _list(data.get("display_attributes", []), f"{path}.display_attributes", maximum=20)
        )
    )
    _require_unique(display_attributes, f"{path}.display_attributes")
    graph_type = _choice(data.get("graph_type", "auto"), GRAPH_TYPES, f"{path}.graph_type")
    role = _slug(data["role"], f"{path}.role") if data.get("role") is not None else None
    group = _text(data["group"], f"{path}.group", maximum=100) if data.get("group") is not None else None
    display_mode = _choice(data.get("display_mode", "row"), DISPLAY_MODES, f"{path}.display_mode")
    return ProfileBinding(
        kind=kind,
        target_id=target_id,
        entity_ids=entity_ids,
        name=name,
        icon=icon,
        display_attributes=display_attributes,
        graph_type=graph_type,
        role=role,
        group=group,
        display_mode=display_mode,
        card_width=_integer_range(data.get("card_width", 1), 1, 4, f"{path}.card_width"),
        card_height=_integer_range(data.get("card_height", 1), 1, 2, f"{path}.card_height"),
        card_shape=_choice(data.get("card_shape", "cut"), CARD_SHAPES, f"{path}.card_shape"),
    )


def _parse_action(value: Any, path: str) -> ProfileAction:
    data = _mapping(value, path)
    required = {"gesture", "type"}
    optional = {"target_id", "source_id", "domain", "service", "data", "name", "icon", "icon_height", "color", "active_color", "role", "active_states"}
    _keys(data, required, optional, path)
    gesture = _choice(data["gesture"], ACTION_GESTURES, f"{path}.gesture")
    action_type = _choice(data["type"], ACTION_TYPES, f"{path}.type")
    target_id = data.get("target_id")
    source_id = data.get("source_id")
    domain = data.get("domain")
    service = data.get("service")
    action_data = data.get("data")
    name = _text(data["name"], f"{path}.name", maximum=100) if data.get("name") is not None else None
    icon = _text(data["icon"], f"{path}.icon", maximum=100) if data.get("icon") is not None else None
    if icon is not None and not icon.startswith("mdi:"):
        raise ProfileValidationError(f"{path}.icon must be an mdi icon")
    icon_height = data.get("icon_height")
    if icon_height is not None and (not isinstance(icon_height, int) or isinstance(icon_height, bool) or not 24 <= icon_height <= 120):
        raise ProfileValidationError(f"{path}.icon_height must be an integer from 24 to 120")
    role = _slug(data["role"], f"{path}.role") if data.get("role") is not None else None

    if action_type == "navigate":
        _require_action_fields(data, path, required={"target_id"})
        target_id = _slug(target_id, f"{path}.target_id")
    elif action_type in {"more_info", "toggle"}:
        _require_action_fields(data, path, required={"target_id"})
        target_id = _entity_id(target_id, f"{path}.target_id")
    elif action_type == "activate":
        _require_action_fields(data, path, required={"target_id"})
        target_id = _entity_id(target_id, f"{path}.target_id")
        if target_id.split(".", 1)[0] not in {"scene", "script", "automation"}:
            raise ProfileValidationError(
                f"{path}.target_id must identify a scene, script, or automation"
            )
    else:
        if target_id == "":
            target_id = None
        _require_action_fields(
            data,
            path,
            required={"domain", "service"},
            allowed={"domain", "service", "target_id", "data"},
        )
        domain = _service_part(domain, f"{path}.domain")
        service = _service_part(service, f"{path}.service")
        if target_id is not None:
            target_id = _entity_id(target_id, f"{path}.target_id")
        if source_id is not None:
            source_id = _entity_id(source_id, f"{path}.source_id")
        if action_data is not None:
            action_data = _json_mapping(action_data, f"{path}.data")

    return ProfileAction(
        gesture=gesture,
        action_type=action_type,
        target_id=target_id,
        domain=domain,
        service=service,
        data=action_data,
        name=name,
        icon=icon,
        icon_height=icon_height,
        role=role,
        source_id=source_id,
    )


def _require_action_fields(
    data: Mapping[str, Any],
    path: str,
    *,
    required: set[str],
    allowed: set[str] | None = None,
) -> None:
    missing = required - data.keys()
    if missing:
        raise ProfileValidationError(f"{path} missing {', '.join(sorted(missing))}")
    irrelevant = (
        {"target_id", "domain", "service", "data"} - (allowed or required)
    ) & data.keys()
    if irrelevant:
        raise ProfileValidationError(
            f"{path} does not allow {', '.join(sorted(irrelevant))} for this action"
        )


def _section_as_dict(section: ProfileSection) -> dict[str, Any]:
    data: dict[str, Any] = {
        "section_id": section.section_id,
        "type": section.section_type,
        "slot": section.slot,
    }
    if section.title is not None:
        data["title"] = section.title
    if section.secondary_title is not None:
        data["secondary_title"] = section.secondary_title
    if section.panel_height != "standard":
        data["panel_height"] = section.panel_height
    if section.bindings:
        data["bindings"] = [
            {
                "kind": binding.kind,
                "target_id": binding.target_id,
                **({"entity_ids": list(binding.entity_ids)} if len(binding.entity_ids) > 1 else {}),
                **({"name": binding.name} if binding.name is not None else {}),
                **({"icon": binding.icon} if binding.icon is not None else {}),
                **({"display_attributes": list(binding.display_attributes)} if binding.display_attributes else {}),
                **({"graph_type": binding.graph_type} if binding.graph_type != "auto" else {}),
                **({"role": binding.role} if binding.role is not None else {}),
                **({"group": binding.group} if binding.group is not None else {}),
                **({"display_mode": binding.display_mode} if binding.display_mode != "row" else {}),
                **({"card_width": binding.card_width} if binding.card_width != 1 else {}),
                **({"card_height": binding.card_height} if binding.card_height != 1 else {}),
                **({"card_shape": binding.card_shape} if binding.card_shape != "cut" else {}),
            }
            for binding in section.bindings
        ]
    if section.actions:
        data["actions"] = [_action_as_dict(action) for action in section.actions]
    if section.default_image is not None:
        data["default_image"] = section.default_image
    if section.grid_column:
        data["grid_column"] = section.grid_column
    if section.grid_row:
        data["grid_row"] = section.grid_row
    if section.column_span != 2:
        data["column_span"] = section.column_span
    if section.row_span != 1:
        data["row_span"] = section.row_span
    if section.initial_view != "dayGridMonth":
        data["initial_view"] = section.initial_view
    if section.forecast_type != "daily":
        data["forecast_type"] = section.forecast_type
    for key, value, default in (
        ("popup_style", section.popup_style, "standard"),
        ("popup_width", section.popup_width, 58),
        ("popup_max_width", section.popup_max_width, 720),
        ("popup_max_height", section.popup_max_height, 580),
        ("content_scale", section.content_scale, 100),
        ("projection_color", section.projection_color, "#16D9FF"),
        ("projection_origin", section.projection_origin, 12),
        ("projection_strength", section.projection_strength, 13),
    ):
        if value != default:
            data[key] = value
    return data


def _action_as_dict(action: ProfileAction) -> dict[str, Any]:
    data: dict[str, Any] = {"gesture": action.gesture, "type": action.action_type}
    for key, value in (
        ("target_id", action.target_id),
        ("source_id", action.source_id),
        ("domain", action.domain),
        ("service", action.service),
        ("data", action.data),
        ("name", action.name),
        ("icon", action.icon),
        ("icon_height", action.icon_height),
        ("role", action.role),
    ):
        if value is not None:
            data[key] = value
    return data


def _color(value: Any, path: str) -> str:
    color = _text(value, path, maximum=7)
    if not _COLOR_PATTERN.fullmatch(color):
        raise ProfileValidationError(f"{path} must be a #RRGGBB color")
    return color.upper()


def _integer_range(value: Any, minimum: int, maximum: int, path: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
        raise ProfileValidationError(f"{path} must be an integer from {minimum} to {maximum}")
    return value


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ProfileValidationError(f"{path} must be an object")
    return value


def _json_mapping(value: Any, path: str) -> Mapping[str, Any]:
    data = _mapping(value, path)
    _validate_json(data, path)
    return data


def _validate_json(value: Any, path: str) -> None:
    if value is None or isinstance(value, (str, int, float, bool)):
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json(item, f"{path}[{index}]")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ProfileValidationError(f"{path} keys must be strings")
            _validate_json(item, f"{path}.{key}")
        return
    raise ProfileValidationError(f"{path} must contain JSON-compatible values")


def _list(
    value: Any, path: str, *, minimum: int = 0, maximum: int
) -> list[Any]:
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        raise ProfileValidationError(
            f"{path} must be a list with {minimum} to {maximum} items"
        )
    return value


def _keys(
    data: Mapping[str, Any], required: set[str], optional: set[str], path: str
) -> None:
    missing = required - data.keys()
    unknown = data.keys() - required - optional
    if missing:
        raise ProfileValidationError(f"{path} missing {', '.join(sorted(missing))}")
    if unknown:
        raise ProfileValidationError(f"{path} has unknown {', '.join(sorted(unknown))}")


def _exact_keys(data: Mapping[str, Any], expected: set[str], path: str) -> None:
    _keys(data, expected, set(), path)


def _text(value: Any, path: str, *, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
        raise ProfileValidationError(f"{path} must be 1 to {maximum} characters")
    return value.strip()


def _slug(value: Any, path: str) -> str:
    text = _text(value, path, maximum=64)
    if not _SLUG_PATTERN.fullmatch(text):
        raise ProfileValidationError(f"{path} must be a lowercase slug")
    return text


def _entity_id(value: Any, path: str) -> str:
    text = _text(value, path, maximum=255)
    if not _ENTITY_ID_PATTERN.fullmatch(text):
        raise ProfileValidationError(f"{path} must be an entity ID")
    return text


def _service_part(value: Any, path: str) -> str:
    text = _text(value, path, maximum=64)
    if not _SERVICE_PART_PATTERN.fullmatch(text):
        raise ProfileValidationError(f"{path} must be a service identifier")
    return text


def _choice(value: Any, choices: Mapping[str, Any] | frozenset[str], path: str) -> str:
    if not isinstance(value, str) or value not in choices:
        raise ProfileValidationError(
            f"{path} must be one of {', '.join(sorted(choices))}"
        )
    return value


def _require_unique(values: Any, description: str) -> None:
    values_list = list(values)
    if len(values_list) != len(set(values_list)):
        raise ProfileValidationError(f"duplicate {description}")
