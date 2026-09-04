"""Home Assistant storage for Butler dashboard profiles and assignments."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import asdict, dataclass
import re
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import (
    DASHBOARD_PROFILE_SCHEMA_VERSION,
    DASHBOARD_STORAGE_KEY,
    DASHBOARD_STORAGE_VERSION,
    DEFAULT_PROFILE_ID,
)
from .profiles import (
    DashboardProfile,
    ProfileValidationError,
    THEMES,
    parse_dashboard_profile,
)

_DISPLAY_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,127}$")
VIEWPORT_CLASSES = frozenset({"compact", "medium", "expanded"})

DEFAULT_PROFILE_PAYLOAD: dict[str, Any] = {
    "schema_version": 1,
    "profile_id": DEFAULT_PROFILE_ID,
    "name": "Default HUD",
    "default_screen_id": "home",
    "screens": [
        {
            "screen_id": "home",
            "title": "Home",
            "composition": "radial_command_overview",
            "sections": [
                {
                    "section_id": "overview",
                    "type": "status_overview",
                    "slot": "overview",
                },
                {
                    "section_id": "left_navigation",
                    "type": "orbital_menu",
                    "slot": "left_menu",
                },
                {
                    "section_id": "assistant",
                    "type": "entity_controls",
                    "slot": "reactor",
                },
                {
                    "section_id": "right_navigation",
                    "type": "orbital_menu",
                    "slot": "right_menu",
                },
                {"section_id": "media", "type": "media", "slot": "media"},
                {"section_id": "events", "type": "events", "slot": "events"},
            ],
        }
    ],
}


@dataclass(frozen=True, slots=True)
class DisplayRegistration:
    """Describe one Butler renderer without storing credentials."""

    display_id: str
    name: str
    model: str
    viewport_class: str
    renderer_schema_version: int

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible registration payload."""
        return asdict(self)


