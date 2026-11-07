"""Unit tests for the BLE and MQTT channels (plain Python, no HA runtime)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "lan_discovery_hub"


def load(name: str):
    """Import a module (dotted, relative to the integration) without HA runtime."""
    pkg = "ldh_test_pkg"
    if pkg not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            pkg, ROOT / "__init__.py", submodule_search_locations=[str(ROOT)]
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[pkg] = module
        try:
            spec.loader.exec_module(module)
        except Exception:
            pass  # __init__ imports Home Assistant; only const/submodules matter here
    parts = name.split(".")
    for index in range(len(parts) - 1):
        sub = ".".join([pkg, *parts[: index + 1]])
        if sub in sys.modules:
            continue
        spec = importlib.util.spec_from_file_location(
            sub, ROOT.joinpath(*parts[: index + 1]) / "__init__.py",
            submodule_search_locations=[str(ROOT.joinpath(*parts[: index + 1]))],
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[sub] = module
        spec.loader.exec_module(module)
    full = ".".join([pkg, *parts])
    if full in sys.modules:
        return sys.modules[full]
    spec = importlib.util.spec_from_file_location(
        full, ROOT.joinpath(*parts).with_suffix(".py")
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[full] = module
    spec.loader.exec_module(module)
    return module


mqtt = load("scanners.mqtt")
ble = load("scanners.ble")


def test_mqtt_parse() -> None:
    payload = json.dumps(
        {
            "name": "Desk Lamp",
            "uniq_id": "lamp01",
            "state_topic": "zigbee2mqtt/lamp",
            "device": {
                "name": "Lamp",
                "manufacturer": "IKEA",
                "model": "TRADFRI",
                "identifiers": ["zigbee2mqtt_0x00158d0001"],
            },
        }
    )
    obs = mqtt.parse_config("homeassistant/light/lamp01/config", payload)
    assert obs is not None, "four-segment topic must parse"
    assert obs.source == "mqtt"
    assert obs.unique_instance is True, "uniq_id is a real identity"
    assert obs.name == "Lamp", obs.name
    assert obs.props["node_id"] is None
    assert obs.props["identifiers"] == ["zigbee2mqtt_0x00158d0001"]

    obs = mqtt.parse_config(
        "homeassistant/sensor/gw01/temp/config",
        json.dumps({"name": "Temp", "uniq_id": "gw01_temp"}),
    )
    assert obs is not None and obs.props["node_id"] == "gw01"
    assert obs.name == "Temp"

    assert mqtt.parse_config("homeassistant/light/lamp/config", "") is None
    assert mqtt.parse_config("homeassistant/light/lamp/config", "not json") is None
    # No uniq_id: the object id is still enough to show the row.
    obs = mqtt.parse_config("homeassistant/light/lamp/config", json.dumps({"cmd_t": "x"}))
    assert obs is not None and obs.name == "lamp", obs


def test_ble_vendor() -> None:
    assert ble.vendor_for({0xFE95: b"x"})[0] == "xiaomi_ble"
    assert ble.vendor_for({0x0969: b"x"})[0] == "switchbot"
    assert ble.vendor_for({0x004C: b"x"}) == (None, None, None), "Apple stays unknown"
    assert ble.vendor_for({}) == (None, None, None)


def test_ble_stale() -> None:
    from datetime import UTC, datetime, timedelta

    assert ble.is_stale(datetime.now(UTC) - timedelta(minutes=30)) is True
    assert ble.is_stale(datetime.now(UTC)) is False
    assert ble.is_stale(None) is False


def test_ble_merges_with_lan_by_mac() -> None:
    registry = load("registry")
    reg = registry.DeviceRegistry()
    reg.upsert(
        registry.Observation(
            source="ble",
            kind="advertisement",
            detail="aa:bb:cc:dd:ee:ff",
            name="Mi Band",
            mac="aa:bb:cc:dd:ee:ff",
            unique_instance=True,
        )
    )
    reg.upsert(
        registry.Observation(
            source="arp",
            kind="neighbor",
            detail="192.168.1.99",
            ip="192.168.1.99",
            mac="aa:bb:cc:dd:ee:ff",
        )
    )
    assert len(reg.records) == 1, "one device seen over BLE and ARP must be one row"
    record = next(iter(reg.records.values()))
    assert record.ip == "192.168.1.99" and record.name == "Mi Band"


serial = load("scanners.serial")


def test_serial_fingerprints() -> None:
    cases = {
        "usb-ITead_Sonoff_Zigbee_3.0_USB_Dongle_Plus_abc123-if00-port0": "zha",
        "usb-Nabu_Casa_SkyConnect_v1.0_5e9a1c2b-if00-port0": "zha",
        "usb-0658_0200-if00": "zwave_js",  # matched by USB id, no model name
        "usb-Silicon_Labs_CP2102_USB_to_UART_Bridge-if00-port0": "",
        "usb-Aeotec_Z-Stick_Gen5-if00": "zwave_js",
    }
    for by_id, expected in cases.items():
        assert serial.classify(by_id)[0] == expected, by_id
    assert serial.pretty_name(
        "usb-ITead_Sonoff_Zigbee_3.0_USB_Dongle_Plus_abc123-if00-port0"
    ).startswith("ITead Sonoff Zigbee")


if __name__ == "__main__":
    test_serial_fingerprints()
    test_mqtt_parse()
    test_ble_vendor()
    test_ble_stale()
    test_ble_merges_with_lan_by_mac()
    print("channel tests passed")
