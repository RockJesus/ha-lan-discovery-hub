"""The LAN Discovery Hub integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
import voluptuous as vol
from homeassistant.helpers.issue_registry import async_delete_issue

from .const import DOMAIN
from .discovery import DiscoveryHub, _issue_id

PLATFORMS: list[Platform] = [Platform.SENSOR]

if TYPE_CHECKING:
    LanDiscoveryConfigEntry = ConfigEntry[DiscoveryHub]  # HA >= 2024.6
else:
    LanDiscoveryConfigEntry = ConfigEntry


async def async_setup_entry(hass: HomeAssistant, entry: LanDiscoveryConfigEntry) -> bool:
    """Set up LAN Discovery Hub from a config entry.

    必须返回 bool：HA 会检查返回值类型，非 bool 会被判定为 setup 失败
    （日志：``async_setup_entry did not return boolean``）。
    """
    hub = DiscoveryHub(hass, entry)
    await hub.async_start()

    entry.runtime_data = hub
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    async def async_acknowledge(call) -> None:
        """Mark a discovered device as acknowledged by the user."""
        await hub.async_acknowledge(call.data["device_key"])

    # 单实例集成，但仍要防御性判断：reload 期间若旧实例的卸载回调尚未执行，
    # 直接再注册会抛 ValueError 并让 reload 整体失败。
    if not hass.services.has_service(DOMAIN, "acknowledge"):
        hass.services.async_register(
            DOMAIN, "acknowledge", async_acknowledge,
            schema=vol.Schema({vol.Required("device_key"): str}),
        )
        entry.async_on_unload(
            lambda: hass.services.async_remove(DOMAIN, "acknowledge")
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: LanDiscoveryConfigEntry) -> bool:
    """Unload a config entry."""
    hub: DiscoveryHub | None = getattr(entry, "runtime_data", None)
    if hub is not None:
        await hub.async_stop()
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        entry.runtime_data = None
    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: LanDiscoveryConfigEntry) -> None:
    """Reload the entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_remove_entry(hass: HomeAssistant, entry: LanDiscoveryConfigEntry) -> None:
    """Clean up repair issues when the entry is removed.

    2026.10 还没有 issue 的 config_entry_id 归属（2026.11 才有），
    所以在移除时按存储里的设备 key 逐个手动删 issue。
    """
    hub = getattr(entry, "runtime_data", None)
    if hub is None:
        return
    for key in hub.store.data:
        async_delete_issue(hass, DOMAIN, _issue_id(key))
