"""Tests for live Butler status discovery."""

from __future__ import annotations

import importlib
from types import SimpleNamespace


def discover(monkeypatch, pipeline, entities, config_entry=None):
    """Run discovery against a compact pipeline/registry fixture."""
    module = importlib.import_module("custom_components.biofects_butler.status")
    registry = SimpleNamespace(async_get=entities.get)
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(
            async_get_entry=lambda entry_id: config_entry
        )
    )
    monkeypatch.setattr(module, "async_get_pipeline", lambda hass: pipeline)
    monkeypatch.setattr(module.er, "async_get", lambda hass: registry)
    return module.get_status(hass, "Home").as_dict()


def test_discovers_real_pipeline_shape(websocket_modules, monkeypatch) -> None:
    """Map the preferred pipeline shape used by the real HA instance."""
    module = importlib.import_module("custom_components.biofects_butler.status")
    pipeline = SimpleNamespace(
        conversation_engine="conversation.tfam_ai",
        stt_engine="stt.faster_whisper",
        tts_engine="tts.piper",
        wake_word_entity=None,
    )
    entities = {
        "conversation.tfam_ai": SimpleNamespace(
            original_name=None,
            name=None,
            platform="local_openai",
            config_entry_id="agent-entry",
        ),
        "stt.faster_whisper": SimpleNamespace(
            original_name="faster-whisper",
            name=None,
            platform="wyoming",
            config_entry_id="stt-entry",
        ),
        "tts.piper": SimpleNamespace(
            original_name="piper",
            name=None,
            platform="wyoming",
            config_entry_id="tts-entry",
        ),
        "wake_word.openwakeword": SimpleNamespace(
            original_name="openwakeword",
            name=None,
            platform="wyoming",
            config_entry_id="wake-entry",
        ),
    }
    registry = SimpleNamespace(async_get=entities.get)
    config_entries = SimpleNamespace(
        async_get_entry=lambda entry_id: SimpleNamespace(data={}, options={})
    )
    hass = SimpleNamespace(config_entries=config_entries)
    monkeypatch.setattr(module, "async_get_pipeline", lambda hass: pipeline)
    monkeypatch.setattr(module.er, "async_get", lambda hass: registry)
    status = module.get_status(hass, "Home").as_dict()

    assert status["assist_pipeline_ready"] is True
    assert status["wake_word"] == {
        "ready": False,
        "provider": None,
        "wake_word_id": None,
    }
    assert status["stt"] == {"ready": True, "provider": "faster-whisper"}
    assert status["tts"] == {"ready": True, "provider": "piper"}
    assert status["conversation_agent"] == {
        "ready": True,
        "backend": "openai_compatible",
        "model": None,
        "supports_tools": None,
    }


def test_partial_pipeline_is_not_ready(websocket_modules, monkeypatch) -> None:
    """A selected TTS alone does not make the Assist pipeline ready."""
    pipeline = SimpleNamespace(
        conversation_engine=None,
        stt_engine=None,
        tts_engine="tts.piper",
        wake_word_entity=None,
    )

    status = discover(monkeypatch, pipeline, {}, None)

    assert status["assist_pipeline_ready"] is False
    assert status["stt"] == {"ready": False, "provider": None}
    assert status["tts"] == {"ready": True, "provider": "tts.piper"}
    assert status["conversation_agent"]["ready"] is False


def test_maps_default_conversation_backend(websocket_modules, monkeypatch) -> None:
    """HA's built-in conversation agent has a stable backend category."""
    entity_id = "conversation.home_assistant"
    pipeline = SimpleNamespace(
        conversation_engine=entity_id,
        stt_engine="stt.cloud",
        tts_engine="tts.cloud",
        wake_word_entity=None,
    )
    entities = {
        entity_id: SimpleNamespace(
            original_name="Home Assistant",
            name=None,
            platform="conversation",
            config_entry_id=None,
        )
    }

    status = discover(monkeypatch, pipeline, entities)

    assert status["conversation_agent"]["backend"] == "ha_default"
    assert status["conversation_agent"]["model"] is None
    assert status["conversation_agent"]["supports_tools"] is None


def test_exposed_metadata_and_unknown_backend(websocket_modules, monkeypatch) -> None:
    """Expose known metadata while preserving an unknown backend category."""
    entity_id = "conversation.future_agent"
    pipeline = SimpleNamespace(
        conversation_engine=entity_id,
        stt_engine="stt.provider",
        tts_engine="tts.provider",
        wake_word_entity="wake_word.provider",
        wake_word_id="alexa",
    )
    entities = {
        entity_id: SimpleNamespace(
            original_name=None,
            name="Future Agent",
            platform="future_conversation",
            config_entry_id="future-entry",
        )
    }
    config_entry = SimpleNamespace(
        data={"model": "future-model"},
        options={"supports_tools": True},
    )

    status = discover(monkeypatch, pipeline, entities, config_entry)

    assert status["wake_word"]["ready"] is True
    assert status["wake_word"]["wake_word_id"] == "alexa"
    assert status["conversation_agent"] == {
        "ready": True,
        "backend": "unknown",
        "model": "future-model",
        "supports_tools": True,
    }