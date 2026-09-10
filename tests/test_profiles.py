"""Tests for the versioned dashboard profile contract."""

from __future__ import annotations

import importlib

import pytest

pytestmark = pytest.mark.usefixtures("websocket_modules")


def valid_profile() -> dict:
    """Return a representative v1 dashboard profile."""
    return {
        "schema_version": 1,
        "profile_id": "kitchen_tablet",
        "name": "Kitchen Tablet",
        "default_screen_id": "home",
        "screens": [
            {
                "screen_id": "home",
                "title": "Home",
                "composition": "radial_command_overview",
                "sections": [
                    {
                        "section_id": "home_overview",
                        "type": "status_overview",
                        "slot": "overview",
                        "title": "Indoor Climate",
                        "bindings": [
                            {
                                "kind": "entity",
                                "target_id": "sensor.kitchen_temperature",
                                "name": "Kitchen Comfort",
                                "icon": "mdi:thermometer-lines",
                                "display_attributes": ["state", "last_updated"],
                            }
                        ],
                    },
                    {
                        "section_id": "home_left_menu",
                        "type": "orbital_menu",
                        "slot": "left_menu",
                        "actions": [
                            {
                                "gesture": "tap",
                                "type": "navigate",
                                "target_id": "climate",
                            },
                        ],
                    },
                    {
                        "section_id": "home_reactor",
                        "type": "entity_controls",
                        "slot": "reactor",
                    },
                    {
                        "section_id": "home_right_menu",
                        "type": "orbital_menu",
                        "slot": "right_menu",
                    },
                    {"section_id": "home_media", "type": "media", "slot": "media"},
                    {"section_id": "home_events", "type": "events", "slot": "events"},
                ],
            },
            {
                "screen_id": "climate",
                "title": "Climate",
                "composition": "focused_control",
                "sections": [
                    {
                        "section_id": "climate_core",
                        "type": "climate",
                        "slot": "core",
                        "bindings": [
                            {"kind": "entity", "target_id": "climate.downstairs"}
                        ],
                        "actions": [
                            {
                                "gesture": "tap",
                                "type": "call_service",
                                "target_id": "climate.downstairs",
                                "domain": "climate",
                                "service": "set_temperature",
                                "data": {"temperature": 72},
                            }
                        ],
                    }
                ],
            },
        ],
    }


def legacy_v0_profile() -> dict:
    """Return the documented pre-release profile shape."""
    return {
        "version": 0,
        "id": "kitchen_tablet",
        "name": "Kitchen Tablet",
        "default_screen": "home",
        "screens": [
            {
                "id": "home",
                "title": "Home",
                "layout": "focused_control",
                "sections": [
                    {
                        "id": "climate_core",
                        "type": "climate",
                        "region": "core",
                        "entities": ["climate.downstairs"],
                    }
                ],
            }
        ],
    }


def load_profiles_module():
    """Import the contract without requiring a Home Assistant runtime."""
    return importlib.import_module("custom_components.biofects_butler.profiles")


def test_profile_round_trip() -> None:
    """Parse a complete profile into immutable typed models and back to JSON."""
    module = load_profiles_module()

    profile = module.parse_dashboard_profile(valid_profile())

    assert profile.profile_id == "kitchen_tablet"
    assert profile.screens[1].sections[0].actions[0].service == "set_temperature"
    assert profile.as_dict() == valid_profile()


def test_calendar_list_week_round_trips() -> None:
    """Calendar presentation remains display metadata while HA owns event data."""
    module = load_profiles_module()
    payload = valid_profile()
    events = payload["screens"][0]["sections"][-1]
    events["initial_view"] = "listWeek"
    events["bindings"] = [{"kind": "entity", "target_id": "calendar.tfam_calendar"}]

    profile = module.parse_dashboard_profile(payload)

    parsed_events = profile.screens[0].sections[-1]
    assert parsed_events.initial_view == "listWeek"
    assert profile.as_dict() == payload


def test_multi_entity_card_round_trips() -> None:
    """One card can group related entities while retaining a primary target."""
    module = load_profiles_module()
    payload = valid_profile()
    binding = payload["screens"][0]["sections"][0]["bindings"][0]
    binding["entity_ids"] = [
        "sensor.kitchen_temperature",
        "sensor.kitchen_humidity",
        "binary_sensor.kitchen_window",
    ]

    profile = module.parse_dashboard_profile(payload)

    parsed = profile.screens[0].sections[0].bindings[0]
    assert parsed.entity_ids == tuple(binding["entity_ids"])
    assert profile.as_dict() == payload


def test_legacy_holographic_theme_is_accepted_but_not_serialized() -> None:
    """A legacy profile theme remains available for display migration only."""
    module = load_profiles_module()
    payload = valid_profile()
    payload["theme"] = "holographic_interface"

    profile = module.parse_dashboard_profile(payload)

    assert profile.theme == "holographic_interface"
    assert "theme" not in profile.as_dict()


