"""Tests for dashboard profile WebSocket commands and subscriptions."""

from __future__ import annotations

import asyncio
import importlib
import sys
from types import SimpleNamespace


def load_modules(websocket_modules):
    """Import fresh profile and WebSocket modules against HA stubs."""
    sys.modules.pop("custom_components.biofects_butler.websocket_api", None)
    profiles = importlib.import_module("custom_components.biofects_butler.profiles")
    websocket = importlib.import_module("custom_components.biofects_butler.websocket_api")
    return profiles, websocket


class FakeProfileStore:
    """Exercise command behavior independently of HA disk storage."""

    def __init__(self, profile, display=None) -> None:
        self.profiles = (profile,)
        self.displays = () if display is None else (display,)
        self.assignments = {}
        self.display_themes = {}
        self.profile = profile
        self.display = display

    async def async_upsert(self, payload):
        return self.profile

    async def async_delete(self, profile_id):
        return None

    async def async_register_display(self, payload):
        return self.display

    async def async_delete_display(self, display_id):
        self.displays = tuple(
            display for display in self.displays if display.display_id != display_id
        )
        self.assignments.pop(display_id, None)
        self.display_themes.pop(display_id, None)

    async def async_assign(self, display_id, profile_id, theme=None):
        self.assignments[display_id] = profile_id
        self.display_themes[display_id] = theme or "butler_neon"

    def theme_for_display(self, display_id):
        return self.display_themes.get(display_id, "butler_neon")

    def for_display(self, display_id):
        return self.profile


def profile_payload() -> dict:
    """Return a compact valid profile payload."""
    return {
        "schema_version": 1,
        "profile_id": "default",
        "name": "Default HUD",
        "default_screen_id": "home",
        "screens": [
            {
                "screen_id": "home",
                "title": "Home",
                "composition": "focused_control",
                "sections": [
                    {
                        "section_id": "core",
                        "type": "status_overview",
                        "slot": "core",
                    }
                ],
            }
        ],
    }


def command_context(websocket_modules, *, include_display: bool = True):
    """Build one command context with captured output and dispatcher state."""
    profiles, websocket = load_modules(websocket_modules)
    profile = profiles.parse_dashboard_profile(profile_payload())
    display = (
        SimpleNamespace(
            display_id="display-123",
            as_dict=lambda: {
                "display_id": "display-123",
                "name": "Kitchen",
                "model": "SM-T733",
                "viewport_class": "expanded",
                "renderer_schema_version": 1,
            },
        )
        if include_display
        else None
    )
    store = FakeProfileStore(profile, display)
    hass = SimpleNamespace(
        data={websocket.DOMAIN: {websocket.DATA_PROFILE_STORE: store}}, dispatcher={}
    )
    results = []
    errors = []
    messages = []
    connection = SimpleNamespace(
        subscriptions={},
        send_result=lambda message_id, data=None: results.append((message_id, data)),
        send_error=lambda *args: errors.append(args),
        send_message=messages.append,
    )
    return websocket, store, hass, connection, results, errors, messages


def test_get_profiles_returns_canonical_snapshot(websocket_modules) -> None:
    """Read command returns profiles, displays, assignments, and version."""
    websocket, _, hass, connection, results, _, _ = command_context(
        websocket_modules
    )

    websocket.websocket_get_dashboard_profiles(hass, connection, {"id": 10})

    assert results[0][1]["version"] == 1
    assert results[0][1]["profiles"][0]["profile_id"] == "default"
    assert results[0][1]["displays"][0]["display_id"] == "display-123"
    assert results[0][1]["display_themes"] == {}


def test_save_delete_register_and_assign(websocket_modules) -> None:
    """Mutations return stable results and publish one update each."""
    websocket, store, hass, connection, results, errors, _ = command_context(
        websocket_modules
    )
    notifications = []
    hass.dispatcher[websocket.SIGNAL_PROFILES_UPDATED] = [
        lambda: notifications.append(True)
    ]

    asyncio.run(
        websocket.websocket_save_dashboard_profile(
            hass, connection, {"id": 11, "profile": profile_payload()}
        )
    )
    asyncio.run(
        websocket.websocket_register_display(
            hass, connection, {"id": 12, "display": {}}
        )
    )
    asyncio.run(
        websocket.websocket_assign_dashboard_profile(
            hass,
            connection,
            {
                "id": 13,
                "display_id": "display-123",
                "profile_id": "default",
                "theme": "holographic_interface",
            },
        )
    )
    asyncio.run(
        websocket.websocket_delete_dashboard_profile(
            hass, connection, {"id": 14, "profile_id": "other"}
        )
    )
    asyncio.run(
        websocket.websocket_delete_display(
            hass, connection, {"id": 15, "display_id": "display-123"}
        )
    )

    assert errors == []
    assert [message_id for message_id, _ in results] == [11, 12, 13, 14, 15]
    assert store.assignments == {}
    assert store.display_themes == {}
    assert notifications == [True, True, True, True, True]


def test_validation_error_does_not_publish(websocket_modules) -> None:
    """A rejected profile returns an error and sends no change event."""
    profiles, websocket = load_modules(websocket_modules)
    _, store, hass, connection, results, errors, _ = command_context(
        websocket_modules
    )

    async def reject(payload):
        raise profiles.ProfileValidationError("invalid profile")

    store.async_upsert = reject
    notifications = []
    hass.dispatcher[websocket.SIGNAL_PROFILES_UPDATED] = [
        lambda: notifications.append(True)
    ]

    asyncio.run(
        websocket.websocket_save_dashboard_profile(
            hass, connection, {"id": 15, "profile": {}}
        )
    )

    assert results == []
    assert errors == [(15, "invalid_format", "invalid profile")]
    assert notifications == []


def test_subscription_sends_snapshot_and_unsubscribes(websocket_modules) -> None:
    """Subscribers receive initial and changed atomic snapshots."""
    websocket, _, hass, connection, results, _, messages = command_context(
        websocket_modules
    )

    websocket.websocket_subscribe_dashboard_profiles(
        hass, connection, {"id": 16}
    )
    hass.dispatcher[websocket.SIGNAL_PROFILES_UPDATED][0]()

    assert results == [(16, None)]
    assert len(messages) == 2
    assert messages[0]["event"]["profiles"][0]["profile_id"] == "default"
    connection.subscriptions[16]()
    assert hass.dispatcher[websocket.SIGNAL_PROFILES_UPDATED] == []