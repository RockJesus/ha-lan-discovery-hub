"""MQTT discovery scanning.

A device that only speaks MQTT announces itself on the broker under
``<prefix>/<component>/[<node_id>/]<object_id>/config`` and never touches mDNS,
SSDP or the ARP table. Those announcements are exactly the devices this
integration is supposed to surface *before* anything is configured, so we listen
to them through Home Assistant's own broker connection instead of opening a
second client (which would need the credentials again).

A retained ``config`` message is replayed on subscribe, so the first scan already
sees every device the broker knows about. An empty payload means the device was
removed and its entry is dropped.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from ..const import SOURCE_MQTT
from ..registry import Observation

_LOGGER = logging.getLogger(__name__)

MAX_DEVICES = 250
DISCOVERY_PREFIX_FALLBACK = "homeassistant"


def discovery_prefix(hass: Any) -> str:
    """Return the discovery prefix the broker actually uses."""
    try:
        entries = hass.config_entries.async_entries("mqtt")
    except Exception:  # noqa: BLE001 - mqtt integration may be absent
        return DISCOVERY_PREFIX_FALLBACK
    for entry in entries:
        prefix = (entry.options or {}).get("discovery_prefix")
        if prefix:
            return str(prefix)
    return DISCOVERY_PREFIX_FALLBACK


def is_configured(hass: Any, identifiers: list[Any]) -> bool:
    """Whether a device with these mqtt identifiers is already in the registry."""
    if not identifiers:
        return False
    try:
        from homeassistant.helpers import device_registry as dr  # noqa: PLC0415

        registry = dr.async_get(hass)
    except Exception:  # noqa: BLE001
        return False
    wanted = {str(item) for item in identifiers}
    for device in registry.devices.values():
        for domain, value in device.identifiers:
            if domain == "mqtt" and str(value) in wanted:
                return True
    return False


def parse_config(topic: str, payload: str | None) -> Observation | None:
    """Turn one discovery message into an observation."""
    if not payload:
        return None
    try:
        data = json.loads(payload)
    except ValueError:
        _LOGGER.debug("忽略无法解析的 MQTT discovery: %s", topic)
        return None
    if not isinstance(data, dict):
        return None

    parts = topic.split("/")
    # <prefix>/<component>/<object>/config  or  <prefix>/<component>/<node>/<object>/config
    component = parts[1] if len(parts) > 2 else "?"
    node_id = parts[2] if len(parts) >= 5 else None
    object_id = parts[-2] if len(parts) > 2 else None

    device = data.get("device") if isinstance(data.get("device"), dict) else {}
    identifiers = device.get("identifiers") or []
    if isinstance(identifiers, str):
        identifiers = [identifiers]

    name = (device.get("name") or data.get("name") or "").strip() or None
    if not name and node_id:
        name = str(node_id)
    if not name and object_id:
        name = str(object_id)

    # Identity is the *device*, not the entity: one physical box publishing
    # fourteen sensors must be one row. The device identifier (or the node id
    # when the payload has no device block) is what all entities share.
    uid = (
        str(identifiers[0])
        if identifiers
        else (node_id or data.get("uniq_id") or data.get("unique_id") or object_id)
    )
    if not uid:
        return None
    key = f"mqtt:{uid}"

    availability = data.get("availability_topic")
    if not availability and isinstance(data.get("availability"), list):
        first = data["availability"][0] if data["availability"] else {}
        availability = first.get("topic") if isinstance(first, dict) else None

    return Observation(
        source=SOURCE_MQTT,
        kind="discovery",
        detail=key,
        name=name,
        manufacturer=device.get("manufacturer"),
        model=device.get("model"),
        hint="MQTT",
        unique_instance=True,
        props={
            "topic": topic,
            "component": component,
            "node_id": node_id,
            "identifiers": identifiers,
            "state_topic": data.get("state_topic"),
            "availability_topic": availability,
        },
    )


class MqttScanner:
    """Collects MQTT discovery announcements via HA's broker connection."""

    def __init__(self, hass: Any, on_observation: Any) -> None:
        """Initialize the scanner."""
        self.hass = hass
        self._on_observation = on_observation
        self.available = False
        self.reason: str | None = None
        self._entries: dict[str, Observation] = {}
        self._unsubs: list[Any] = []

    async def async_start(self) -> None:
        """Subscribe to the discovery wildcards."""
        prefix = discovery_prefix(self.hass)
        topics = [f"{prefix}/+/+/config", f"{prefix}/+/+/+/config"]
        try:
            from homeassistant.components.mqtt import async_subscribe  # noqa: PLC0415
        except Exception as err:  # noqa: BLE001 - mqtt is optional
            self.reason = str(err)
            _LOGGER.debug("MQTT 通道不可用: %s", err)
            return

        for topic in topics:
            try:
                unsub = await async_subscribe(
                    self.hass, topic, self._handler, 0, "utf-8"
                )
            except Exception as err:  # noqa: BLE001
                self.reason = str(err)
                _LOGGER.debug("订阅 %s 失败: %s", topic, err)
                continue
            self._unsubs.append(unsub)
        self.available = bool(self._unsubs)
        if self.available:
            self.reason = None
            _LOGGER.debug("MQTT discovery 已订阅: %s", ", ".join(topics))

    async def async_stop(self) -> None:
        """Unsubscribe from the broker."""
        for unsub in self._unsubs:
            try:
                unsub()
            except Exception:  # noqa: BLE001 - shutdown must not raise
                pass
        self._unsubs = []

    def _handler(self, msg: Any) -> None:
        """Record one discovery message."""
        topic = getattr(msg, "topic", "")
        payload = getattr(msg, "payload", None)
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8", "replace")
        if not payload:
            self._entries.pop(topic, None)
            return
        observation = parse_config(topic, payload)
        if observation is None:
            return
        if len(self._entries) >= MAX_DEVICES and topic not in self._entries:
            return
        self._entries[topic] = observation

    def snapshot(self) -> list[Observation]:
        """Every device currently announced on the broker."""
        if not self.available:
            return []
        try:
            return list(self._entries.values())
        except RuntimeError:  # a message landed while we were copying
            return []