def test_robot_butler_theme_is_accepted() -> None:
    """The animated robot presentation can be assigned as a display theme."""
    module = load_profiles_module()
    payload = valid_profile()
    payload["theme"] = "robot_butler"

    profile = module.parse_dashboard_profile(payload)

    assert profile.theme == "robot_butler"


def test_migrates_v0_without_mutating_source() -> None:
    """Known historical names migrate to canonical v1 before validation."""
    module = load_profiles_module()
    payload = legacy_v0_profile()
    original = legacy_v0_profile()

    profile = module.parse_dashboard_profile(payload)

    assert payload == original
    assert profile.schema_version == 1
    assert profile.default_screen_id == "home"
    assert profile.screens[0].sections[2].slot == "reactor"
    assert profile.screens[0].sections[2].bindings[0].target_id == (
        "climate.downstairs"
    )


def test_binding_icon_override_round_trips() -> None:
    """Dashboard-specific MDI icons survive strict parsing and serialization."""
    module = load_profiles_module()

    profile = module.parse_dashboard_profile(valid_profile())

    binding = profile.screens[0].sections[0].bindings[0]
    assert binding.name == "Kitchen Comfort"
    assert binding.icon == "mdi:thermometer-lines"
    assert binding.display_attributes == ("state", "last_updated")
    assert profile.as_dict()["screens"][0]["sections"][0]["bindings"][0]["icon"] == "mdi:thermometer-lines"
    assert profile.as_dict()["screens"][0]["sections"][0]["title"] == "Indoor Climate"


def test_binding_graph_type_round_trips() -> None:
    """Native graph presentation can be selected per entity card."""
    module = load_profiles_module()
    payload = valid_profile()
    payload["screens"][0]["sections"][0]["bindings"][0]["graph_type"] = "gauge"
    payload["screens"][0]["sections"][0]["bindings"][0]["role"] = "weather_source"

    profile = module.parse_dashboard_profile(payload)

    assert profile.screens[0].sections[0].bindings[0].graph_type == "gauge"
    assert profile.screens[0].sections[0].bindings[0].role == "weather_source"
    assert profile.as_dict()["screens"][0]["sections"][0]["bindings"][0]["graph_type"] == "gauge"
    assert profile.as_dict()["screens"][0]["sections"][0]["bindings"][0]["role"] == "weather_source"


def test_weather_forecast_type_round_trips() -> None:
    """Weather sections retain a supported forecast mode."""
    module = load_profiles_module()
    payload = valid_profile()
    section = payload["screens"][0]["sections"][0]
    section["type"] = "weather"
    section["forecast_type"] = "hourly"

    profile = module.parse_dashboard_profile(payload)

    assert profile.screens[0].sections[0].forecast_type == "hourly"
    assert profile.as_dict()["screens"][0]["sections"][0]["forecast_type"] == "hourly"


def test_weather_forecast_type_rejects_unknown_value() -> None:
    """Weather forecast modes must match Home Assistant's API values."""
    module = load_profiles_module()
    payload = valid_profile()
    payload["screens"][0]["sections"][0]["forecast_type"] = "weekly"

    with pytest.raises(module.ProfileValidationError, match="forecast_type"):
        module.parse_dashboard_profile(payload)


def test_quick_command_button_round_trips() -> None:
    """Custom command appearance and service calls remain profile-owned."""
    module = load_profiles_module()
    payload = valid_profile()
    payload["screens"][0]["sections"][0]["actions"] = [{
        "gesture": "tap",
        "type": "call_service",
        "domain": "script",
        "service": "dinner_time",
        "name": "Dinner Time",
        "icon": "mdi:food",
        "icon_height": 70,
        "color": "#29B6F6",
        "active_color": "#66FF99",
        "role": "form_submit",
        "active_states": ["on", "playing"],
        "data": {"announce": True},
    }]

    profile = module.parse_dashboard_profile(payload)
    action = profile.screens[0].sections[0].actions[0]

    assert action.name == "Dinner Time"
    assert action.icon == "mdi:food"
    assert action.icon_height == 70
    assert action.role == "form_submit"
    serialized_action = profile.as_dict()["screens"][0]["sections"][0]["actions"][0]
    assert "color" not in serialized_action
    assert "active_color" not in serialized_action
    assert "active_states" not in serialized_action
    assert action.data == {"announce": True}


