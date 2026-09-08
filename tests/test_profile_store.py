"""Tests for Home Assistant dashboard profile persistence."""

from __future__ import annotations

import asyncio
import importlib
import sys
from types import ModuleType, SimpleNamespace

import pytest


class FakeStore:
    """Capture Home Assistant storage reads and writes."""

    loaded = None
    saved = None
    constructor_args = None
    save_error = None

    def __init__(self, hass, version, key) -> None:
        type(self).constructor_args = (hass, version, key)

    async def async_load(self):
        return type(self).loaded

    async def async_save(self, data) -> None:
        if type(self).save_error is not None:
            raise type(self).save_error
        type(self).saved = data


@pytest.fixture
def store_module(websocket_modules, monkeypatch):
    """Import the store against a compact HA Store implementation."""
    storage = ModuleType("homeassistant.helpers.storage")
    storage.Store = FakeStore
    monkeypatch.setitem(sys.modules, "homeassistant.helpers.storage", storage)
    FakeStore.loaded = None
    FakeStore.saved = None
    FakeStore.constructor_args = None
    FakeStore.save_error = None
    sys.modules.pop("custom_components.biofects_butler.profile_store", None)
    return importlib.import_module("custom_components.biofects_butler.profile_store")


def test_empty_store_loads_builtin_default(store_module) -> None:
    """A fresh or unavailable store always exposes a usable HUD profile."""
    hass = SimpleNamespace()
    store = store_module.DashboardProfileStore(hass)

    asyncio.run(store.async_load())

    assert FakeStore.constructor_args == (
        hass,
        store_module.DASHBOARD_STORAGE_VERSION,
        "biofects_butler.dashboard_profiles",
    )
    assert [profile.profile_id for profile in store.profiles] == ["default"]
    assert store.for_display("unassigned").profile_id == "default"


def test_load_recovers_valid_profiles_and_assignments(store_module) -> None:
    """Corrupt records are skipped without losing valid neighboring data."""
    custom = dict(store_module.DEFAULT_PROFILE_PAYLOAD)
    custom.update(
        profile_id="bedroom", name="Bedroom", theme="holographic_interface"
    )
    corrupt = dict(store_module.DEFAULT_PROFILE_PAYLOAD)
    corrupt.update(profile_id="bad", schema_version=99)
    FakeStore.loaded = {
        "profiles": [custom, corrupt, "not-an-object"],
        "displays": [
            {
                "display_id": "wall-tablet",
                "name": "Wall Tablet",
                "model": "SM-T733",
                "viewport_class": "expanded",
                "renderer_schema_version": 1,
            },
            {"display_id": "broken"},
        ],
        "assignments": {
            "wall-tablet": "bedroom",
            "missing-profile": "missing",
            "INVALID DISPLAY": "bedroom",
        },
    }
    store = store_module.DashboardProfileStore(SimpleNamespace())

    asyncio.run(store.async_load())

    assert [profile.profile_id for profile in store.profiles] == [
        "bedroom",
        "default",
    ]
    assert store.assignments == {"wall-tablet": "bedroom"}
    assert store.display_themes == {"wall-tablet": "holographic_interface"}
    assert store.for_display("wall-tablet").profile_id == "bedroom"
    assert FakeStore.saved["display_themes"] == {
        "wall-tablet": "holographic_interface"
    }
    assert "theme" not in next(
        profile for profile in FakeStore.saved["profiles"]
        if profile["profile_id"] == "bedroom"
    )


def test_upsert_and_assignment_persist_complete_snapshot(store_module) -> None:
    """Profile and assignment changes save canonical complete snapshots."""
    store = store_module.DashboardProfileStore(SimpleNamespace())
    asyncio.run(store.async_load())
    custom = dict(store_module.DEFAULT_PROFILE_PAYLOAD)
    custom.update(profile_id="kitchen", name="Kitchen")

    profile = asyncio.run(store.async_upsert(custom))
    asyncio.run(
        store.async_register_display(
            {
                "display_id": "display-123",
                "name": "Kitchen",
                "model": "SM-T733",
                "viewport_class": "expanded",
                "renderer_schema_version": 1,
            }
        )
    )
    asyncio.run(
        store.async_assign(
            "display-123", profile.profile_id, "holographic_interface"
        )
    )

    assert FakeStore.saved["assignments"] == {"display-123": "kitchen"}
    assert FakeStore.saved["display_themes"] == {
        "display-123": "holographic_interface"
    }
    assert FakeStore.saved["displays"][0]["model"] == "SM-T733"
    assert [item["profile_id"] for item in FakeStore.saved["profiles"]] == [
        "default",
        "kitchen",
    ]


