"""WebSocket API for Biofects Butler."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)

from .const import (
    DASHBOARD_PROFILE_SCHEMA_VERSION,
    DATA_PROFILE_STORE,
    DEFAULT_ASSISTANT_NAME,
    DOMAIN,
    SIGNAL_PROFILES_UPDATED,
    SIGNAL_STATUS_UPDATED,
)
from .profiles import ProfileValidationError
from .status import get_status
from .setup_options import async_get_setup_options


@callback
def async_register_websocket_api(hass: HomeAssistant) -> None:
    """Register Butler WebSocket commands."""
    websocket_api.async_register_command(hass, websocket_status)
    websocket_api.async_register_command(hass, websocket_subscribe_status)
    websocket_api.async_register_command(hass, websocket_get_setup_options)
    websocket_api.async_register_command(hass, websocket_get_dashboard_profiles)
    websocket_api.async_register_command(hass, websocket_save_dashboard_profile)
    websocket_api.async_register_command(hass, websocket_delete_dashboard_profile)
    websocket_api.async_register_command(hass, websocket_register_display)
    websocket_api.async_register_command(hass, websocket_delete_display)
    websocket_api.async_register_command(hass, websocket_assign_dashboard_profile)
    websocket_api.async_register_command(hass, websocket_subscribe_dashboard_profiles)


def _status_payload(hass: HomeAssistant) -> dict[str, Any]:
    """Build the current status payload."""
    return get_status(hass, DEFAULT_ASSISTANT_NAME).as_dict()


@callback
@websocket_api.websocket_command(
    {vol.Required("type"): "biofects_butler/status"}
)
def websocket_status(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return aggregated Butler status."""
    connection.send_result(msg["id"], _status_payload(hass))


