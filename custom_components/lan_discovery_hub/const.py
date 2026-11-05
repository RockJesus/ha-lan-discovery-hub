"""Constants for the LAN Discovery Hub integration."""

from typing import Final

DOMAIN: Final = "lan_discovery_hub"
MANUFACTURER: Final = "LAN Discovery Hub"

CONF_IGNORED_TYPES: Final = "ignored_types"
DEFAULT_IGNORED_TYPES: Final = ["_spotify-connect._tcp.local."]

ISSUE_NEW_DEVICE: Final = "new_device"
EVENT_DEVICE_SEEN: Final = "lan_discovery_hub_device_seen"
