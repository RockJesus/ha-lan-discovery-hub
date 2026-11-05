"""Config flow for LAN Discovery Hub (single instance)."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback

from .const import (
    CONF_IGNORED_TYPES,
    DEFAULT_IGNORED_TYPES,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class LanDiscoveryConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the single-instance config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step — there is nothing to configure."""
        # 单实例集成：固定 unique_id，重复添加直接 abort
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if user_input is not None:
            return self.async_create_entry(title="LAN Discovery Hub", data={})
        return self.async_show_form(step_id="user")

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> OptionsFlow:
        """Return the options flow."""
        return LanDiscoveryOptionsFlow()


class LanDiscoveryOptionsFlow(OptionsFlow):
    """Options: ignored mDNS service types."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        current = self.config_entry.options.get(
            CONF_IGNORED_TYPES, DEFAULT_IGNORED_TYPES
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_IGNORED_TYPES,
                        description={"suggested_value": ", ".join(current)},
                    ): str,
                }
            ),
        )
