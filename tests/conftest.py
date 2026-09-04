"""Test support for Biofects Butler without a full HA runtime."""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

COMPONENT_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(COMPONENT_ROOT))


def install_status_stubs(
    monkeypatch: pytest.MonkeyPatch, components: ModuleType
) -> None:
    """Install framework modules imported by live status discovery."""

    class PipelineNotFound(Exception):
        pass

    assist_pipeline = ModuleType("homeassistant.components.assist_pipeline")
    assist_pipeline.async_get_pipeline = lambda hass: (_ for _ in ()).throw(KeyError())
    assist_error = ModuleType("homeassistant.components.assist_pipeline.error")
    assist_error.PipelineNotFound = PipelineNotFound
    wake_word = ModuleType("homeassistant.components.wake_word")
    wake_word.async_default_entity = lambda hass: None
    helpers = ModuleType("homeassistant.helpers")
    entity_registry = ModuleType("homeassistant.helpers.entity_registry")
    entity_registry.EntityRegistry = object
    entity_registry.EVENT_ENTITY_REGISTRY_UPDATED = "entity_registry_updated"
    entity_registry.async_get = lambda hass: SimpleNamespace(async_get=lambda entity_id: None)
    dispatcher = ModuleType("homeassistant.helpers.dispatcher")

    def async_dispatcher_connect(hass, signal, target):
        listeners = hass.dispatcher.setdefault(signal, [])
        listeners.append(target)
        return lambda: listeners.remove(target)

    def async_dispatcher_send(hass, signal, *args):
        for target in list(hass.dispatcher.get(signal, [])):
            target(*args)

    dispatcher.async_dispatcher_connect = async_dispatcher_connect
    dispatcher.async_dispatcher_send = async_dispatcher_send
    loader = ModuleType("homeassistant.loader")

    class IntegrationNotFound(Exception):
        pass

    async def async_get_config_flows(hass):
        return set()

    async def async_get_integration(hass, domain):
        raise IntegrationNotFound(domain)

    loader.IntegrationNotFound = IntegrationNotFound
    loader.async_get_config_flows = async_get_config_flows
    loader.async_get_integration = async_get_integration
    homeassistant = sys.modules["homeassistant"]
    homeassistant.loader = loader
    helpers.entity_registry = entity_registry
    helpers.dispatcher = dispatcher

    components.assist_pipeline = assist_pipeline
    components.wake_word = wake_word
    monkeypatch.setitem(sys.modules, "homeassistant.components.assist_pipeline", assist_pipeline)
    monkeypatch.setitem(sys.modules, "homeassistant.components.assist_pipeline.error", assist_error)
    monkeypatch.setitem(sys.modules, "homeassistant.components.wake_word", wake_word)
    monkeypatch.setitem(sys.modules, "homeassistant.helpers", helpers)
    monkeypatch.setitem(sys.modules, "homeassistant.helpers.entity_registry", entity_registry)
    monkeypatch.setitem(sys.modules, "homeassistant.helpers.dispatcher", dispatcher)
    monkeypatch.setitem(sys.modules, "homeassistant.loader", loader)


@pytest.fixture
def websocket_modules(monkeypatch: pytest.MonkeyPatch) -> type:
    """Install the minimal HA modules needed by the WebSocket module."""
    for name in list(sys.modules):
        if name.startswith("custom_components.biofects_butler"):
            sys.modules.pop(name)

    class FakeWebsocketApi:
        ERR_NOT_FOUND = "not_found"

        class ActiveConnection:
            pass

        @staticmethod
        def websocket_command(schema):
            return lambda function: function

        @staticmethod
        def async_response(function):
            return function

        @staticmethod
        def async_register_command(hass, command):
            hass.registered_commands.append(command)

        @staticmethod
        def event_message(subscription_id, event):
            return {"id": subscription_id, "type": "event", "event": event}

    homeassistant = ModuleType("homeassistant")
    components = ModuleType("homeassistant.components")
    components.websocket_api = FakeWebsocketApi
    config_entries = ModuleType("homeassistant.config_entries")
    config_entries.ConfigEntry = object
    core = ModuleType("homeassistant.core")
    core.HomeAssistant = object
    core.callback = lambda function: function

    monkeypatch.setitem(sys.modules, "homeassistant", homeassistant)
    monkeypatch.setitem(sys.modules, "homeassistant.components", components)
    monkeypatch.setitem(sys.modules, "homeassistant.config_entries", config_entries)
    monkeypatch.setitem(sys.modules, "homeassistant.core", core)
    install_status_stubs(monkeypatch, components)
    return FakeWebsocketApi