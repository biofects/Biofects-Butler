"""Constants for Biofects Butler."""

from typing import Final

DOMAIN: Final = "biofects_butler"
DEFAULT_ASSISTANT_NAME: Final = "Home"
CONF_ASSISTANT_NAME: Final = "assistant_name"
STATUS_API_VERSION: Final = 2
DASHBOARD_PROFILE_SCHEMA_VERSION: Final = 1
DASHBOARD_STORAGE_VERSION: Final = 1
DASHBOARD_STORAGE_KEY: Final = f"{DOMAIN}.dashboard_profiles"
DATA_PROFILE_STORE: Final = "profile_store"
DEFAULT_PROFILE_ID: Final = "default"
PLATFORMS: Final = ["binary_sensor"]
SIGNAL_STATUS_UPDATED: Final = f"{DOMAIN}_status_updated"
SIGNAL_PROFILES_UPDATED: Final = f"{DOMAIN}_profiles_updated"