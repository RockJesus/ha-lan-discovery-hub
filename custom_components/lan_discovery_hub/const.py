"""Constants for the LAN Discovery Hub integration."""

from typing import Final

DOMAIN: Final = "lan_discovery_hub"
MANUFACTURER: Final = "LAN Discovery Hub"

# Storage. Each aggregation schema change gets a fresh key so an upgrade never
# reinterprets records written by an older, possibly buggy, merge strategy.
STORAGE_VERSION: Final = 1
STORAGE_KEY: Final = "lan_discovery_hub.registry.v3"

# Networks that belong to the Home Assistant container itself (supervisor and
# docker bridges). Devices "found" there are services inside the box, not the
# user's LAN, so they are skipped instead of polluting the ledger.
NOISE_IP_NETWORKS: Final = (
    "172.30.32.0/23",
    "172.17.0.0/16",
    "127.0.0.0/8",
    "169.254.0.0/16",
)


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
SOURCE_BLE: Final = "ble"
SOURCE_MQTT: Final = "mqtt"
SOURCE_SERIAL: Final = "serial"

DEFAULT_SOURCES: Final = [
    SOURCE_MDNS,
    SOURCE_SSDP,
    SOURCE_PROBE,
    SOURCE_BLE,
    SOURCE_MQTT,
    SOURCE_SERIAL,
]

# Bluetooth company identifiers -> the integration that would adopt the device.
# Only vendors whose ids are unambiguous are listed; unknown ones stay "unknown"
# rather than pointing the user at the wrong integration.
# Serial adapter fingerprints, checked in order against the /dev/serial/by-id
# name (lower-cased). An empty domain means "recognised hardware, unknown
# integration" — the row still helps, it just does not claim a coordinator.
SERIAL_HINTS: Final = (
    ("sonoff_zigbee", "zha", None, "Sonoff Zigbee"),
    ("skyconnect", "zha", None, "Nabu Casa SkyConnect"),
    ("conbee", "zha", None, "ConBee"),
    ("cc2652", "zha", None, "CC2652"),
    ("cc2531", "zha", None, "CC2531"),
    ("zigbee", "zha", None, "Zigbee 适配器"),
    ("z-stick", "zwave_js", None, "Aeotec Z-Stick"),
    ("zwave", "zwave_js", None, "Z-Wave 适配器"),
    ("aeotec", "zwave_js", None, "Aeotec"),
    ("cp210", "", None, "Silicon Labs CP210x"),
    ("ch340", "", None, "WCH CH340"),
    ("ch343", "", None, "WCH CH343"),
    ("espressif", "", None, "Espressif 串口"),
)

# Fallback when the by-id name carries no model string (unnamed sticks show
# only "usb-0658_0200-if00"): known USB ids of radio adapters.
SERIAL_VID_PID: Final = {
    "0658:0200": ("zwave_js", None, "Aeotec Z-Stick Gen5"),
    "0658:0280": ("zwave_js", None, "Aeotec Z-Stick 7"),
    "10c4:ea60": ("", None, "Silicon Labs CP210x"),
    "1a86:7523": ("", None, "WCH CH340"),
    "303a:1001": ("", None, "Espressif USB JTAG/serial"),
}

BLE_VENDORS: Final = {
    0xFE95: ("xiaomi_ble", None, "Xiaomi"),
    0x0969: ("switchbot", None, "SwitchBot"),
    0x0499: ("ruuvitag_ble", None, "Ruuvi"),
    0x0157: ("qingping", None, "Qingping"),
}
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
