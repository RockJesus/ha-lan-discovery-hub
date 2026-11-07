"""Sensor platform: a compact summary of the inventory."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    EVENT_DEVICE_FOUND,
    EVENT_SCAN_FINISHED,
    MANUFACTURER,
)
from .hub import DiscoveryHub
from .registry import STATE_AVAILABLE, STATE_INSTALLABLE, STATE_ORDER

PARALLEL_UPDATES = 0

# Only the most interesting devices are exposed as attributes: state
# attributes hold a handful of values, the panel is the place for a full
# inventory.
ATTRIBUTE_LIMIT = 25


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the summary sensor."""
    hub: DiscoveryHub = entry.runtime_data
    await _async_drop_stale_summary_sensors(hass, entry)
    async_add_entities([DiscoveredDevicesSensor(hub, entry)])


async def _async_drop_stale_summary_sensors(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Remove summary sensors left behind by earlier unique_id schemes.

    They keep showing up as permanently unavailable entities, and the new one
    gets an awkward ``_2`` suffix because the old id is still taken.
    """
    registry = er.async_get(hass)
    keep = f"{entry.entry_id}_devices"
    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        if entity.domain != "sensor" or entity.unique_id == keep:
            continue
        if not entity.unique_id.endswith(("_devices", "_discovered_devices")):
            continue
        registry.async_remove(entity.entity_id)


class DiscoveredDevicesSensor(SensorEntity):
    """Number of LAN devices currently in the inventory."""

    _attr_has_entity_name = True
    _attr_translation_key = "discovered_devices"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:lan"

    def __init__(self, hub: DiscoveryHub, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        self._hub = hub
        self._attr_unique_id = f"{entry.entry_id}_devices"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="LAN Discovery Hub",
            manufacturer=MANUFACTURER,
            model="network inventory",
        )

    async def async_added_to_hass(self) -> None:
        """Refresh whenever a device is seen or a scan finishes."""
        self.async_on_remove(
            self.hass.bus.async_listen(EVENT_DEVICE_FOUND, self._handle_event)
        )
        self.async_on_remove(
            self.hass.bus.async_listen(EVENT_SCAN_FINISHED, self._handle_event)
        )

    @callback
    def _handle_event(self, _event) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self) -> int:
        """Return the number of devices in the inventory."""
        return len(self._hub.registry.records)

    @property
    def extra_state_attributes(self) -> dict:
        """Return counters and the devices that need attention."""
        counts = {
            "configured": 0,
            "available": 0,
            "installable": 0,
            "unknown": 0,
        }
        attention = []
        for record in self._hub.registry.records.values():
            state = record.state
            counts[state] = counts.get(state, 0) + 1
            if state not in (STATE_AVAILABLE, STATE_INSTALLABLE):
                continue
            if record.acknowledged:
                continue
            attention.append(
                {
                    "device_id": record.device_id,
                    "name": record.name,
                    "ip": record.ip,
                    "mac": record.mac,
                    "state": state,
                    "integration": record.integration_name or record.domain,
                    "repo": record.repo,
                }
            )

        attention.sort(
            key=lambda item: STATE_ORDER.get(item["state"], 0), reverse=True
        )
        return {
            "counts": counts,
            "needs_attention": attention[:ATTRIBUTE_LIMIT],
            "scanning": self._hub.scanning,
            "last_scan": self._hub.last_scan,
        }
