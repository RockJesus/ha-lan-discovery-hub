"""Constants for the LAN Discovery Hub integration."""

from typing import Final

DOMAIN: Final = "lan_discovery_hub"
MANUFACTURER: Final = "LAN Discovery Hub"

# Storage. A new key is used for the v0.2 device-aggregated schema so that
# upgrading does not try to reinterpret the old per-service records.
STORAGE_VERSION: Final = 1
STORAGE_KEY: Final = "lan_discovery_hub.registry.v2"

# Options
CONF_SOURCES: Final = "sources"
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_FULL_SWEEP: Final = "full_sweep"
CONF_IGNORED_TYPES: Final = "ignored_types"
CONF_IGNORED_DEVICES: Final = "ignored_devices"

SOURCE_MDNS: Final = "mdns"
SOURCE_SSDP: Final = "ssdp"
SOURCE_PROBE: Final = "probe"
SOURCE_ARP: Final = "arp"

DEFAULT_SOURCES: Final = [SOURCE_MDNS, SOURCE_SSDP, SOURCE_PROBE]
DEFAULT_SCAN_INTERVAL: Final = 300
DEFAULT_FULL_SWEEP: Final = False
DEFAULT_IGNORED_TYPES: Final = [
    "_spotify-connect._tcp.local.",
    "_companion-link._tcp.local.",
    "_raop._tcp.local.",
]

# Events
EVENT_DEVICE_FOUND: Final = "lan_discovery_hub_device_found"
EVENT_SCAN_FINISHED: Final = "lan_discovery_hub_scan_finished"

# Services
SERVICE_SCAN: Final = "scan"
SERVICE_ACKNOWLEDGE: Final = "acknowledge"

# Panel / frontend
PANEL_URL: Final = "lan-discovery-hub"
PANEL_ELEMENT: Final = "lan-discovery-hub-panel"
PANEL_MODULE_URL: Final = "/lan_discovery_hub_frontend/lan-discovery-hub-panel.js"
FRONTEND_PATH: Final = "/lan_discovery_hub_frontend"

# mDNS: HA's generated table covers most service types, these are the ones we
# always browse for (plus everything the table knows) and the extras that HA
# itself does not map but users still want to see on their network.
EXTRA_MDNS_TYPES: Final = (
    "_smb._tcp.local.",
    "_afpovertcp._tcp.local.",
    "_nfs._tcp.local.",
    "_http._tcp.local.",
    "_https._tcp.local.",
    "_ssh._tcp.local.",
    "_workstation._tcp.local.",
)

# SSDP search targets. `ssdp:all` is intentionally first: it makes devices
# answer with every service they expose, which is what an inventory wants.
SSDP_TARGETS: Final = (
    "ssdp:all",
    "upnp:rootdevice",
    "urn:dial-multiscreen-org:service:dial:1",
    "urn:schemas-upnp-org:device:MediaRenderer:1",
    "urn:schemas-upnp-org:device:MediaServer:1",
    "urn:schemas-upnp-org:device:Basic:1",
)

# TCP probe. Only these ports are tried, and only against IPs we have already
# seen announced or in the ARP cache — no blind network-wide scanning by
# default.
PROBE_PORTS: Final = {
    22: "ssh",
    80: "http",
    443: "https",
    445: "smb",
    548: "afp",
    554: "rtsp",
    1883: "mqtt",
    5000: "http-alt",
    7000: "airplay",
    8009: "cast",
    8123: "home-assistant",
    8888: "http-alt",
    9100: "printer",
    32400: "plex",
    49152: "upnp",
}

# Cheaper port set used by the optional full /24 sweep.
SWEEP_PORTS: Final = (80, 443, 22)
