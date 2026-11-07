"""Diagnostics support for LAN Discovery Hub."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .hub import DiscoveryHub

TO_REDACT = {"access_token", "refresh_token", "token", "password", "secret"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: Any
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    hub: DiscoveryHub | None = getattr(entry, "runtime_data", None)
    return {
        "entry": {
            "title": entry.title,
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
        },
        "domain": DOMAIN,
        "scanning": hub.scanning if hub else None,
        "last_scan": hub.last_scan if hub else None,
        "inventory": hub.snapshot() if hub else {},
    }
