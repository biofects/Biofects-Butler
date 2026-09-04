"""Config flow for Biofects Butler."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback

from .const import DEFAULT_ASSISTANT_NAME, DOMAIN
from .setup_options import async_get_setup_options
from .status import ButlerStatus, get_status

CONF_BACKEND = "conversation_backend"


class BiofectsButlerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a Biofects Butler config flow."""

    VERSION = 1

    _reconfigure = False
    _selected_backend: str | None = None
    _status: ButlerStatus | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> BiofectsButlerOptionsFlow:
        """Return the Butler options flow."""
        return BiofectsButlerOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Create the single Butler config entry."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return await self.async_step_pipeline()

        return self.async_show_form(step_id="user")

    async def async_step_pipeline(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the preferred Assist pipeline readiness check."""
        self._status = get_status(self.hass, DEFAULT_ASSISTANT_NAME)
        if user_input is not None:
            return await self.async_step_backend()

        missing = _missing_components(self._status)
        return self.async_show_form(
            step_id="pipeline",
            description_placeholders={
                "pipeline_state": "ready" if self._status.assist_pipeline_ready else "incomplete",
                "missing_components": ", ".join(missing) if missing else "none",
            },
        )

    async def async_step_backend(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select among conversation backends exposed by HA."""
        options = await async_get_setup_options(self.hass)
        choices = {
            option["id"]: option["name"]
            for option in options["backends"]
            if option["available"] or option["configured"]
        }
        if not choices:
            return self.async_abort(reason="no_backends_available")

        if user_input is not None:
            self._selected_backend = user_input[CONF_BACKEND]
            selected = next(
                option
                for option in options["backends"]
                if option["id"] == self._selected_backend
            )
            if not selected["configured"]:
                return await self.async_step_provider()
            return await self.async_step_summary()

        default = self._selected_backend
        if default not in choices:
            default = next(
                (option["id"] for option in options["backends"] if option["configured"]),
                next(iter(choices)),
            )
        return self.async_show_form(
            step_id="backend",
            data_schema=vol.Schema(
                {vol.Required(CONF_BACKEND, default=default): vol.In(choices)}
            ),
        )

    async def async_step_provider(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Hand provider setup to its owning HA integration and resume."""
        options = await async_get_setup_options(self.hass)
        selected = next(
            option
            for option in options["backends"]
            if option["id"] == self._selected_backend
        )
        if selected["configured"]:
            return await self.async_step_summary()

        return self.async_show_form(
            step_id="provider",
            description_placeholders={
                "provider": selected["name"],
                "configuration_url": selected["configuration_url"] or "/config/integrations",
            },
            errors={"base": "provider_not_configured"} if user_input is not None else {},
        )

    async def async_step_summary(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Summarize and save Butler setup."""
        self._status = get_status(self.hass, DEFAULT_ASSISTANT_NAME)
        if user_input is not None:
            data = {CONF_BACKEND: self._selected_backend}
            if self._reconfigure:
                return self.async_update_reload_and_abort(
                    self._get_reconfigure_entry(), data_updates=data
                )
            return self.async_create_entry(title="Biofects Butler", data=data)

        return self.async_show_form(
            step_id="summary",
            description_placeholders={
                "backend": self._selected_backend or "ha_default",
                "pipeline_state": "ready" if self._status.assist_pipeline_ready else "incomplete",
            },
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Rerun setup checks for an existing Butler entry."""
        self._reconfigure = True
        self._selected_backend = self._get_reconfigure_entry().data.get(CONF_BACKEND)
        return await self.async_step_pipeline(user_input)


class BiofectsButlerOptionsFlow(OptionsFlow):
    """Allow changing the preferred backend from Butler options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show available backend choices."""
        options = await async_get_setup_options(self.hass)
        choices = {
            option["id"]: option["name"]
            for option in options["backends"]
            if option["configured"]
        }
        if not choices:
            return self.async_abort(reason="no_configured_backends")
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        default = self.config_entry.options.get(
            CONF_BACKEND,
            self.config_entry.data.get(CONF_BACKEND, next(iter(choices))),
        )
        if default not in choices:
            default = next(iter(choices))
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {vol.Required(CONF_BACKEND, default=default): vol.In(choices)}
            ),
        )


def _missing_components(status: ButlerStatus) -> list[str]:
    """Return actionable names for missing preferred-pipeline components."""
    providers = (
        ("wake word", status.wake_word.ready),
        ("speech to text", status.stt.ready),
        ("text to speech", status.tts.ready),
        ("conversation agent", status.conversation_agent.ready),
    )
    return [name for name, ready in providers if not ready]