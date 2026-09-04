"""Biofects Butler integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DATA_PROFILE_STORE, DOMAIN, PLATFORMS
from .websocket_api import async_register_websocket_api


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Biofects Butler integration."""
    from .frontend import async_register_frontend
    from .profile_store import DashboardProfileStore

    profile_store = DashboardProfileStore(hass)
    await profile_store.async_load()
    hass.data.setdefault(DOMAIN, {})[DATA_PROFILE_STORE] = profile_store
    async_register_websocket_api(hass)
    await async_register_frontend(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Biofects Butler from a config entry."""
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Biofects Butler config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)