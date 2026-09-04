"""Tests for the Butler config flow."""

from __future__ import annotations

import asyncio
import importlib
import sys
from types import ModuleType, SimpleNamespace

import pytest
import voluptuous as vol

from conftest import install_status_stubs


class AlreadyConfigured(Exception):
    """Raised by the test flow when an entry already exists."""


class FakeConfigFlow:
    """Minimal ConfigFlow behavior used by contract tests."""

    configured = False

    def __init_subclass__(cls, **kwargs) -> None:
        cls.domain = kwargs["domain"]

    async def async_set_unique_id(self, unique_id: str) -> None:
        self.unique_id = unique_id

    def _abort_if_unique_id_configured(self) -> None:
        if self.configured:
            raise AlreadyConfigured

    def async_show_form(self, **kwargs) -> dict:
        return {"type": "form", **kwargs}

    def async_create_entry(self, **kwargs) -> dict:
        return {"type": "create_entry", **kwargs}

    def async_abort(self, **kwargs) -> dict:
        return {"type": "abort", **kwargs}


class FakeOptionsFlow:
    """Minimal OptionsFlow behavior used by contract tests."""

    def async_show_form(self, **kwargs) -> dict:
        return {"type": "form", **kwargs}

    def async_create_entry(self, **kwargs) -> dict:
        return {"type": "create_entry", **kwargs}

    def async_abort(self, **kwargs) -> dict:
        return {"type": "abort", **kwargs}


@pytest.fixture
def config_flow_module(monkeypatch: pytest.MonkeyPatch):
    """Import the flow with minimal Home Assistant framework types."""
    for name in list(sys.modules):
        if name.startswith("custom_components.biofects_butler"):
            sys.modules.pop(name)

    homeassistant = ModuleType("homeassistant")
    components = ModuleType("homeassistant.components")
    websocket_api = ModuleType("homeassistant.components.websocket_api")
    websocket_api.ActiveConnection = object
    websocket_api.websocket_command = lambda schema: lambda function: function
    websocket_api.async_response = lambda function: function
    websocket_api.event_message = lambda subscription_id, event: event
    websocket_api.ERR_NOT_FOUND = "not_found"
    websocket_api.async_register_command = lambda hass, command: None
    components.websocket_api = websocket_api
    config_entries = ModuleType("homeassistant.config_entries")
    config_entries.ConfigEntry = object
    config_entries.ConfigFlow = FakeConfigFlow
    config_entries.ConfigFlowResult = dict
    config_entries.OptionsFlow = FakeOptionsFlow
    core = ModuleType("homeassistant.core")
    core.HomeAssistant = object
    core.callback = lambda function: function

    monkeypatch.setitem(sys.modules, "homeassistant", homeassistant)
    monkeypatch.setitem(sys.modules, "homeassistant.components", components)
    monkeypatch.setitem(sys.modules, "homeassistant.components.websocket_api", websocket_api)
    monkeypatch.setitem(sys.modules, "homeassistant.config_entries", config_entries)
    monkeypatch.setitem(sys.modules, "homeassistant.core", core)
    install_status_stubs(monkeypatch, components)
    return importlib.import_module("custom_components.biofects_butler.config_flow")


def ready_status() -> SimpleNamespace:
    """Return a complete preferred-pipeline status."""
    ready = SimpleNamespace(ready=True)
    return SimpleNamespace(
        assist_pipeline_ready=True,
        wake_word=ready,
        stt=ready,
        tts=ready,
        conversation_agent=ready,
    )


def backend_options(configured: bool = True) -> dict:
    """Return configured, configurable, and unavailable choices."""
    return {
        "version": 1,
        "backends": [
            {
                "id": "ha_default",
                "name": "Home Assistant",
                "available": True,
                "configured": True,
                "configuration_url": None,
            },
            {
                "id": "ollama",
                "name": "Ollama",
                "available": True,
                "configured": configured,
                "configuration_url": "/config/integrations/dashboard/add?domain=ollama",
            },
            {
                "id": "missing",
                "name": "Missing provider",
                "available": False,
                "configured": False,
                "configuration_url": None,
            },
        ],
    }


def test_completed_setup_creates_single_entry(config_flow_module, monkeypatch) -> None:
    """A complete pipeline proceeds through backend selection and summary."""
    monkeypatch.setattr(config_flow_module, "get_status", lambda hass, name: ready_status())

    async def get_options(hass):
        return backend_options()

    monkeypatch.setattr(config_flow_module, "async_get_setup_options", get_options)
    flow = config_flow_module.BiofectsButlerConfigFlow()
    flow.hass = object()

    form = asyncio.run(flow.async_step_user())
    pipeline = asyncio.run(flow.async_step_user({}))
    backend = asyncio.run(flow.async_step_pipeline({}))
    summary = asyncio.run(flow.async_step_backend({"conversation_backend": "ollama"}))
    result = asyncio.run(flow.async_step_summary({}))

    assert flow.unique_id == "biofects_butler"
    assert form == {"type": "form", "step_id": "user"}
    assert pipeline["step_id"] == "pipeline"
    assert pipeline["description_placeholders"]["pipeline_state"] == "ready"
    assert backend["step_id"] == "backend"
    assert summary["step_id"] == "summary"
    assert result == {
        "type": "create_entry",
        "title": "Biofects Butler",
        "data": {"conversation_backend": "ollama"},
    }


def test_provider_handoff_retries_and_resumes(config_flow_module, monkeypatch) -> None:
    """An unconfigured backend stays in native-HA handoff until configured."""
    monkeypatch.setattr(config_flow_module, "get_status", lambda hass, name: ready_status())
    configured = False

    async def get_options(hass):
        return backend_options(configured)

    monkeypatch.setattr(config_flow_module, "async_get_setup_options", get_options)
    flow = config_flow_module.BiofectsButlerConfigFlow()
    flow.hass = object()

    asyncio.run(flow.async_step_user({}))
    asyncio.run(flow.async_step_pipeline({}))
    handoff = asyncio.run(flow.async_step_backend({"conversation_backend": "ollama"}))
    retry = asyncio.run(flow.async_step_provider({}))
    configured = True
    resumed = asyncio.run(flow.async_step_provider({}))

    assert handoff["step_id"] == "provider"
    assert handoff["description_placeholders"]["configuration_url"].startswith("/config/")
    assert retry["errors"] == {"base": "provider_not_configured"}
    assert resumed["step_id"] == "summary"


def test_backend_form_filters_unavailable_options(config_flow_module, monkeypatch) -> None:
    """The HA flow does not offer integrations that cannot be configured."""
    async def get_options(hass):
        return backend_options()

    monkeypatch.setattr(config_flow_module, "async_get_setup_options", get_options)
    flow = config_flow_module.BiofectsButlerConfigFlow()
    flow.hass = object()

    form = asyncio.run(flow.async_step_backend())

    assert form["data_schema"]({"conversation_backend": "ollama"})
    with pytest.raises(vol.Invalid):
        form["data_schema"]({"conversation_backend": "missing"})


def test_duplicate_entry_is_rejected(config_flow_module) -> None:
    """A second Butler entry is prevented."""
    flow = config_flow_module.BiofectsButlerConfigFlow()
    flow.configured = True

    with pytest.raises(AlreadyConfigured):
        asyncio.run(flow.async_step_user())