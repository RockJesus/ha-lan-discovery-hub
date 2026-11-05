"""Sensor platform for LAN Discovery Hub."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, MANUFACTURER
from .discovery import DiscoveryHub

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    hub: DiscoveryHub = entry.runtime_data
    async_add_entities([DiscoveredDevicesSensor(hub, entry)])


class DiscoveredDevicesSensor(SensorEntity):
    """Reports the number of LAN devices discovered so far."""

    _attr_has_entity_name = True
    _attr_translation_key = "discovered_devices"
    _attr_state_class = SensorStateClass.TOTAL
    _attr_icon = "mdi:radar"

    def __init__(self, hub: DiscoveryHub, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        self._hub = hub
        self._attr_unique_id = f"{entry.entry_id}_discovered_devices"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="LAN Discovery Hub",
            manufacturer=MANUFACTURER,
            model="discovery hub",
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to discovery events."""
        self.async_on_remove(
            self.hass.bus.async_listen(
                "lan_discovery_hub_device_seen",
                self._async_handle_event,
            )
        )

    @callback
    def _async_handle_event(self, event) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self) -> int:
        """Return the number of discovered devices."""
        return len(self._hub.store.data)

    @property
    def extra_state_attributes(self) -> dict:
        """Return the discovered devices as attributes."""
        return {
            "devices": [
                {
                    "name": info["name"],
                    "type": info["service_type"],
                    "integration": info.get("suggested_integration"),
                    "first_seen": info["first_seen"],
                }
                for info in self._hub.store.data.values()
            ]
        }