class DashboardProfileStore:
    """Persist valid profile snapshots and display assignments in HA."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize an unloaded profile store."""
        self._store: Store[dict[str, Any]] = Store(
            hass, DASHBOARD_STORAGE_VERSION, DASHBOARD_STORAGE_KEY
        )
        self._profiles: dict[str, DashboardProfile] = {}
        self._displays: dict[str, DisplayRegistration] = {}
        self._assignments: dict[str, str] = {}
        self._display_themes: dict[str, str] = {}
        self._mutation_lock = asyncio.Lock()

    @property
    def profiles(self) -> tuple[DashboardProfile, ...]:
        """Return the current valid profiles in stable ID order."""
        return tuple(self._profiles[key] for key in sorted(self._profiles))

    @property
    def assignments(self) -> dict[str, str]:
        """Return a copy of current display-to-profile assignments."""
        return dict(self._assignments)

    @property
    def displays(self) -> tuple[DisplayRegistration, ...]:
        """Return registered displays in stable ID order."""
        return tuple(self._displays[key] for key in sorted(self._displays))

    @property
    def display_themes(self) -> dict[str, str]:
        """Return a copy of current display theme selections."""
        return dict(self._display_themes)

    def theme_for_display(self, display_id: str) -> str:
        """Resolve a display theme independently from its dashboard profile."""
        return self._display_themes.get(display_id, "butler_neon")

    async def async_load(self) -> None:
        """Load valid data and guarantee that the built-in profile exists."""
        self._profiles = {
            DEFAULT_PROFILE_ID: parse_dashboard_profile(DEFAULT_PROFILE_PAYLOAD)
        }
        self._displays = {}
        self._assignments = {}
        self._display_themes = {}
        stored = await self._store.async_load()
        if not isinstance(stored, Mapping):
            return
        recovered = False

        profiles = stored.get("profiles")
        if isinstance(profiles, list):
            for payload in profiles:
                try:
                    profile = parse_dashboard_profile(payload)
                except (ProfileValidationError, TypeError):
                    recovered = True
                    continue
                self._profiles[profile.profile_id] = profile
                if payload != profile.as_dict():
                    recovered = True
        elif profiles is not None:
            recovered = True

        displays = stored.get("displays")
        if isinstance(displays, list):
            for payload in displays:
                try:
                    display = parse_display_registration(payload)
                except (ProfileValidationError, TypeError):
                    recovered = True
                    continue
                self._displays[display.display_id] = display
        elif displays is not None:
            recovered = True

        assignments = stored.get("assignments")
        if isinstance(assignments, Mapping):
            valid_assignments = {
                display_id: profile_id
                for display_id, profile_id in assignments.items()
                if display_id in self._displays and profile_id in self._profiles
            }
            self._assignments = valid_assignments
            if dict(assignments) != valid_assignments:
                recovered = True
        elif assignments is not None:
            recovered = True

        display_themes = stored.get("display_themes")
        if isinstance(display_themes, Mapping):
            valid_themes = {
                display_id: theme
                for display_id, theme in display_themes.items()
                if display_id in self._displays and theme in THEMES
            }
            self._display_themes = valid_themes
            if dict(display_themes) != valid_themes:
                recovered = True
        elif display_themes is not None:
            recovered = True

        for display_id, profile_id in self._assignments.items():
            if display_id not in self._display_themes:
                self._display_themes[display_id] = self._profiles[profile_id].theme
                recovered = True

        if recovered:
            await self._async_save_snapshot(
                self._profiles, self._displays, self._assignments, self._display_themes
            )

    def get(self, profile_id: str) -> DashboardProfile | None:
        """Return one profile by ID."""
        return self._profiles.get(profile_id)

    def for_display(self, display_id: str) -> DashboardProfile:
        """Resolve an assigned profile or the built-in fallback."""
        profile_id = self._assignments.get(display_id, DEFAULT_PROFILE_ID)
        return self._profiles.get(profile_id, self._profiles[DEFAULT_PROFILE_ID])

    async def async_upsert(self, payload: Mapping[str, Any]) -> DashboardProfile:
        """Validate and atomically persist one complete profile."""
        profile = parse_dashboard_profile(payload)
        async with self._mutation_lock:
            profiles = {**self._profiles, profile.profile_id: profile}
            await self._async_save_snapshot(
                profiles, self._displays, self._assignments, self._display_themes
            )
            self._profiles = profiles
        return profile

    async def async_delete(self, profile_id: str) -> None:
        """Delete a non-default profile and clear its display assignments."""
        async with self._mutation_lock:
            if profile_id == DEFAULT_PROFILE_ID:
                raise ProfileValidationError(
                    "the built-in default profile cannot be deleted"
                )
            if profile_id not in self._profiles:
                raise ProfileValidationError(f"unknown profile {profile_id!r}")
            profiles = {
                stored_id: profile
                for stored_id, profile in self._profiles.items()
                if stored_id != profile_id
            }
            assignments = {
                display_id: assigned_profile_id
                for display_id, assigned_profile_id in self._assignments.items()
                if assigned_profile_id != profile_id
            }
            await self._async_save_snapshot(
                profiles, self._displays, assignments, self._display_themes
            )
            self._profiles = profiles
            self._assignments = assignments

    async def async_register_display(
        self, payload: Mapping[str, Any]
    ) -> DisplayRegistration:
        """Validate and persist renderer capabilities for one display."""
        display = parse_display_registration(payload)
        async with self._mutation_lock:
            displays = {**self._displays, display.display_id: display}
            await self._async_save_snapshot(
                self._profiles, displays, self._assignments, self._display_themes
            )
            self._displays = displays
        return display

    async def async_delete_display(self, display_id: str) -> None:
        """Delete a display and its profile and theme assignments."""
        async with self._mutation_lock:
            if not _valid_display_id(display_id):
                raise ProfileValidationError("display_id must be a lowercase ID")
            if display_id not in self._displays:
                raise ProfileValidationError(f"unknown display {display_id!r}")
            displays = {
                stored_id: display
                for stored_id, display in self._displays.items()
                if stored_id != display_id
            }
            assignments = {
                stored_id: profile_id
                for stored_id, profile_id in self._assignments.items()
                if stored_id != display_id
            }
            display_themes = {
                stored_id: theme
                for stored_id, theme in self._display_themes.items()
                if stored_id != display_id
            }
            await self._async_save_snapshot(
                self._profiles, displays, assignments, display_themes
            )
            self._displays = displays
            self._assignments = assignments
            self._display_themes = display_themes

    async def async_assign(
        self, display_id: str, profile_id: str, theme: str | None = None
    ) -> None:
        """Assign a profile and theme to a persistent display ID."""
        async with self._mutation_lock:
            if not _valid_display_id(display_id):
                raise ProfileValidationError("display_id must be a lowercase ID")
            if display_id not in self._displays:
                raise ProfileValidationError(f"unknown display {display_id!r}")
            if profile_id not in self._profiles:
                raise ProfileValidationError(f"unknown profile {profile_id!r}")
            if theme is not None and theme not in THEMES:
                raise ProfileValidationError("display theme is unsupported")
            assignments = {**self._assignments, display_id: profile_id}
            display_themes = {
                **self._display_themes,
                display_id: theme or self.theme_for_display(display_id),
            }
            await self._async_save_snapshot(
                self._profiles, self._displays, assignments, display_themes
            )
            self._assignments = assignments
            self._display_themes = display_themes

    async def _async_save_snapshot(
        self,
        profiles: Mapping[str, DashboardProfile],
        displays: Mapping[str, DisplayRegistration],
        assignments: Mapping[str, str],
        display_themes: Mapping[str, str],
    ) -> None:
        """Persist one complete valid snapshot."""
        await self._store.async_save(
            {
                "profiles": [profiles[key].as_dict() for key in sorted(profiles)],
                "displays": [displays[key].as_dict() for key in sorted(displays)],
                "assignments": dict(sorted(assignments.items())),
                "display_themes": dict(sorted(display_themes.items())),
            }
        )


