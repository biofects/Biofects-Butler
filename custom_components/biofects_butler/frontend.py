"""Home Assistant frontend registration for the Butler profile editor."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components import panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

PANEL_URL_PATH = "biofects-butler"
PANEL_MODULE_URL = "/biofects_butler_static/biofects-butler-panel.js?v=60"
PANEL_ELEMENT = "biofects-butler-panel"


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Serve and register the administrator-only profile editor panel."""
    frontend_path = Path(__file__).parent / "frontend"
    await hass.http.async_register_static_paths(
        [StaticPathConfig("/biofects_butler_static", str(frontend_path), False)]
    )
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL_PATH,
        webcomponent_name=PANEL_ELEMENT,
        sidebar_title="Butler Dashboards",
        sidebar_icon="mdi:monitor-dashboard",
        module_url=PANEL_MODULE_URL,
        require_admin=True,
    )