"""Tests for Butler integration setup and unload."""

from __future__ import annotations

import asyncio
import importlib
import sys
from types import ModuleType, SimpleNamespace

import pytest

from conftest import install_status_stubs


@pytest.fixture
def integration_module(monkeypatch: pytest.MonkeyPatch):
    """Import integration setup with minimal Home Assistant types."""
    for name in list(sys.modules):
        if name.startswith("custom_components.biofects_butler"):
            sys.modules.pop(name)

    homeassistant = ModuleType("homeassistant")
    components = ModuleType("homeassistant.components")
    panel_custom = ModuleType("homeassistant.components.panel_custom")

    async def async_register_panel(hass, **kwargs) -> None:
        hass.panels.append(kwargs)

    panel_custom.async_register_panel = async_register_panel
    websocket_api = ModuleType("homeassistant.components.websocket_api")
    websocket_api.ActiveConnection = object
    websocket_api.websocket_command = lambda schema: lambda function: function
    websocket_api.async_response = lambda function: function
    websocket_api.event_message = lambda subscription_id, event: {
        "id": subscription_id,
        "event": event,
    }
    websocket_api.ERR_NOT_FOUND = "not_found"
    websocket_api.async_register_command = lambda hass, command: hass.commands.append(command)
    components.panel_custom = panel_custom
    components.websocket_api = websocket_api
    http = ModuleType("homeassistant.components.http")

    class StaticPathConfig:
        def __init__(self, url_path, path, cache_headers=True) -> None:
            self.url_path = url_path
            self.path = path
            self.cache_headers = cache_headers

    http.StaticPathConfig = StaticPathConfig
    config_entries = ModuleType("homeassistant.config_entries")
    config_entries.ConfigEntry = object
    core = ModuleType("homeassistant.core")
    core.HomeAssistant = object
    core.callback = lambda function: function

    monkeypatch.setitem(sys.modules, "homeassistant", homeassistant)
    monkeypatch.setitem(sys.modules, "homeassistant.components", components)
    monkeypatch.setitem(sys.modules, "homeassistant.components.panel_custom", panel_custom)
    monkeypatch.setitem(sys.modules, "homeassistant.components.http", http)
    monkeypatch.setitem(sys.modules, "homeassistant.components.websocket_api", websocket_api)
    monkeypatch.setitem(sys.modules, "homeassistant.config_entries", config_entries)
    monkeypatch.setitem(sys.modules, "homeassistant.core", core)
    install_status_stubs(monkeypatch, components)
    storage = ModuleType("homeassistant.helpers.storage")

    class Store:
        def __init__(self, hass, version, key) -> None:
            pass

        async def async_load(self):
            return None

        async def async_save(self, data) -> None:
            pass

    storage.Store = Store
    monkeypatch.setitem(sys.modules, "homeassistant.helpers.storage", storage)
    return importlib.import_module("custom_components.biofects_butler")


def test_setup_registers_websocket_command(integration_module) -> None:
    """YAML-level setup registers the Butler command set once."""
    class Http:
        async def async_register_static_paths(self, paths) -> None:
            hass.static_paths.extend(paths)

    hass = SimpleNamespace(
        commands=[], data={}, http=Http(), panels=[], static_paths=[]
    )

    assert asyncio.run(integration_module.async_setup(hass, {})) is True
    assert [command.__name__ for command in hass.commands] == [
        "websocket_status",
        "websocket_subscribe_status",
        "websocket_get_setup_options",
        "websocket_get_dashboard_profiles",
        "websocket_save_dashboard_profile",
        "websocket_delete_dashboard_profile",
        "websocket_register_display",
            "websocket_delete_display",
        "websocket_assign_dashboard_profile",
        "websocket_subscribe_dashboard_profiles",
    ]
    assert hass.static_paths[0].url_path == "/biofects_butler_static"
    assert hass.static_paths[0].cache_headers is False
    assert hass.panels == [
        {
            "frontend_url_path": "biofects-butler",
            "webcomponent_name": "biofects-butler-panel",
            "sidebar_title": "Butler Dashboards",
            "sidebar_icon": "mdi:monitor-dashboard",
                "module_url": "/biofects_butler_static/biofects-butler-panel.js?v=55",
            "require_admin": True,
        }
    ]


def test_entry_setup_and_unload_platforms(integration_module) -> None:
    """Config entry lifecycle forwards and unloads the sensor platform."""
    calls: list[tuple[str, list[str]]] = []

    class ConfigEntries:
        async def async_forward_entry_setups(self, entry, platforms) -> None:
            calls.append(("setup", platforms))

        async def async_unload_platforms(self, entry, platforms) -> bool:
            calls.append(("unload", platforms))
            return True

    hass = SimpleNamespace(config_entries=ConfigEntries())
    entry = SimpleNamespace(entry_id="test")

    assert asyncio.run(integration_module.async_setup_entry(hass, entry)) is True
    assert asyncio.run(integration_module.async_unload_entry(hass, entry)) is True
    assert calls == [
        ("setup", ["binary_sensor"]),
        ("unload", ["binary_sensor"]),
    ]