@callback
@websocket_api.websocket_command(
    {vol.Required("type"): "biofects_butler/subscribe_status"}
)
def websocket_subscribe_status(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Subscribe a Butler client to live status updates."""

    @callback
    def send_status(*_: Any) -> None:
        connection.send_message(
            websocket_api.event_message(msg["id"], _status_payload(hass))
        )

    async def async_pipeline_changed(*_: Any) -> None:
        send_status()

    pipeline_store = hass.data["assist_pipeline"].pipeline_store
    remove_pipeline_listener = pipeline_store.async_add_listener(
        async_pipeline_changed
    )
    remove_registry_listener = hass.bus.async_listen(
        er.EVENT_ENTITY_REGISTRY_UPDATED, send_status
    )
    remove_butler_listener = async_dispatcher_connect(
        hass, SIGNAL_STATUS_UPDATED, send_status
    )

    @callback
    def unsubscribe() -> None:
        remove_pipeline_listener()
        remove_registry_listener()
        remove_butler_listener()

    connection.subscriptions[msg["id"]] = unsubscribe
    connection.send_result(msg["id"])
    send_status()


@websocket_api.websocket_command(
    {vol.Required("type"): "biofects_butler/get_setup_options"}
)
@websocket_api.async_response
async def websocket_get_setup_options(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return setup choices owned by integrations available in HA."""
    connection.send_result(msg["id"], await async_get_setup_options(hass))


def _profile_store(hass: HomeAssistant) -> Any:
    """Return the loaded dashboard profile store."""
    return hass.data[DOMAIN][DATA_PROFILE_STORE]


def _profiles_payload(hass: HomeAssistant) -> dict[str, Any]:
    """Return one canonical versioned dashboard configuration snapshot."""
    store = _profile_store(hass)
    return {
        "version": DASHBOARD_PROFILE_SCHEMA_VERSION,
        "profiles": [profile.as_dict() for profile in store.profiles],
        "displays": [display.as_dict() for display in store.displays],
        "assignments": store.assignments,
        "display_themes": store.display_themes,
    }


def _send_profile_error(
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
    error: ProfileValidationError,
) -> None:
    """Return a stable validation error without exposing internals."""
    connection.send_error(msg["id"], "invalid_format", str(error))


@callback
@websocket_api.websocket_command(
    {vol.Required("type"): "biofects_butler/get_dashboard_profiles"}
)
def websocket_get_dashboard_profiles(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return all profiles, registered displays, and assignments."""
    connection.send_result(msg["id"], _profiles_payload(hass))


@websocket_api.websocket_command(
    {
        vol.Required("type"): "biofects_butler/save_dashboard_profile",
        vol.Required("profile"): dict,
    }
)
@websocket_api.async_response
async def websocket_save_dashboard_profile(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Validate and persist one complete dashboard profile."""
    try:
        profile = await _profile_store(hass).async_upsert(msg["profile"])
    except ProfileValidationError as error:
        _send_profile_error(connection, msg, error)
        return
    connection.send_result(msg["id"], {"profile": profile.as_dict()})
    async_dispatcher_send(hass, SIGNAL_PROFILES_UPDATED)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "biofects_butler/delete_dashboard_profile",
        vol.Required("profile_id"): vol.All(str, vol.Strip),
    }
)
@websocket_api.async_response
async def websocket_delete_dashboard_profile(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Delete a non-default dashboard profile."""
    try:
        await _profile_store(hass).async_delete(msg["profile_id"])
    except ProfileValidationError as error:
        _send_profile_error(connection, msg, error)
        return
    connection.send_result(msg["id"], {"profile_id": msg["profile_id"]})
    async_dispatcher_send(hass, SIGNAL_PROFILES_UPDATED)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "biofects_butler/register_display",
        vol.Required("display"): dict,
    }
)
@websocket_api.async_response
async def websocket_register_display(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Register display capabilities and return its resolved profile."""
    try:
        display = await _profile_store(hass).async_register_display(msg["display"])
    except ProfileValidationError as error:
        _send_profile_error(connection, msg, error)
        return
    profile = _profile_store(hass).for_display(display.display_id)
    profile_payload = profile.as_dict()
    profile_payload["theme"] = _profile_store(hass).theme_for_display(
        display.display_id
    )
    connection.send_result(
        msg["id"], {"display": display.as_dict(), "profile": profile_payload}
    )
    async_dispatcher_send(hass, SIGNAL_PROFILES_UPDATED)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "biofects_butler/delete_display",
        vol.Required("display_id"): vol.All(str, vol.Strip),
    }
)
@websocket_api.async_response
async def websocket_delete_display(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Delete a stale Butler display registration."""
    try:
        await _profile_store(hass).async_delete_display(msg["display_id"])
    except ProfileValidationError as error:
        _send_profile_error(connection, msg, error)
        return
    connection.send_result(msg["id"], {"display_id": msg["display_id"]})
    async_dispatcher_send(hass, SIGNAL_PROFILES_UPDATED)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "biofects_butler/assign_dashboard_profile",
        vol.Required("display_id"): vol.All(str, vol.Strip),
        vol.Required("profile_id"): vol.All(str, vol.Strip),
        vol.Optional("theme"): vol.All(str, vol.Strip),
    }
)
@websocket_api.async_response
async def websocket_assign_dashboard_profile(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Assign a registered display to a known profile."""
    try:
        await _profile_store(hass).async_assign(
            msg["display_id"], msg["profile_id"], msg.get("theme")
        )
    except ProfileValidationError as error:
        _send_profile_error(connection, msg, error)
        return
    connection.send_result(
        msg["id"],
        {
            "display_id": msg["display_id"],
            "profile_id": msg["profile_id"],
            "theme": _profile_store(hass).theme_for_display(msg["display_id"]),
        },
    )
    async_dispatcher_send(hass, SIGNAL_PROFILES_UPDATED)


@callback
@websocket_api.websocket_command(
    {vol.Required("type"): "biofects_butler/subscribe_dashboard_profiles"}
)
def websocket_subscribe_dashboard_profiles(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Subscribe to complete, atomic dashboard configuration snapshots."""

    @callback
    def send_profiles(*_: Any) -> None:
        connection.send_message(
            websocket_api.event_message(msg["id"], _profiles_payload(hass))
        )

    connection.subscriptions[msg["id"]] = async_dispatcher_connect(
        hass, SIGNAL_PROFILES_UPDATED, send_profiles
    )
    connection.send_result(msg["id"])
    send_profiles()