def test_calendar_form_section_round_trips() -> None:
    """Calendar forms are explicit profile-owned panels."""
    module = load_profiles_module()
    payload = valid_profile()
    payload["screens"][1]["sections"][0]["type"] = "calendar_form"
    payload["screens"][1]["sections"][0].update({
        "popup_style": "projector", "popup_width": 64, "popup_max_width": 800,
        "popup_max_height": 640, "content_scale": 90,
        "projection_color": "#00CCFF", "projection_origin": 20,
        "projection_strength": 25,
    })

    profile = module.parse_dashboard_profile(payload)

    assert profile.screens[1].sections[0].section_type == "calendar_form"
    assert profile.screens[1].sections[0].popup_style == "projector"
    assert profile.screens[1].sections[0].projection_strength == 25


def test_quick_command_allows_blank_optional_target() -> None:
    """An untouched optional target field is treated as absent."""
    module = load_profiles_module()
    payload = valid_profile()
    payload["screens"][0]["sections"][0]["actions"] = [{
        "gesture": "tap",
        "type": "call_service",
        "domain": "script",
        "service": "dinner_time",
        "target_id": "",
        "name": "Dinner Time",
    }]

    action = module.parse_dashboard_profile(payload).screens[0].sections[0].actions[0]

    assert action.target_id is None


def test_home_panel_preserves_quick_commands_type() -> None:
    """Home normalization does not discard a user-selected panel renderer."""
    module = load_profiles_module()
    payload = valid_profile()
    media = next(section for section in payload["screens"][0]["sections"] if section["slot"] == "media")
    media["type"] = "quick_commands"

    saved = module.parse_dashboard_profile(payload).as_dict()

    saved_media = next(section for section in saved["screens"][0]["sections"] if section["slot"] == "media")
    assert saved_media["type"] == "quick_commands"


def test_media_event_headings_round_trip() -> None:
    """Home media and event panels retain independent headings."""
    module = load_profiles_module()
    payload = valid_profile()
    media = payload["screens"][0]["sections"][-2]
    events = payload["screens"][0]["sections"][-1]
    media["title"] = "Now Playing"
    events["title"] = "Family Calendar"

    saved = module.parse_dashboard_profile(payload).as_dict()["screens"][0]["sections"]

    assert saved[-2]["title"] == "Now Playing"
    assert saved[-1]["title"] == "Family Calendar"


def test_panel_height_and_removed_panels_round_trip() -> None:
    """Panel presentation and intentional removal survive normalization."""
    module = load_profiles_module()
    payload = valid_profile()
    home = payload["screens"][0]
    home["sections"] = [home["sections"][0]]
    home["sections"][0]["panel_height"] = "full_height"

    saved = module.parse_dashboard_profile(payload).as_dict()["screens"][0]["sections"]

    assert len(saved) == 1
    assert saved[0]["slot"] == "overview"
    assert saved[0]["panel_height"] == "full_height"


def test_empty_dashboard_round_trips() -> None:
    """Removing every panel leaves an editable empty dashboard."""
    module = load_profiles_module()
    payload = valid_profile()
    payload["screens"][0]["sections"] = []

    saved = module.parse_dashboard_profile(payload).as_dict()

    assert saved["screens"][0]["sections"] == []


def test_adds_primary_home_to_existing_profile() -> None:
    """Older profiles gain an editable Home overview without losing pages."""
    module = load_profiles_module()
    payload = valid_profile()
    payload["screens"] = payload["screens"][1:]
    payload["default_screen_id"] = "climate"

    profile = module.parse_dashboard_profile(payload)

    assert profile.default_screen_id == "home"
    assert [screen.screen_id for screen in profile.screens] == ["home", "climate"]
    assert profile.screens[0].composition == "radial_command_overview"
    assert len(profile.screens[0].sections) == 6


def test_normalizes_existing_home_without_losing_card_data() -> None:
    """A valid custom Home becomes fixed while its editable card data survives."""
    module = load_profiles_module()
    payload = valid_profile()
    payload["screens"][0] = {
        "screen_id": "home",
        "title": "My Dashboard",
        "composition": "focused_control",
        "sections": [
            {
                "section_id": "custom_core",
                "type": "climate",
                "slot": "core",
                "bindings": [
                    {
                        "kind": "entity",
                        "target_id": "climate.downstairs",
                        "icon": "mdi:hvac",
                        "display_attributes": ["climate_current"],
                    }
                ],
                "actions": [
                    {
                        "gesture": "tap",
                        "type": "activate",
                        "target_id": "script.good_night",
                    }
                ],
            }
        ],
    }

    profile = module.parse_dashboard_profile(payload)

    home = profile.screens[0]
    reactor = home.sections[2]
    assert home.title == "Home"
    assert home.composition == "radial_command_overview"
    assert [section.slot for section in home.sections] == [
        "overview", "left_menu", "reactor", "right_menu", "media", "events"
    ]
    assert reactor.bindings[0].icon == "mdi:hvac"
    assert reactor.bindings[0].display_attributes == ("climate_current",)
    assert reactor.actions[0].target_id == "script.good_night"


