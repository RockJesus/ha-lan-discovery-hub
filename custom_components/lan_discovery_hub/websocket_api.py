"""Websocket API backing the sidebar panel."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .i18n import t
from .const import DOMAIN
from .hub import async_get_hub


@callback
def async_register_websocket_api(hass: HomeAssistant) -> None:
    """Register every command once."""
    websocket_api.async_register_command(hass, websocket_devices)
    websocket_api.async_register_command(hass, websocket_scan)
    websocket_api.async_register_command(hass, websocket_acknowledge)
    websocket_api.async_register_command(hass, websocket_rename)
    websocket_api.async_register_command(hass, websocket_forget)
    websocket_api.async_register_command(hass, websocket_restore)
    websocket_api.async_register_command(hass, websocket_configure)
    websocket_api.async_register_command(hass, websocket_catalog)
    websocket_api.async_register_command(hass, websocket_catalog_refresh)
    websocket_api.async_register_command(hass, websocket_http_probe)


def _hub_or_error(connection: Any, msg: dict[str, Any]) -> Any:
    hub = async_get_hub(connection.hass)
    if hub is None:
        connection.send_error(msg["id"], "not_loaded", t(connection.hass, "ws.not_loaded"))
        return None
    return hub


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/devices",
        vol.Optional("include_ignored", default=False): bool,
    }
)
@websocket_api.async_response
async def websocket_devices(
    hass: HomeAssistant, connection: Any, msg: dict[str, Any]
) -> None:
    """Return the full inventory."""
    hub = _hub_or_error(connection, msg)
    if hub is None:
        return
    connection.send_result(
        msg["id"], hub.snapshot(include_ignored=bool(msg.get("include_ignored")))
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/scan",
        vol.Optional("full", default=False): bool,
    }
)
@websocket_api.async_response
async def websocket_scan(
    hass: HomeAssistant, connection: Any, msg: dict[str, Any]
) -> None:
    """Trigger a scan round."""
    hub = _hub_or_error(connection, msg)
    if hub is None:
        return
    await hub.async_rescan(full=bool(msg.get("full")))
    connection.send_result(msg["id"], {"success": True})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/acknowledge",
        vol.Required("device_id"): str,
    }
)
@websocket_api.async_response
async def websocket_acknowledge(
    hass: HomeAssistant, connection: Any, msg: dict[str, Any]
) -> None:
    """Mark a device as handled."""
    hub = _hub_or_error(connection, msg)
    if hub is None:
        return
    success = await hub.async_acknowledge(msg["device_id"])
    connection.send_result(msg["id"], {"success": success})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/rename",
        vol.Required("device_id"): str,
        vol.Optional("name", default=""): str,
    }
)
@websocket_api.async_response
async def websocket_rename(
    hass: HomeAssistant, connection: Any, msg: dict[str, Any]
) -> None:
    """Pin a name the user chose; an empty name restores automatic naming."""
    hub = _hub_or_error(connection, msg)
    if hub is None:
        return
    success = await hub.async_rename(msg["device_id"], msg.get("name"))
    connection.send_result(msg["id"], {"success": success})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/forget",
        vol.Required("device_id"): str,
    }
)
@websocket_api.async_response
async def websocket_forget(
    hass: HomeAssistant, connection: Any, msg: dict[str, Any]
) -> None:
    """Drop a device from the inventory."""
    hub = _hub_or_error(connection, msg)
    if hub is None:
        return
    success = await hub.async_forget(msg["device_id"])
    connection.send_result(msg["id"], {"success": success})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/restore",
        vol.Required("device_id"): str,
    }
)
@websocket_api.async_response
async def websocket_restore(
    hass: HomeAssistant, connection: Any, msg: dict[str, Any]
) -> None:
    """Bring an ignored device back into the panel."""
    hub = _hub_or_error(connection, msg)
    if hub is None:
        return
    success = await hub.async_restore(msg["device_id"])
    connection.send_result(msg["id"], {"success": success})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/configure",
        vol.Required("domain"): str,
    }
)
@websocket_api.async_response
async def websocket_configure(
    hass: HomeAssistant, connection: Any, msg: dict[str, Any]
) -> None:
    """Open the official setup flow of an integration."""
    hub = _hub_or_error(connection, msg)
    if hub is None:
        return
    result = await hub.async_configure(msg["domain"])
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/catalog",
        vol.Optional("query", default=""): str,
        vol.Optional("limit", default=20): int,
    }
)
@websocket_api.async_response
async def websocket_catalog(
    hass: HomeAssistant, connection: Any, msg: dict[str, Any]
) -> None:
    """Search the marketplace catalog the suggestions are drawn from."""
    hub = _hub_or_error(connection, msg)
    if hub is None:
        return
    query = (msg.get("query") or "").strip().lower()
    limit = max(1, min(int(msg.get("limit") or 20), 100))
    entries = hub.catalog.entries
    if query:
        entries = [
            entry
            for entry in entries
            if query in entry.get("domain", "").lower()
            or query in entry.get("name", "").lower()
            or query in entry.get("description", "").lower()
            or query in entry.get("full_name", "").lower()
        ]
    connection.send_result(
        msg["id"],
        {
            "info": hub.catalog.info(),
            "total": len(entries),
            "entries": entries[:limit],
        },
    )


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/catalog/refresh"})
@websocket_api.async_response
async def websocket_catalog_refresh(
    hass: HomeAssistant, connection: Any, msg: dict[str, Any]
) -> None:
    """Re-fetch the catalog now."""
    hub = _hub_or_error(connection, msg)
    if hub is None:
        return
    ok = await hub.catalog.async_refresh()
    connection.send_result(msg["id"], {"success": ok, **hub.catalog.info()})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/http_probe",
        vol.Required("ip"): str,
        vol.Required("port"): int,
    }
)
@websocket_api.async_response
async def websocket_http_probe(
    hass: HomeAssistant, connection: Any, msg: dict[str, Any]
) -> None:
    """Fetch one device web UI and report status, title or the exact error."""
    from .identity import probe_http  # noqa: PLC0415 - keep import graph flat

    result = await probe_http(hass, msg["ip"], int(msg["port"]))
    connection.send_result(msg["id"], result)
