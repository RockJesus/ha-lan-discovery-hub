"""LAN Discovery Hub: an inventory of everything on the local network."""

from __future__ import annotations

import json

import logging
from pathlib import Path

import voluptuous as vol

from homeassistant.components.frontend import (
    async_register_built_in_panel,
    async_remove_panel,
)
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    FRONTEND_PATH,
    PANEL_ELEMENT,
    PANEL_MODULE_URL,
    PANEL_URL,
    SERVICE_ACKNOWLEDGE,
    SERVICE_SCAN,
    STORAGE_KEY,
    STORAGE_VERSION,
)

from .hub import DiscoveryHub, async_get_hub
from .websocket_api import async_register_websocket_api

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

SCAN_SCHEMA = vol.Schema({vol.Optional("full", default=False): cv.boolean})
ACKNOWLEDGE_SCHEMA = vol.Schema({vol.Required("device_id"): cv.string})


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the websocket API once, before any entry is set up."""
    async_register_websocket_api(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the hub from a config entry."""
    hub = DiscoveryHub(hass, entry)
    await hub.async_start()

    store = hass.data.setdefault(
        DOMAIN, {"hubs": {}, "panel": False, "static": False}
    )
    store["hubs"][entry.entry_id] = hub
    entry.runtime_data = hub

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await _async_register_panel(hass)
    _async_register_services(hass)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    store = hass.data.get(DOMAIN) or {}
    hub = (store.get("hubs") or {}).pop(entry.entry_id, None)
    if hub is not None:
        await hub.async_stop()

    # Keep the dict itself: the static path flag must survive an unload, because
    # a static path cannot be unregistered and re-registering it would raise.
    if not (store.get("hubs") or {}):
        if store.get("panel"):
            try:
                async_remove_panel(hass, PANEL_URL)
            except Exception as err:  # noqa: BLE001 - panel may already be gone
                _LOGGER.debug("移除侧栏面板失败: %s", err)
            store["panel"] = False

    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove the stored inventory along with the entry."""
    store: Store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    await store.async_remove()


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload when the scan options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def _async_register_panel(hass: HomeAssistant) -> None:
    """Register the sidebar panel and serve its frontend module."""
    store = hass.data.setdefault(
        DOMAIN, {"hubs": {}, "panel": False, "static": False}
    )
    if store.get("panel"):
        return

    if not store.get("static"):
        frontend_dir = Path(__file__).parent / "frontend"
        try:
            await hass.http.async_register_static_paths(
                [StaticPathConfig(FRONTEND_PATH, str(frontend_dir), False)]
            )
        except Exception as err:  # noqa: BLE001 - duplicate path after a reload
            # A static path cannot be unregistered, so a second registration
            # raises. Keep going: the panel itself is what matters.
            _LOGGER.debug("注册前端静态目录失败（可能已注册）: %s", err)
        store["static"] = True

    # Bust the browser's module cache on every release: a custom panel's
    # module_url is a stable path, so without a version the browser keeps
    # rendering the previous build (observed on a real instance after 0.3.6).
    version = "0"
    try:
        version = json.loads(
            (Path(__file__).parent / "manifest.json").read_text(encoding="utf-8")
        ).get("version", "0")
    except Exception:  # noqa: BLE001 - a missing manifest is not fatal here
        pass
    module_url = f"{PANEL_MODULE_URL}?v={version}"

    try:
        async_register_built_in_panel(
            hass,
            component_name="custom",
            sidebar_title="局域网发现",
            sidebar_icon="mdi:lan",
            frontend_url_path=PANEL_URL,
            config={
                "_panel_custom": {
                    "name": PANEL_ELEMENT,
                    "module_url": module_url,
                    "embed_iframe": False,
                    "trust_external": False,
                }
            },
            require_admin=False,
        )
    except ValueError as err:
        # The panel is already registered; that is the desired end state.
        _LOGGER.debug("侧栏面板已存在: %s", err)
    store["panel"] = True


def _async_register_services(hass: HomeAssistant) -> None:
    """Register the scan and acknowledge services once."""
    if hass.services.has_service(DOMAIN, SERVICE_SCAN):
        return

    async def _async_handle_scan(call: ServiceCall) -> None:
        hub = async_get_hub(hass)
        if hub is None:
            _LOGGER.warning("LAN Discovery Hub 未运行，忽略扫描请求")
            return
        await hub.async_rescan(full=bool(call.data.get("full")))

    async def _async_handle_acknowledge(call: ServiceCall) -> None:
        hub = async_get_hub(hass)
        if hub is None:
            return
        await hub.async_acknowledge(call.data["device_id"])

    hass.services.async_register(
        DOMAIN, SERVICE_SCAN, _async_handle_scan, schema=SCAN_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ACKNOWLEDGE,
        _async_handle_acknowledge,
        schema=ACKNOWLEDGE_SCHEMA,
    )
