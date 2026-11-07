"""Runtime hub: owns the scanners, the device registry and the guidance state."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.event import async_call_later, async_track_time_interval
from homeassistant.helpers.storage import Store

from .const import (
    CONF_FULL_SWEEP,
    CONF_IGNORED_DEVICES,
    CONF_IGNORED_TYPES,
    CONF_SCAN_INTERVAL,
    CONF_SOURCES,
    DEFAULT_FULL_SWEEP,
    DEFAULT_IGNORED_TYPES,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SOURCES,
    EVENT_DEVICE_FOUND,
    EVENT_SCAN_FINISHED,
    EXTRA_MDNS_TYPES,
    PROBE_PORTS,
    SOURCE_ARP,
    SOURCE_MDNS,
    SOURCE_PROBE,
    SOURCE_SSDP,
    SSDP_TARGETS,
    STORAGE_KEY,
    STORAGE_VERSION,
    SWEEP_PORTS,
)
from .matcher import IntegrationMatcher
from .registry import (
    STATE_AVAILABLE,
    STATE_CONFIGURED,
    STATE_INSTALLABLE,
    STATE_ORDER,
    STATE_UNKNOWN,
    DeviceRecord,
    DeviceRegistry,
    Observation,
)
from .scanners.mdns import MdnsScanner
from .scanners.probe import (
    async_probe_ips,
    async_sweep_subnet,
    local_prefix,
    read_arp_cache,
)
from .scanners.ssdp import SsdpScanner

_LOGGER = logging.getLogger(__name__)

NOTIFICATION_ID = "lan_discovery_hub_devices"
NOTIFY_DELAY = 8
SAVE_DELAY = 5
FIRST_SCAN_DELAY = 20
ACTIONABLE_STATES = (STATE_AVAILABLE, STATE_INSTALLABLE)


def _utcnow() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class DiscoveryHub:
    """Coordinates scanning, aggregation, matching and user guidance."""

    def __init__(self, hass: HomeAssistant, entry: Any) -> None:
        """Initialize the hub from the config entry options."""
        self.hass = hass
        self.entry = entry
        options = entry.options

        self.registry = DeviceRegistry()
        self.matcher = IntegrationMatcher(hass.config.config_dir)
        self.store: Store = Store(hass, STORAGE_VERSION, STORAGE_KEY)

        self._mdns: MdnsScanner | None = None
        self._ssdp: SsdpScanner | None = None
        self._unsub_interval: Any = None
        self._unsub_first_scan: Any = None
        self._save_unsub: Any = None
        self._notify_unsub: Any = None
        self._scan_lock = asyncio.Lock()

        self._sources = list(options.get(CONF_SOURCES, DEFAULT_SOURCES))
        self._interval = max(
            60, int(options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
        )
        self._ignored_types = [
            str(item).lower()
            for item in options.get(CONF_IGNORED_TYPES, DEFAULT_IGNORED_TYPES)
        ]
        self._ignored_devices = set(options.get(CONF_IGNORED_DEVICES, []))
        self._full_sweep = bool(options.get(CONF_FULL_SWEEP, DEFAULT_FULL_SWEEP))

        self.scanning = False
        self.last_scan: str | None = None

    # ------------------------------------------------------------------ live

    async def async_start(self) -> None:
        """Load stored devices and start every enabled scanner."""
        await self._async_load()

        if SOURCE_MDNS in self._sources:
            service_types = sorted(
                set(self.matcher.mdns_service_types()) | set(EXTRA_MDNS_TYPES)
            )
            self._mdns = MdnsScanner(
                self.hass,
                self._async_on_observation,
                service_types,
                self._ignored_types,
            )
            try:
                await self._mdns.async_start()
            except Exception as err:  # noqa: BLE001 - mDNS must not block setup
                _LOGGER.warning("启动 mDNS 扫描失败: %s", err)
                self._mdns = None

        if SOURCE_SSDP in self._sources:
            self._ssdp = SsdpScanner(
                self.hass, self._async_on_observation, SSDP_TARGETS
            )

        self._unsub_interval = async_track_time_interval(
            self.hass,
            self._async_periodic_scan,
            timedelta(seconds=self._interval),
        )
        self._unsub_first_scan = async_call_later(
            self.hass, FIRST_SCAN_DELAY, self._async_first_scan
        )

    async def async_stop(self) -> None:
        """Stop scanning and flush pending state."""
        for unsub in (
            self._unsub_interval,
            self._unsub_first_scan,
            self._save_unsub,
            self._notify_unsub,
        ):
            if unsub:
                unsub()
        self._unsub_interval = None
        self._unsub_first_scan = None
        self._save_unsub = None
        self._notify_unsub = None

        if self._mdns is not None:
            await self._mdns.async_stop()
            self._mdns = None

        await self._async_save()

    # ------------------------------------------------------------- persistence

    async def _async_load(self) -> None:
        try:
            stored = await self.store.async_load()
        except (ValueError, KeyError, TypeError) as err:
            _LOGGER.warning("读取存储失败，将重新开始: %s", err)
            stored = None
        if stored:
            self.registry.load(stored)

    async def _async_save(self) -> None:
        try:
            await self.store.async_save(self.registry.as_payload())
        except (OSError, ValueError) as err:
            _LOGGER.warning("保存设备台账失败: %s", err)

    def _schedule_save(self) -> None:
        if self._save_unsub is not None:
            return
        self._save_unsub = async_call_later(
            self.hass, SAVE_DELAY, self._async_save_later
        )

    async def _async_save_later(self, _now: Any = None) -> None:
        self._save_unsub = None
        await self._async_save()

    # ---------------------------------------------------------------- scanning

    async def _async_first_scan(self, _now: Any = None) -> None:
        self._unsub_first_scan = None
        await self.async_rescan()

    async def _async_periodic_scan(self, _now: Any = None) -> None:
        await self.async_rescan()

    async def async_rescan(self, full: bool = False) -> None:
        """Run one scan round across the enabled channels."""
        if self._scan_lock.locked():
            _LOGGER.debug("上一轮扫描仍在进行，跳过本轮")
            return
        async with self._scan_lock:
            self.scanning = True
            try:
                if SOURCE_ARP in self._sources or SOURCE_PROBE in self._sources:
                    await self._async_collect_arp()
                if self._ssdp is not None:
                    await self._ssdp.async_scan()
                if full or self._full_sweep:
                    await self._async_sweep_subnet()
                if SOURCE_PROBE in self._sources:
                    await self._async_probe_known()
            except Exception as err:  # noqa: BLE001 - a broken channel must not kill the loop
                _LOGGER.exception("扫描出错: %s", err)
            finally:
                self.scanning = False
                self.last_scan = _utcnow()

        await self._async_save()
        self.hass.bus.async_fire(
            EVENT_SCAN_FINISHED, {"devices": len(self.registry.records)}
        )

    async def _async_collect_arp(self) -> None:
        cache = read_arp_cache()
        if not cache:
            _LOGGER.debug("没有可用的 ARP 邻居缓存")
            return
        for ip, mac in cache.items():
            await self._async_on_observation(
                Observation(
                    source=SOURCE_ARP,
                    kind="neighbor",
                    detail="arp",
                    ip=ip,
                    mac=mac,
                    hint="arp",
                )
            )

    async def _async_probe_known(self) -> None:
        targets = [
            record.ip
            for record in list(self.registry.records.values())
            if record.ip and not record.ip.startswith("127.")
        ]
        if not targets:
            return
        results = await async_probe_ips(targets, tuple(PROBE_PORTS))
        for ip, ports in results.items():
            if not ports:
                continue
            await self._async_on_observation(
                Observation(
                    source=SOURCE_PROBE,
                    kind="tcp",
                    detail="open-ports",
                    ip=ip,
                    hint="tcp",
                    props={"ports": ports},
                )
            )

    async def _async_sweep_subnet(self) -> None:
        prefix = local_prefix()
        if not prefix:
            _LOGGER.warning("无法确定本机网段，跳过全网段扫描")
            return
        _LOGGER.info("开始 /24 网段扫描: %s.0/24", prefix)
        results = await async_sweep_subnet(prefix, SWEEP_PORTS)
        for ip, ports in results.items():
            if not ports:
                continue
            await self._async_on_observation(
                Observation(
                    source=SOURCE_PROBE,
                    kind="tcp",
                    detail="open-ports",
                    ip=ip,
                    hint="tcp",
                    props={"ports": ports},
                )
            )

    # ------------------------------------------------------------- aggregation

    async def _async_on_observation(self, observation: Observation) -> None:
        """Fold one sighting into the registry and update guidance."""
        if (
            observation.source == SOURCE_MDNS
            and observation.kind.lower() in self._ignored_types
        ):
            return

        record, created = self.registry.upsert(observation)
        if record.device_id in self._ignored_devices:
            return

        self._async_apply_match(record, observation)

        if created:
            self.hass.bus.async_fire(
                EVENT_DEVICE_FOUND,
                {
                    "device_id": record.device_id,
                    "name": record.name,
                    "ip": record.ip,
                    "mac": record.mac,
                    "state": record.state,
                    "domain": record.domain,
                    "source": observation.source,
                    "service": observation.service_key,
                },
            )
            self._schedule_notification()

        self._schedule_save()

    def _async_apply_match(
        self, record: DeviceRecord, observation: Observation
    ) -> None:
        """Store the integration match (never downgrade a stronger match)."""
        match = self.matcher.resolve(observation)
        if match is None or not match.domain:
            return

        present = self.matcher.integration_present(self.hass, match.domain)
        configured = self._async_is_device_configured(record)
        if configured:
            state = STATE_CONFIGURED
        elif present:
            state = STATE_AVAILABLE
        else:
            state = STATE_INSTALLABLE

        current_rank = STATE_ORDER.get(record.state, 0)
        new_rank = STATE_ORDER.get(state, 0)
        if (
            record.domain
            and record.domain != match.domain
            and current_rank > new_rank
        ):
            # A previously resolved, more actionable match wins over a
            # fingerprint that only maps to a weaker state.
            return
        if record.domain == match.domain and current_rank == new_rank:
            return

        display = match.integration or self.matcher.display_name(
            self.hass, match.domain
        )
        self.registry.set_match(
            record.device_id,
            state=state,
            domain=match.domain,
            integration_name=display,
            repo=match.repo,
            match_source=match.source,
        )

    def _async_is_device_configured(self, record: DeviceRecord) -> bool:
        """Whether an existing device registry entry already covers this device."""
        registry = dr.async_get(self.hass)
        for device in registry.devices.values():
            if record.mac:
                for connection_type, value in device.connections:
                    if (
                        connection_type == "mac"
                        and str(value).lower() == record.mac
                    ):
                        return True
            if record.ip and device.configuration_url:
                if record.ip in device.configuration_url:
                    return True
        return False

    # ------------------------------------------------------------ notification

    def _schedule_notification(self) -> None:
        if self._notify_unsub is not None:
            return
        self._notify_unsub = async_call_later(
            self.hass, NOTIFY_DELAY, self._async_notify
        )

    async def _async_notify(self, _now: Any = None) -> None:
        """Send one summary notification instead of one per device."""
        self._notify_unsub = None
        from homeassistant.components import persistent_notification  # noqa: PLC0415

        actionable = [
            record
            for record in self.registry.records.values()
            if not record.acknowledged and record.state in ACTIONABLE_STATES
        ]
        if not actionable:
            return

        actionable.sort(key=lambda item: (STATE_ORDER[item.state], item.name.lower()))
        lines = []
        for record in actionable[:8]:
            integration = record.integration_name or record.domain or "未知集成"
            where = record.ip or record.mac or "未知地址"
            lines.append(f"- **{record.name}**（{where}）→ {integration}")
        if len(actionable) > 8:
            lines.append(f"- 其余 {len(actionable) - 8} 台见面板")

        message = (
            f"发现 **{len(actionable)}** 台可接入的设备：\n\n"
            + "\n".join(lines)
            + "\n\n打开侧栏「局域网发现」面板可查看全部设备、一键配置或安装对应集成。"
        )
        try:
            persistent_notification.async_create(
                self.hass,
                message,
                title="局域网发现",
                notification_id=NOTIFICATION_ID,
            )
        except Exception as err:  # noqa: BLE001 - notification is best effort
            _LOGGER.debug("创建通知失败: %s", err)

    async def async_dismiss_notification(self) -> None:
        """Remove the summary notification once nothing needs attention."""
        remaining = [
            record
            for record in self.registry.records.values()
            if not record.acknowledged and record.state in ACTIONABLE_STATES
        ]
        if remaining:
            return
        from homeassistant.components import persistent_notification  # noqa: PLC0415

        try:
            persistent_notification.async_dismiss(self.hass, NOTIFICATION_ID)
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("移除通知失败: %s", err)

    # ---------------------------------------------------------------- actions

    async def async_configure(self, domain: str) -> dict[str, Any]:
        """Open the official setup flow of an integration."""
        result = await self.hass.config_entries.flow.async_init(
            domain, context={"source": SOURCE_USER}
        )
        return {
            "type": result.get("type"),
            "flow_id": result.get("flow_id"),
            "reason": result.get("reason"),
            "url": "/config/integrations",
        }

    async def async_acknowledge(self, device_id: str) -> bool:
        """Mark one device as handled."""
        changed = self.registry.acknowledge(device_id)
        if changed:
            await self._async_save()
            await self.async_dismiss_notification()
        return changed

    async def async_forget(self, device_id: str) -> bool:
        """Drop a device from the inventory."""
        removed = self.registry.remove(device_id)
        if removed:
            await self._async_save()
        return removed

    # ------------------------------------------------------------------ views

    def snapshot(self) -> dict[str, Any]:
        """Return the full inventory plus counters for the panel."""
        counts = {
            STATE_CONFIGURED: 0,
            STATE_AVAILABLE: 0,
            STATE_INSTALLABLE: 0,
            STATE_UNKNOWN: 0,
        }
        for record in self.registry.records.values():
            counts[record.state] = counts.get(record.state, 0) + 1

        records = sorted(
            self.registry.records.values(),
            key=lambda item: (-STATE_ORDER.get(item.state, 0), item.name.lower()),
        )
        return {
            "devices": [record.as_dict() for record in records],
            "counts": counts,
            "total": len(self.registry.records),
            "sources": self._sources,
            "scanning": self.scanning,
            "last_scan": self.last_scan,
        }

    def get_record(self, device_id: str) -> DeviceRecord | None:
        """Return one record by id."""
        return self.registry.get(device_id)


def async_get_hub(hass: HomeAssistant) -> DiscoveryHub | None:
    """Return the single running hub instance, if any."""
    store = hass.data.get("lan_discovery_hub")
    if not isinstance(store, dict):
        return None
    hubs = store.get("hubs") or {}
    return next(iter(hubs.values()), None)
