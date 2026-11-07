"""Bluetooth (BLE) discoveries, read from Home Assistant's bluetooth manager.

We deliberately do not open a scanner of our own: Home Assistant already runs
one (local adapter or an ESPHome proxy) and everything it hears is cached in
``habluetooth``. Reading that cache keeps a single radio owner and means the
ledger shows exactly what HA itself could connect to.

A phone or a watch rotating its random address is not an asset worth listing, so
only advertisements that carry a name or vendor data are kept, and stale cache
entries (older than ``MAX_AGE``) are ignored.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from ..const import BLE_VENDORS, SOURCE_BLE
from ..registry import Observation, normalize_mac

_LOGGER = logging.getLogger(__name__)

MAX_AGE = timedelta(minutes=15)
MAX_DEVICES = 200


def vendor_for(manufacturer_data: dict[int, Any] | None) -> tuple[str | None, str | None, str | None]:
    """Return ``(domain, repo, label)`` for the first vendor id we recognise."""
    for company_id in manufacturer_data or {}:
        entry = BLE_VENDORS.get(int(company_id))
        if entry:
            return entry[0], entry[1], entry[2]
    return None, None, None


def is_stale(last_seen: Any) -> bool:
    """Whether a cached advertisement is too old to be trusted."""
    if not isinstance(last_seen, datetime):
        return False
    now = datetime.now(UTC)
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=UTC)
    return (now - last_seen) > MAX_AGE


class BleScanner:
    """Turns the bluetooth manager's cache into observations."""

    def __init__(self, hass: Any, on_observation: Any) -> None:
        """Initialize the scanner."""
        self.hass = hass
        self._on_observation = on_observation
        self.available = False
        self.reason: str | None = None

    async def async_start(self) -> None:
        """Check that the bluetooth integration can serve us."""
        try:
            from homeassistant.components.bluetooth import (  # noqa: PLC0415
                async_current_scanners,
            )

            scanners = async_current_scanners(self.hass)
        except Exception as err:  # noqa: BLE001 - bluetooth is optional
            self.reason = str(err)
            _LOGGER.debug("蓝牙通道不可用: %s", err)
            return
        self.available = True
        if scanners:
            self.reason = None
        else:
            try:
                entries = self.hass.config_entries.async_entries("bluetooth")
            except Exception:  # noqa: BLE001
                entries = []
            self.reason = (
                f"蓝牙适配器/代理已配置 {len(entries)} 个，但当前没有在线扫描器"
                if entries
                else "没有已启用的蓝牙扫描器（未配置适配器或代理）"
            )
        _LOGGER.debug("蓝牙通道就绪，扫描器 %s 个", len(scanners))

    async def async_stop(self) -> None:
        """Nothing to release: we only read the shared cache."""

    def snapshot(self) -> list[Observation]:
        """Every advertisement currently known, as observations."""
        if not self.available:
            return []
        try:
            from homeassistant.components.bluetooth import (  # noqa: PLC0415
                async_discovered_service_info,
            )

            infos = list(async_discovered_service_info(self.hass, connectable=False))
        except Exception as err:  # noqa: BLE001 - never break the scan loop
            _LOGGER.debug("读取蓝牙缓存失败: %s", err)
            return []

        out: list[Observation] = []
        for info in infos:
            address = normalize_mac(getattr(info, "address", None))
            if not address:
                # macOS-style or otherwise unusable identifiers rotate; skip.
                continue
            name = (getattr(info, "name", None) or "").strip() or None
            manufacturer_data = getattr(info, "manufacturer_data", None) or {}
            if not name and not manufacturer_data:
                continue
            if is_stale(getattr(info, "time", None)):
                continue

            domain, repo, label = vendor_for(manufacturer_data)
            out.append(
                Observation(
                    source=SOURCE_BLE,
                    kind="advertisement",
                    detail=address,
                    name=name,
                    mac=address,
                    manufacturer=label,
                    hint="BLE",
                    unique_instance=True,
                    props={
                        "rssi": getattr(info, "rssi", None),
                        "service_uuids": list(getattr(info, "service_uuids", None) or []),
                        "vendor_domain": domain,
                        "vendor_repo": repo,
                        "source": getattr(info, "source", None),
                        "connectable": bool(getattr(info, "connectable", False)),
                    },
                )
            )
            if len(out) >= MAX_DEVICES:
                break
        return out

    def active_keys(self) -> set[str]:
        """Service keys for the advertisements seen in the last snapshot."""
        return {obs.service_key for obs in self.snapshot()}
