"""Live status discovery for Biofects Butler."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from homeassistant.components.assist_pipeline import async_get_pipeline
from homeassistant.components.assist_pipeline.error import PipelineNotFound
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DEFAULT_ASSISTANT_NAME, STATUS_API_VERSION


@dataclass(frozen=True, slots=True)
class ProviderStatus:
    """Represent one selected voice provider."""

    ready: bool
    provider: str | None


@dataclass(frozen=True, slots=True)
class WakeWordStatus:
    """Represent the wake provider and model selected on the HA pipeline."""

    ready: bool
    provider: str | None
    wake_word_id: str | None


@dataclass(frozen=True, slots=True)
class ConversationAgentStatus:
    """Represent the selected conversation agent."""

    ready: bool
    backend: str | None
    model: str | None
    supports_tools: bool | None


@dataclass(frozen=True, slots=True)
class ButlerStatus:
    """Represent aggregated Butler status."""

    version: int
    ha_connected: bool
    assistant_name: str
    assist_pipeline_ready: bool
    wake_word: WakeWordStatus
    stt: ProviderStatus
    tts: ProviderStatus
    conversation_agent: ConversationAgentStatus

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible status payload."""
        return asdict(self)


BACKEND_BY_PLATFORM = {
    "anthropic": "cloud",
    "conversation": "ha_default",
    "extended_openai_conversation": "openai_compatible",
    "google_generative_ai_conversation": "cloud",
    "local_openai": "openai_compatible",
    "ollama": "ollama",
    "openai_conversation": "cloud",
}


def _provider_status(
    registry: er.EntityRegistry, entity_id: str | None
) -> ProviderStatus:
    """Resolve a selected provider without invoking it."""
    if entity_id is None:
        return ProviderStatus(ready=False, provider=None)

    entry = registry.async_get(entity_id)
    provider = (entry.original_name or entry.name or entry.platform) if entry else entity_id
    return ProviderStatus(ready=True, provider=provider)


def _conversation_status(
    hass: HomeAssistant,
    registry: er.EntityRegistry,
    entity_id: str | None,
) -> ConversationAgentStatus:
    """Resolve selected conversation backend metadata."""
    if entity_id is None:
        return ConversationAgentStatus(False, None, None, None)

    entry = registry.async_get(entity_id)
    platform = entry.platform if entry else None
    backend = BACKEND_BY_PLATFORM.get(platform, "unknown") if platform else "unknown"
    model = None
    supports_tools = None

    if entry and entry.config_entry_id:
        config_entry = hass.config_entries.async_get_entry(entry.config_entry_id)
        if config_entry:
            model = _first_string(
                config_entry.options.get("model"),
                config_entry.data.get("model"),
                config_entry.data.get("model_name"),
            )
            tool_value = config_entry.options.get("supports_tools")
            if isinstance(tool_value, bool):
                supports_tools = tool_value

    return ConversationAgentStatus(True, backend, model, supports_tools)


def _first_string(*values: object) -> str | None:
    """Return the first non-empty string."""
    return next((value for value in values if isinstance(value, str) and value), None)


def get_status(hass: HomeAssistant, assistant_name: str) -> ButlerStatus:
    """Discover the preferred HA Assist pipeline and selected providers."""
    registry = er.async_get(hass)
    try:
        pipeline = async_get_pipeline(hass)
    except (KeyError, PipelineNotFound):
        return ButlerStatus(
            version=STATUS_API_VERSION,
            ha_connected=True,
            assistant_name=assistant_name or DEFAULT_ASSISTANT_NAME,
            assist_pipeline_ready=False,
            wake_word=WakeWordStatus(False, None, None),
            stt=ProviderStatus(False, None),
            tts=ProviderStatus(False, None),
            conversation_agent=ConversationAgentStatus(False, None, None, None),
        )

    wake_word_provider = _provider_status(registry, pipeline.wake_word_entity)
    wake_word_id = getattr(pipeline, "wake_word_id", None)
    wake_word_status = WakeWordStatus(
        ready=wake_word_provider.ready and wake_word_id is not None,
        provider=wake_word_provider.provider,
        wake_word_id=wake_word_id,
    )
    stt = _provider_status(registry, pipeline.stt_engine)
    tts = _provider_status(registry, pipeline.tts_engine)
    conversation = _conversation_status(
        hass, registry, pipeline.conversation_engine
    )
    return ButlerStatus(
        version=STATUS_API_VERSION,
        ha_connected=True,
        assistant_name=assistant_name or DEFAULT_ASSISTANT_NAME,
        assist_pipeline_ready=stt.ready and tts.ready and conversation.ready,
        wake_word=wake_word_status,
        stt=stt,
        tts=tts,
        conversation_agent=conversation,
    )