def test_normalizes_home_sidebar_blueprint_actions() -> None:
    """Home sidebars retain only five ordered tap-navigation entries."""
    module = load_profiles_module()
    payload = valid_profile()
    left_menu = payload["screens"][0]["sections"][1]
    left_menu["actions"] = [
        {"gesture": "hold", "type": "navigate", "target_id": "climate"}
        for _ in range(6)
    ] + [
        {"gesture": "tap", "type": "activate", "target_id": "script.good_night"}
    ]

    profile = module.parse_dashboard_profile(payload)

    actions = profile.screens[0].sections[1].actions
    assert len(actions) == 5
    assert all(action.action_type == "navigate" for action in actions)
    assert all(action.gesture == "tap" for action in actions)


def test_legacy_home_assistant_card_settings_are_discarded() -> None:
    """Profiles saved during card-host support migrate back to native pages."""
    module = load_profiles_module()
    payload = valid_profile()
    payload["screens"][1].update(
        ha_dashboard_path="lovelace",
        ha_view_path="climate",
        ha_card_scale=85,
    )

    profile = module.parse_dashboard_profile(payload)

    saved_screen = profile.as_dict()["screens"][1]
    assert saved_screen["screen_id"] == "climate"
    assert "ha_dashboard_path" not in saved_screen
    assert "ha_view_path" not in saved_screen
    assert "ha_card_scale" not in saved_screen


def test_rejects_newer_and_unversioned_profiles() -> None:
    """Unknown future or ambiguous profiles never replace current data."""
    module = load_profiles_module()
    future = valid_profile()
    future["schema_version"] = 2
    unversioned = valid_profile()
    del unversioned["schema_version"]

    with pytest.raises(module.ProfileMigrationError, match="newer than supported"):
        module.parse_dashboard_profile(future)
    with pytest.raises(module.ProfileMigrationError, match="version is required"):
        module.parse_dashboard_profile(unversioned)


def test_migrated_profile_still_requires_strict_v1_content() -> None:
    """Migration translates known fields but cannot bypass v1 validation."""
    module = load_profiles_module()
    payload = legacy_v0_profile()
    payload["screens"][0]["sections"][0]["type"] = "custom_html"

    with pytest.raises(module.ProfileValidationError, match="type"):
        module.parse_dashboard_profile(payload)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda profile: profile.update(schema_version=2), "schema_version"),
        (lambda profile: profile.update(injected_css="cyan"), "unknown"),
        (
            lambda profile: profile["screens"][0].update(composition="freeform"),
            "composition",
        ),
        (
            lambda profile: profile["screens"][0]["sections"][0].update(
                slot="absolute_pixels"
            ),
            "slot",
        ),
        (
            lambda profile: profile["screens"][0]["sections"][0].update(
                type="custom_html"
            ),
            "type",
        ),
    ],
)
def test_rejects_unsupported_contract(mutate, message: str) -> None:
    """Reject version, styling, composition, slot, and renderer injection."""
    module = load_profiles_module()
    payload = valid_profile()
    mutate(payload)

    with pytest.raises(module.ProfileValidationError, match=message):
        module.parse_dashboard_profile(payload)


def test_rejects_duplicate_slots() -> None:
    """A composition slot can host only one section."""
    module = load_profiles_module()
    payload = valid_profile()
    payload["screens"][0]["sections"][1]["slot"] = "overview"

    with pytest.raises(module.ProfileValidationError, match="duplicate.*slots"):
        module.parse_dashboard_profile(payload)


def test_rejects_unknown_navigation_target() -> None:
    """Navigation actions must resolve within the same atomic profile."""
    module = load_profiles_module()
    payload = valid_profile()
    payload["screens"][0]["sections"][1]["actions"][0]["target_id"] = "missing"

    with pytest.raises(module.ProfileValidationError, match="unknown screen"):
        module.parse_dashboard_profile(payload)


def test_rejects_activation_for_unapproved_domain() -> None:
    """Activate actions are limited to scenes, scripts, and automations."""
    module = load_profiles_module()
    payload = valid_profile()
    payload["screens"][0]["sections"][1]["actions"][0] = {
        "gesture": "tap",
        "type": "activate",
        "target_id": "lock.front_door",
    }

    with pytest.raises(module.ProfileValidationError, match="scene, script"):
        module.parse_dashboard_profile(payload)


def test_rejects_non_json_service_data() -> None:
    """Service payloads cannot contain executable or process-local objects."""
    module = load_profiles_module()
    payload = valid_profile()
    payload["screens"][1]["sections"][0]["actions"][0]["data"] = {
        "callback": object()
    }

    with pytest.raises(module.ProfileValidationError, match="JSON-compatible"):
        module.parse_dashboard_profile(payload)