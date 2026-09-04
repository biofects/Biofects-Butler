"""Tests for Butler setup choices."""

from __future__ import annotations

import asyncio
import importlib
from types import SimpleNamespace


def test_filters_options_by_installed_flows_and_entries(
    websocket_modules, monkeypatch
) -> None:
    """Classify configured, configurable, and unavailable choices."""
    module = importlib.import_module(
        "custom_components.biofects_butler.setup_options"
    )
    installed = {"conversation", "ollama", "local_openai", "openai_conversation"}

    async def get_integration(hass, domain):
        if domain not in installed:
            raise module.loader.IntegrationNotFound(domain)
        return SimpleNamespace(domain=domain)

    async def get_flows(hass):
        return {"ollama", "local_openai", "openai_conversation"}

    monkeypatch.setattr(module.loader, "async_get_integration", get_integration)
    monkeypatch.setattr(module.loader, "async_get_config_flows", get_flows)
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(
            async_entries=lambda: [SimpleNamespace(domain="local_openai")]
        )
    )

    payload = asyncio.run(module.async_get_setup_options(hass))
    options = {option["id"]: option for option in payload["backends"]}

    assert payload["version"] == 1
    assert options["ha_default"]["state"] == "configured"
    assert options["ollama"]["state"] == "needs_configuration"
    assert options["ollama"]["configuration_url"].endswith("domain=ollama")
    assert options["openai_compatible"]["state"] == "configured"
    assert options["openai_compatible"]["integration_domain"] == "local_openai"
    assert options["openai"]["state"] == "needs_configuration"
    assert options["anthropic"]["state"] == "unavailable"
    assert options["anthropic"]["configuration_url"] is None


def test_websocket_command_returns_versioned_options(
    websocket_modules, monkeypatch
) -> None:
    """Expose setup options through the authenticated WebSocket command."""
    module = importlib.import_module(
        "custom_components.biofects_butler.websocket_api"
    )

    async def get_options(hass):
        return {"version": 1, "backends": []}

    monkeypatch.setattr(module, "async_get_setup_options", get_options)
    sent = []
    connection = SimpleNamespace(
        send_result=lambda message_id, result: sent.append((message_id, result))
    )

    asyncio.run(
        module.websocket_get_setup_options(
            SimpleNamespace(), connection, {"id": 14}
        )
    )

    assert sent == [(14, {"version": 1, "backends": []})]