def test_delete_display_clears_registration_assignment_and_theme(store_module) -> None:
    """Deleting a stale display removes all data keyed by its stable ID."""
    store = store_module.DashboardProfileStore(SimpleNamespace())
    asyncio.run(store.async_load())
    asyncio.run(
        store.async_register_display(
            {
                "display_id": "stale-tablet",
                "name": "Samsung SM-T733",
                "model": "SM-T733",
                "viewport_class": "medium",
                "renderer_schema_version": 1,
            }
        )
    )
    asyncio.run(store.async_assign("stale-tablet", "default", "holographic_interface"))

    asyncio.run(store.async_delete_display("stale-tablet"))

    assert store.displays == ()
    assert store.assignments == {}
    assert store.display_themes == {}
    assert FakeStore.saved["displays"] == []


def test_free_registration_rejects_third_device_but_allows_updates(store_module) -> None:
    """Free keeps two stable registrations and lets either device reconnect."""
    store = store_module.DashboardProfileStore(SimpleNamespace())
    asyncio.run(store.async_load())

    def registration(display_id: str, name: str) -> dict[str, object]:
        return {
            "display_id": display_id,
            "name": name,
            "model": "SM-T733",
            "viewport_class": "medium",
            "renderer_schema_version": 1,
        }

    asyncio.run(store.async_register_display(registration("display-one", "One")))
    asyncio.run(store.async_register_display(registration("display-two", "Two")))
    asyncio.run(store.async_register_display(registration("display-one", "Updated One")))

    with pytest.raises(
        store_module.ProfileValidationError,
        match="Free supports up to 2 devices",
    ):
        asyncio.run(store.async_register_display(registration("display-three", "Three")))

    assert [display.display_id for display in store.displays] == [
        "display-one",
        "display-two",
    ]
    assert store.displays[0].name == "Updated One"


def test_paid_registration_is_not_subject_to_free_device_limit(store_module) -> None:
    """Paid evaluation clients can register beyond the Free display cap."""
    store = store_module.DashboardProfileStore(SimpleNamespace())
    asyncio.run(store.async_load())
    registration = {
        "name": "Display",
        "model": "Android",
        "viewport_class": "medium",
        "renderer_schema_version": 1,
    }

    for display_id in ("free-one", "free-two"):
        asyncio.run(store.async_register_display({
            **registration, "display_id": display_id,
        }))
    paid = asyncio.run(store.async_register_display({
        **registration, "display_id": "paid-three", "edition": "paid",
    }))

    assert paid.edition == "paid"
    assert [display.display_id for display in store.displays] == [
        "free-one", "free-two", "paid-three",
    ]
    assert FakeStore.saved["displays"][-1]["edition"] == "paid"


def test_registration_rejects_unknown_edition(store_module) -> None:
    """Only recognized app editions may affect registration policy."""
    with pytest.raises(
        store_module.ProfileValidationError,
        match="edition must be free or paid",
    ):
        store_module.parse_display_registration({
            "display_id": "display-one",
            "name": "Display",
            "model": "Android",
            "viewport_class": "medium",
            "renderer_schema_version": 1,
            "edition": "unlimited",
        })


