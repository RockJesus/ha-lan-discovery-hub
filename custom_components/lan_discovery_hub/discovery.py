"""LAN device discovery: mDNS/SSDP/DHCP listeners and device bookkeeping.

设计要点（对照 skill 的 2026.10 规范）：
- 推送型：推送型：不引入轮询 coordinator，监听回调即为数据源。
- 数据落盘用 helpers.storage.Store（跨重启记住已见设备）。
- 新设备用 issue_registry 报 warning；用户处理方式是去对应集成配置，
  issue 本身 is_fixable=False（修复流路由到别的集成会在 2026.11 有更官方的
  做法，v0.1 保持简单）。
"""

from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store
from homeassistant.helpers.issue_registry import (
    async_create_issue,
    async_delete_issue,
    IssueSeverity,
)

from .const import (
    CONF_IGNORED_TYPES,
    DEFAULT_IGNORED_TYPES,
    DOMAIN,
    ISSUE_NEW_DEVICE,
)

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
STORAGE_KEY = "lan_discovery_hub/devices"

# hassfest 已收录的、由对应集成负责的常见服务类型（示例子集，
# 完整映射表在 homeassistant/components/zeroconf/discovery.py）。
KNOWN_TYPES: dict[str, str] = {
    "_airplay._tcp.local.": "apple_tv",
    "_googlecast._tcp.local.": "cast",
    "_hue._tcp.local.": "hue",
    "_homekit._tcp.local.": "homekit_controller",
    "_esphomelib._tcp.local.": "esphome",
    "_shelly._tcp.local.": "shelly",
    "_tuya._tcp.local.": "tuya",
    "_matter._tcp.local.": "matter",
    "_ipp._tcp.local.": "ipp",
    "_smb._tcp.local.": "",
    "_http._tcp.local.": "",
}


class DiscoveryStore:
    """Persist seen devices across restarts."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.data: dict[str, dict[str, Any]] = {}

    async def async_load(self) -> None:
        self.data = await self._store.async_load() or {}

    async def async_save(self) -> None:
        await self._store.async_save(self.data)


class DiscoveryHub:
    """Tracks LAN devices seen via mDNS and raises issues for new ones."""

    def __init__(self, hass: HomeAssistant, entry) -> None:
        self.hass = hass
        self.entry = entry
        self.store = DiscoveryStore(hass)
        self._ignored: list[str] = list(
            entry.options.get(CONF_IGNORED_TYPES, DEFAULT_IGNORED_TYPES)
        )

    async def async_start(self) -> None:
        """Load persisted state and subscribe to zeroconf browsing."""
        await self.store.async_load()

        # zeroconf 集成的浏览器由框架管理（它本身已把全部服务类型交给
        # 各集成），这里用 HassJob 包一层自己的回调监听全部类型。
        from homeassistant.components.zeroconf import (  # noqa: PLC0415
            async_get_instance,
        )

        zc = await async_get_instance(self.hass)

        # zeroconf 库的 AsyncServiceBrowser 在 hass 的事件循环里回调
        from zeroconf import (  # noqa: PLC0415
            Zeroconf,
            ServiceStateChange,
        )
        from zeroconf.asyncio import (  # noqa: PLC0415
            AsyncServiceBrowser,
        )

        @callback
        def _on_service_state_change(
            zc: Zeroconf,
            service_type: str,
            name: str,
            state_change: ServiceStateChange,
        ) -> None:
            if state_change is not ServiceStateChange.Added:
                return
            self.hass.async_create_task(
                self._async_handle_service(service_type, name)
            )

        self._browser = AsyncServiceBrowser(
            zc, list(KNOWN_TYPES) or None, handlers=[_on_service_state_change]
        )
        _LOGGER.info("LAN discovery listener started")

    async def async_stop(self) -> None:
        """Tear down the browser."""
        browser = getattr(self, "_browser", None)
        if browser is not None:
            await browser.async_cancel()

    async def _async_handle_service(self, service_type: str, name: str) -> None:
        """Bookkeep one mDNS announcement."""
        if service_type in self._ignored:
            return

        key = f"{service_type}::{name}"
        if key in self.store.data:
            return

        target_domain = KNOWN_TYPES.get(service_type, "")
        info = {
            "service_type": service_type,
            "name": name,
            "first_seen": datetime.now(UTC).isoformat(),
            "suggested_integration": target_domain or None,
        }
        self.store.data[key] = info
        await self.store.async_save()

        self.hass.bus.async_fire(
            "lan_discovery_hub_device_seen",
            {"service_type": service_type, "name": name, "integration": target_domain or None},
        )

        async_create_issue(
            self.hass,
            DOMAIN,
            f"{ISSUE_NEW_DEVICE}_{abs(hash(key)) % 10**10}",
            # 2026.11 起可传 config_entry_id= 让 issue 随 entry 清理；
            # 本集成是 single_config_entry，2026.10 上暂手动清理。
            is_fixable=False,
            severity=IssueSeverity.WARNING,
            translation_key=ISSUE_NEW_DEVICE,
            translation_placeholders={
                "name": name.rsplit(".", 1)[0],
                "service_type": service_type,
                "integration": target_domain or "（未知，需要手动识别）",
            },
        )
        _LOGGER.debug("New LAN device: %s (%s)", name, service_type)

    async def async_acknowledge(self, key: str) -> None:
        """User acknowledged a device: drop its issue but keep the record."""
        if key not in self.store.data:
            return
        self.store.data[key]["acknowledged"] = True
        await self.store.async_save()
        # issue id 在创建时由 key 哈希而来；重放同一哈希以删除
        async_delete_issue(
            self.hass, DOMAIN, f"{ISSUE_NEW_DEVICE}_{abs(hash(key)) % 10**10}"
        )
