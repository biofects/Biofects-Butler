"""Setup choices owned by existing Home Assistant integrations."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from homeassistant import loader
from homeassistant.core import HomeAssistant


@dataclass(frozen=True, slots=True)
class BackendDefinition:
    """Describe one provider-neutral conversation choice."""

    id: str
    name: str
    category: str
    domains: tuple[str, ...]


BACKENDS = (
    BackendDefinition("ha_default", "Home Assistant", "ha_default", ("conversation",)),
    BackendDefinition("ollama", "Ollama", "ollama", ("ollama",)),
    BackendDefinition(
        "openai_compatible",
        "OpenAI-compatible / vLLM",
        "openai_compatible",
        ("local_openai", "extended_openai_conversation"),
    ),
    BackendDefinition("openai", "OpenAI", "cloud", ("openai_conversation",)),
    BackendDefinition("anthropic", "Anthropic", "cloud", ("anthropic",)),
    BackendDefinition(
        "google_generative_ai",
        "Google Generative AI",
        "cloud",
        ("google_generative_ai_conversation",),
    ),
)


async def async_get_setup_options(hass: HomeAssistant) -> dict:
    """Return conversation choices supported by this HA installation."""
    config_flows = await loader.async_get_config_flows(hass)
    configured_domains = {entry.domain for entry in hass.config_entries.async_entries()}
    options = []

    for backend in BACKENDS:
        installed_domains = []
        for domain in backend.domains:
            try:
                await loader.async_get_integration(hass, domain)
            except loader.IntegrationNotFound:
                continue
            installed_domains.append(domain)

        configured = backend.id == "ha_default" or any(
            domain in configured_domains for domain in backend.domains
        )
        flow_domains = [
            domain for domain in installed_domains if domain in config_flows
        ]
        available = backend.id == "ha_default" or bool(flow_domains)
        owner_domain = next(
            (
                domain
                for domain in backend.domains
                if domain in configured_domains
            ),
            flow_domains[0] if flow_domains else None,
        )
        state = (
            "configured"
            if configured
            else "needs_configuration"
            if available
            else "unavailable"
        )
        options.append(
            {
                **asdict(backend),
                "domains": list(backend.domains),
                "installed": bool(installed_domains),
                "configured": configured,
                "available": available,
                "state": state,
                "integration_domain": owner_domain,
                "configuration_url": (
                    f"/config/integrations/dashboard/add?domain={owner_domain}"
                    if state == "needs_configuration" and owner_domain
                    else None
                ),
            }
        )

    return {"version": 1, "backends": options}