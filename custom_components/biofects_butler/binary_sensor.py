"""Binary sensors for Biofects Butler."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DEFAULT_ASSISTANT_NAME, STATUS_API_VERSION


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Butler binary sensors."""
    async_add_entities([ButlerConnectionSensor(entry)])


class ButlerConnectionSensor(BinarySensorEntity):
    """Represent the Butler integration connection state."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_extra_state_attributes = {
        "api_version": STATUS_API_VERSION,
        "assistant_name": DEFAULT_ASSISTANT_NAME,
    }
    _attr_is_on = True
    _attr_name = "Connection"
    _attr_translation_key = "connection"

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the connection sensor."""
        self._attr_unique_id = f"{entry.entry_id}_connection"