def _valid_display_id(value: Any) -> bool:
    return isinstance(value, str) and _DISPLAY_ID_PATTERN.fullmatch(value) is not None


def parse_display_registration(payload: Mapping[str, Any]) -> DisplayRegistration:
    """Validate one display registration payload."""
    if not isinstance(payload, Mapping):
        raise ProfileValidationError("display must be an object")
    expected = {
        "display_id",
        "name",
        "model",
        "viewport_class",
        "renderer_schema_version",
    }
    missing = expected - payload.keys()
    unknown = payload.keys() - expected
    if missing:
        raise ProfileValidationError(
            f"display missing {', '.join(sorted(missing))}"
        )
    if unknown:
        raise ProfileValidationError(
            f"display has unknown {', '.join(sorted(unknown))}"
        )

    display_id = payload["display_id"]
    if not _valid_display_id(display_id):
        raise ProfileValidationError("display_id must be a lowercase ID")
    name = _display_text(payload["name"], "display.name", 80)
    model = _display_text(payload["model"], "display.model", 100)
    viewport_class = payload["viewport_class"]
    if viewport_class not in VIEWPORT_CLASSES:
        raise ProfileValidationError(
            "display.viewport_class must be compact, medium, or expanded"
        )
    renderer_schema_version = payload["renderer_schema_version"]
    if not isinstance(renderer_schema_version, int) or isinstance(
        renderer_schema_version, bool
    ) or not 1 <= renderer_schema_version <= DASHBOARD_PROFILE_SCHEMA_VERSION:
        raise ProfileValidationError("display renderer schema version is unsupported")
    return DisplayRegistration(
        display_id=display_id,
        name=name,
        model=model,
        viewport_class=viewport_class,
        renderer_schema_version=renderer_schema_version,
    )


def _display_text(value: Any, path: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
        raise ProfileValidationError(f"{path} must be 1 to {maximum} characters")
    return value.strip()