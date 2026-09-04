"""Tests for the Butler WebSocket API contract."""

from __future__ import annotations

import asyncio
import importlib
import sys
from types import SimpleNamespace


def test_status_contract(websocket_modules) -> None:
    """The M0 status command returns the documented static payload."""
    sys.modules.pop("custom_components.biofects_butler.websocket_api", None)
    module = importlib.import_module("custom_components.biofects_butler.websocket_api")
    sent: list[tuple[int, dict]] = []
    connection = SimpleNamespace(send_result=lambda message_id, data: sent.append((message_id, data)))

    hass = SimpleNamespace(
        config_entries=SimpleNamespace(async_entries=lambda domain: [])
    )
    module.websocket_status(hass, connection, {"id": 7})

    message_id, status = sent[0]
    assert message_id == 7
    assert status["version"] == 2
    assert status["ha_connected"] is True
    assert status["assistant_name"] == "Home"
    assert status["assist_pipeline_ready"] is False
    assert status["wake_word"] == {
        "ready": False,
        "provider": None,
        "wake_word_id": None,
    }
    assert status["stt"] == {"ready": False, "provider": None}
    assert status["tts"] == {"ready": False, "provider": None}
    assert status["conversation_agent"]["ready"] is False


def test_registers_status_command(websocket_modules) -> None:
    """Integration setup registers all Butler commands."""
    sys.modules.pop("custom_components.biofects_butler.websocket_api", None)
    module = importlib.import_module("custom_components.biofects_butler.websocket_api")
    hass = SimpleNamespace(registered_commands=[])

    module.async_register_websocket_api(hass)

    assert hass.registered_commands == [
        module.websocket_status,
        module.websocket_subscribe_status,
        module.websocket_set_assistant_name,
        module.websocket_get_setup_options,
        module.websocket_get_dashboard_profiles,
        module.websocket_save_dashboard_profile,
        module.websocket_delete_dashboard_profile,
        module.websocket_register_display,
        module.websocket_delete_display,
        module.websocket_assign_dashboard_profile,
        module.websocket_subscribe_dashboard_profiles,
    ]


def test_set_assistant_name_persists_and_notifies(websocket_modules) -> None:
    """A name write persists and refreshes every subscribed client."""
    module = importlib.import_module("custom_components.biofects_butler.websocket_api")
    entry = SimpleNamespace(options={"other": True})

    class ConfigEntries:
        def async_entries(self, domain):
            return [entry]

        def async_update_entry(self, updated_entry, *, options):
            updated_entry.options = options

    hass = SimpleNamespace(config_entries=ConfigEntries(), dispatcher={})
    notifications = []
    hass.dispatcher[module.SIGNAL_STATUS_UPDATED] = [lambda: notifications.append(True)]
    results = []
    connection = SimpleNamespace(
        send_result=lambda message_id, data: results.append((message_id, data)),
        send_error=lambda *args: None,
    )

    module.websocket_set_assistant_name(
        hass, connection, {"id": 8, "name": "Jarvis"}
    )

    assert entry.options == {"other": True, "assistant_name": "Jarvis"}
    assert results == [(8, {"assistant_name": "Jarvis"})]
    assert notifications == [True]


def test_subscribe_pushes_pipeline_updates_and_cleans_up(websocket_modules) -> None:
    """A subscription sends immediately, refreshes, and removes its listeners."""
    module = importlib.import_module("custom_components.biofects_butler.websocket_api")
    pipeline_listeners = []
    bus_listeners = []

    def add_pipeline_listener(listener):
        pipeline_listeners.append(listener)
        return lambda: pipeline_listeners.remove(listener)

    def add_bus_listener(event_type, listener):
        bus_listeners.append(listener)
        return lambda: bus_listeners.remove(listener)

    hass = SimpleNamespace(
        bus=SimpleNamespace(async_listen=add_bus_listener),
        config_entries=SimpleNamespace(async_entries=lambda domain: []),
        data={
            "assist_pipeline": SimpleNamespace(
                pipeline_store=SimpleNamespace(
                    async_add_listener=add_pipeline_listener
                )
            )
        },
        dispatcher={},
    )
    messages = []
    results = []
    connection = SimpleNamespace(
        subscriptions={},
        send_message=messages.append,
        send_result=lambda message_id: results.append(message_id),
    )

    module.websocket_subscribe_status(hass, connection, {"id": 9})
    asyncio.run(pipeline_listeners[0]("updated", "pipeline-id", {}))

    assert results == [9]
    assert len(messages) == 2
    assert messages[0]["event"]["assistant_name"] == "Home"
    assert messages[1]["event"] == messages[0]["event"]

    connection.subscriptions[9]()
    assert pipeline_listeners == []
    assert bus_listeners == []
    assert hass.dispatcher[module.SIGNAL_STATUS_UPDATED] == []