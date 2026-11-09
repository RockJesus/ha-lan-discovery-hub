"""Config flow for LAN Discovery Hub (single instance)."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

from .i18n import t
from .const import (
    CONF_FULL_SWEEP,
    CONF_IGNORED_TYPES,
    CONF_SCAN_INTERVAL,
    CONF_SOURCES,
    DEFAULT_FULL_SWEEP,
    DEFAULT_IGNORED_TYPES,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SOURCES,
    DOMAIN,
    SOURCE_ARP,
    SOURCE_MDNS,
    SOURCE_PROBE,
    SOURCE_SSDP,
)

_LOGGER = logging.getLogger(__name__)

def source_labels(hass: Any) -> dict[str, str]:
    """Channel names for the options selector in the current language."""
    return {
        SOURCE_MDNS: t(hass, "source.mdns"),
        SOURCE_SSDP: t(hass, "source.ssdp"),
        SOURCE_PROBE: t(hass, "source.probe"),
        SOURCE_ARP: t(hass, "source.arp"),
    }


class LanDiscoveryConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the single-instance config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Create the single hub entry."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if user_input is not None:
            return self.async_create_entry(title="LAN Discovery Hub", data={})
        return self.async_show_form(step_id="user")

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return LanDiscoveryOptionsFlow()


class LanDiscoveryOptionsFlow(OptionsFlow):
    """Tune which channels run and how often."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the scan options."""
        if user_input is not None:
            ignored = [
                item.strip()
                for item in str(user_input.get(CONF_IGNORED_TYPES, "")).split(",")
                if item.strip()
            ]
            data = {
                CONF_SOURCES: user_input[CONF_SOURCES],
                CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL]),
                CONF_FULL_SWEEP: bool(user_input[CONF_FULL_SWEEP]),
                CONF_IGNORED_TYPES: ignored,
            }
            return self.async_create_entry(data=data)

        options = self.config_entry.options
        current_sources = options.get(CONF_SOURCES, DEFAULT_SOURCES)
        current_ignored = options.get(CONF_IGNORED_TYPES, DEFAULT_IGNORED_TYPES)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SOURCES, default=current_sources
                    ): cv.multi_select(source_labels(self.hass)),
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=options.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): vol.All(
                        vol.Coerce(int), vol.Range(min=60, max=86400)
                    ),
                    vol.Required(
                        CONF_FULL_SWEEP,
                        default=options.get(
                            CONF_FULL_SWEEP, DEFAULT_FULL_SWEEP
                        ),
                    ): cv.boolean,
                    vol.Optional(
                        CONF_IGNORED_TYPES,
                        default=", ".join(current_ignored),
                    ): str,
                }
            ),
        )