def test_reregistration_replaces_old_id_and_preserves_assignment(store_module) -> None:
    """A physical device receives one record even when its registration ID changes."""
    store = store_module.DashboardProfileStore(SimpleNamespace())
    asyncio.run(store.async_load())
    custom = dict(store_module.DEFAULT_PROFILE_PAYLOAD)
    custom.update(profile_id="kitchen", name="Kitchen")
    asyncio.run(store.async_upsert(custom))
    asyncio.run(
        store.async_register_display(
            {
                "display_id": "android_old",
                "name": "Samsung SM-T733",
                "model": "SM-T733",
                "viewport_class": "medium",
                "renderer_schema_version": 1,
            }
        )
    )
    asyncio.run(
        store.async_assign("android_old", "kitchen", "holographic_interface")
    )

    registered = asyncio.run(
        store.async_register_display(
            {
                "display_id": "android_stable",
                "device_key": "android_stable",
                "previous_display_id": "android_old",
                "name": "Samsung SM-T733",
                "model": "SM-T733",
                "viewport_class": "medium",
                "renderer_schema_version": 1,
            }
        )
    )

    assert registered.display_id == "android_stable"
    assert [display.display_id for display in store.displays] == ["android_stable"]
    assert store.assignments == {"android_stable": "kitchen"}
    assert store.display_themes == {"android_stable": "holographic_interface"}
    assert FakeStore.saved["displays"] == [
        {
            "display_id": "android_stable",
            "name": "Samsung SM-T733",
            "model": "SM-T733",
            "viewport_class": "medium",
            "renderer_schema_version": 1,
            "device_key": "android_stable",
        }
    ]


def test_reregistration_deduplicates_matching_device_key(store_module) -> None:
    """A matching stable device key removes an older registration automatically."""
    store = store_module.DashboardProfileStore(SimpleNamespace())
    asyncio.run(store.async_load())

    for display_id in ("android_first", "android_second"):
        asyncio.run(
            store.async_register_display(
                {
                    "display_id": display_id,
                    "device_key": "android_physical_device",
                    "name": "Wall Display",
                    "model": "UC-Display",
                    "viewport_class": "expanded",
                    "renderer_schema_version": 1,
                }
            )
        )

    assert [display.display_id for display in store.displays] == ["android_second"]


def test_first_keyed_registration_collapses_matching_legacy_records(store_module) -> None:
    """Stable IDs replace duplicate legacy records created before device keys existed."""
    store = store_module.DashboardProfileStore(SimpleNamespace())
    asyncio.run(store.async_load())
    for display_id in ("android_legacy_free", "android_legacy_paid"):
        asyncio.run(
            store.async_register_display(
                {
                    "display_id": display_id,
                    "name": "samsung SM-T733",
                    "model": "SM-T733",
                    "viewport_class": "medium",
                    "renderer_schema_version": 1,
                }
            )
        )

    asyncio.run(
        store.async_register_display(
            {
                "display_id": "android_stable_tablet",
                "device_key": "android_stable_tablet",
                "name": "samsung SM-T733",
                "model": "SM-T733",
                "viewport_class": "medium",
                "renderer_schema_version": 1,
            }
        )
    )

    assert [display.display_id for display in store.displays] == [
        "android_stable_tablet"
    ]

    asyncio.run(
        store.async_register_display(
            {
                "display_id": "android_legacy_returns",
                "name": "samsung SM-T733",
                "model": "SM-T733",
                "viewport_class": "medium",
                "renderer_schema_version": 1,
            }
        )
    )

    assert [display.display_id for display in store.displays] == [
        "android_stable_tablet"
    ]


def test_replacement_is_allowed_for_grandfathered_over_limit_store(store_module) -> None:
    """An existing physical device can migrate even when legacy data exceeds the cap."""
    store = store_module.DashboardProfileStore(SimpleNamespace())
    asyncio.run(store.async_load())
    registration = {
        "name": "Other Display",
        "model": "Other",
        "viewport_class": "medium",
        "renderer_schema_version": 1,
    }
    store._displays = {
        "echo": store_module.parse_display_registration(
            {**registration, "display_id": "echo"}
        ),
        "unifi": store_module.parse_display_registration(
            {**registration, "display_id": "unifi"}
        ),
        "tablet_old": store_module.parse_display_registration(
            {
                **registration,
                "display_id": "tablet_old",
                "name": "samsung SM-T733",
                "model": "SM-T733",
            }
        ),
    }

    asyncio.run(
        store.async_register_display(
            {
                **registration,
                "display_id": "tablet_stable",
                "device_key": "tablet_stable",
                "name": "samsung SM-T733",
                "model": "SM-T733",
            }
        )
    )

    assert [display.display_id for display in store.displays] == [
        "echo",
        "tablet_stable",
        "unifi",
    ]


