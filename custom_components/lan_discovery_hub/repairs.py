"""Repair flow: 引导用户前往对应集成完成添加/安装.

设计：
- issue 的 ``is_fixable=True`` 时，点击「修复」会进入这里。
- 目标集成**未安装** → 先初始化该集成的 config flow，再用 repairs 的
  ``next_flow`` 把用户直接送到官方添加/安装界面（链式打开）。
- 目标集成**已安装** → 提示用户去对应集成里添加设备，确认后关闭提示。

注意：这里不替用户做「接入」这个决定，只负责把人送到正确的地方，
符合 HA「发现不等于自动接入」的安全模型。
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.repairs import RepairsFlow
from homeassistant.components.repairs.const import FlowType
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, Any] | None,
) -> RepairsFlow:
    """Create a fix flow for a discovery issue."""
    return DiscoveryGuidanceFlow(hass, issue_id, data or {})


class DiscoveryGuidanceFlow(RepairsFlow):
    """引导用户到目标集成的添加/安装入口。"""

    def __init__(
        self, hass: HomeAssistant, issue_id: str, data: dict[str, Any]
    ) -> None:
        """Initialize the flow."""
        super().__init__()
        self._hass = hass
        self._issue_id = issue_id
        self._data = data
        self._placeholders: dict[str, str] = {}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """显示引导说明，用户点提交后进入 confirm。"""
        target = self._data.get("integration") or ""
        installed = bool(self._data.get("installed"))
        self._placeholders = {
            "integration": target or "未知",
            "installed": "yes" if installed else "no",
        }
        if user_input is not None:
            return await self.async_step_confirm()

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({}),
            description_placeholders=self._placeholders,
        )

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """未安装则链式打开该集成的配置流程，然后关闭本提示。"""
        target = self._data.get("integration") or ""
        installed = bool(self._data.get("installed"))

        if target and not installed:
            try:
                result = await self.hass.config_entries.flow.async_init(
                    target, context={"source": "repairs"}
                )
            except Exception as err:  # noqa: BLE001 - 第三方集成可能不可用
                _LOGGER.warning("无法打开集成 %s 的配置流程: %s", target, err)
                return self.async_abort(
                    reason="cannot_start_flow",
                    description_placeholders={"integration": target},
                )

            flow_id = result.get("flow_id")
            if flow_id:
                _LOGGER.info("引导用户到集成 %s 的配置流程", target)
                return self.async_create_entry(
                    data={},
                    next_flow=(FlowType.CONFIG_FLOW, flow_id),
                )

        return self.async_create_entry(data={})