def test_delete_clears_assignments_and_preserves_default(store_module) -> None:
    """Deleting a profile falls assigned displays back to the built-in HUD."""
    store = store_module.DashboardProfileStore(SimpleNamespace())
    asyncio.run(store.async_load())
    custom = dict(store_module.DEFAULT_PROFILE_PAYLOAD)
    custom.update(profile_id="kitchen", name="Kitchen")
    asyncio.run(store.async_upsert(custom))
    asyncio.run(
        store.async_register_display(
            {
                "display_id": "display-123",
                "name": "Kitchen",
                "model": "SM-T733",
                "viewport_class": "expanded",
                "renderer_schema_version": 1,
            }
        )
    )
    asyncio.run(store.async_assign("display-123", "kitchen"))

    asyncio.run(store.async_delete("kitchen"))

    assert store.assignments == {}
    assert store.for_display("display-123").profile_id == "default"
    with pytest.raises(store_module.ProfileValidationError, match="cannot be deleted"):
        asyncio.run(store.async_delete("default"))


def test_rejected_update_keeps_last_valid_snapshot(store_module) -> None:
    """Invalid replacement data never mutates or saves the active profile."""
    store = store_module.DashboardProfileStore(SimpleNamespace())
    asyncio.run(store.async_load())
    before = store.get("default")
    invalid = dict(store_module.DEFAULT_PROFILE_PAYLOAD)
    invalid["schema_version"] = 99

    with pytest.raises(store_module.ProfileValidationError):
        asyncio.run(store.async_upsert(invalid))

    assert store.get("default") is before
    assert FakeStore.saved is None


def test_storage_failure_keeps_last_valid_snapshot(store_module) -> None:
    """An HA storage error cannot expose a profile that was not persisted."""
    store = store_module.DashboardProfileStore(SimpleNamespace())
    asyncio.run(store.async_load())
    custom = dict(store_module.DEFAULT_PROFILE_PAYLOAD)
    custom.update(profile_id="kitchen", name="Kitchen")
    FakeStore.save_error = OSError("disk unavailable")

    with pytest.raises(OSError, match="disk unavailable"):
        asyncio.run(store.async_upsert(custom))

    assert store.get("kitchen") is None
    assert [profile.profile_id for profile in store.profiles] == ["default"]


def test_rejects_assignment_before_display_registration(store_module) -> None:
    """Assignments cannot target an unknown or spoofed display ID."""
    store = store_module.DashboardProfileStore(SimpleNamespace())
    asyncio.run(store.async_load())

    with pytest.raises(store_module.ProfileValidationError, match="unknown display"):
        asyncio.run(store.async_assign("display-123", "default"))


def test_load_migrates_and_rewrites_legacy_profile(store_module) -> None:
    """A supported historical profile is validated and saved canonically."""
    FakeStore.loaded = {
        "profiles": [
            {
                "version": 0,
                "id": "legacy",
                "name": "Legacy",
                "default_screen": "home",
                "screens": [
                    {
                        "id": "home",
                        "title": "Home",
                        "layout": "focused_control",
                        "sections": [
                            {
                                "id": "core",
                                "type": "status_overview",
                                "region": "core",
                                "entities": ["sensor.temperature"],
                            }
                        ],
                    }
                ],
            }
        ],
        "displays": [],
        "assignments": {},
    }
    store = store_module.DashboardProfileStore(SimpleNamespace())

    asyncio.run(store.async_load())

    assert store.get("legacy").schema_version == 1
    saved = next(
        profile for profile in FakeStore.saved["profiles"]
        if profile["profile_id"] == "legacy"
    )
    assert saved["schema_version"] == 1
    assert "version" not in saved


def test_load_rewrites_recovered_snapshot_without_future_profile(store_module) -> None:
    """Unsupported profiles and dangling assignments are removed atomically."""
    future = dict(store_module.DEFAULT_PROFILE_PAYLOAD)
    future.update(profile_id="future", schema_version=99)
    FakeStore.loaded = {
        "profiles": [future],
        "displays": [],
        "assignments": {"missing-display": "future"},
    }
    store = store_module.DashboardProfileStore(SimpleNamespace())

    asyncio.run(store.async_load())

    assert [profile.profile_id for profile in store.profiles] == ["default"]
    assert FakeStore.saved["assignments"] == {}
    assert [item["profile_id"] for item in FakeStore.saved["profiles"]] == [
        "default"
    ]