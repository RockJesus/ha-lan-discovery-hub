"""Runtime hub: owns the scanners, the device registry and the guidance state."""

from __future__ import annotations

import asyncio
import ipaddress
from datetime import UTC, datetime, timedelta
import logging
from pathlib import Path
from typing import Any

from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.event import async_call_later, async_track_time_interval
from homeassistant.helpers.storage import Store

from .catalog import IntegrationCatalog
from .i18n import language_of, t
from .const import (
    CONF_FULL_SWEEP,
    CONF_IGNORED_DEVICES,
    CONF_IGNORED_TYPES,
    CONF_SCAN_INTERVAL,
    CONF_SOURCES,
    DEFAULT_FULL_SWEEP,
    DEFAULT_IGNORED_TYPES,
    NOISE_IP_NETWORKS,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SOURCES,
    EVENT_DEVICE_FOUND,
    EVENT_SCAN_FINISHED,
    EXTRA_MDNS_TYPES,
    PROBE_PORTS,
    SOURCE_ARP,
    SOURCE_BLE,
    SOURCE_MDNS,
    SOURCE_MQTT,
    SOURCE_PROBE,
    SOURCE_SERIAL,
    SOURCE_SSDP,
    SSDP_TARGETS,
    STORAGE_KEY,
    STORAGE_VERSION,
    SWEEP_PORTS,
)
from .matcher import IntegrationMatcher, Match
from .registry import (
    STATE_AVAILABLE,
    STATE_CONFIGURED,
    STATE_INSTALLABLE,
    STATE_ORDER,
    STATE_UNKNOWN,
    DeviceRecord,
    DeviceRegistry,
    Observation,
    vendor_for_mac,
)
from .scanners.ble import BleScanner
from .scanners.mdns import MdnsScanner
from .scanners.mqtt import MqttScanner, is_configured as _mqtt_configured
from .scanners.serial import SerialScanner
from .scanners.probe import (
    async_probe_ips,
    async_sweep_subnet,
    local_prefix,
    read_arp_cache,
)
from .scanners.ssdp import SsdpScanner

_LOGGER = logging.getLogger(__name__)


def is_noise_ip(ip: str | None) -> bool:
    """Return True when the address belongs to the HA container, not the LAN."""
    if not ip:
        return False
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(address in ipaddress.ip_network(net) for net in NOISE_IP_NETWORKS)


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
        self.catalog = IntegrationCatalog(hass)
        self.matcher = IntegrationMatcher(hass.config.config_dir)
        self.store: Store = Store(hass, STORAGE_VERSION, STORAGE_KEY)

        self._mdns: MdnsScanner | None = None
        self._ssdp: SsdpScanner | None = None
        self._ble: BleScanner | None = None
        self._mqtt: MqttScanner | None = None
        self._serial: SerialScanner | None = None
        self._unsub_interval: Any = None
        self._unsub_first_scan: Any = None
        self._save_unsub: Any = None
        self._notify_unsub: Any = None
        self._scan_lock = asyncio.Lock()

        self._installed_domains: set[str] = set()
        self._sources = list(options.get(CONF_SOURCES, DEFAULT_SOURCES))
        self._interval = max(
            60, int(options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
        )
        self._ignored_types = [
            str(item).lower()
            for item in options.get(CONF_IGNORED_TYPES, DEFAULT_IGNORED_TYPES)
        ]
        self._ignored_devices = set(options.get(CONF_IGNORED_DEVICES, []))
        # Every fingerprint this device has ever shown, keyed by device_id then
        # domain. A device that advertises several protocols is decided on the
        # strongest evidence rather than on whichever packet arrived first.
        self._match_votes: dict[str, dict[str, dict[str, object]]] = {}
        self._full_sweep = bool(options.get(CONF_FULL_SWEEP, DEFAULT_FULL_SWEEP))

        self.scanning = False
        self.last_scan: str | None = None

    # ------------------------------------------------------------------ live

    async def async_start(self) -> None:
        """Load stored devices, the catalog, and start every enabled scanner."""
        # The catalog is what turns evidence into a suggestion; load it before
        # the first scan so the very first render already has candidates.
        await self.catalog.async_load()
        self.matcher.set_language(language_of(self.hass))
        await self.matcher.async_load_maps(self.hass)
        # Directory walking and the 45k-line OUI table are blocking I/O: keep
        # both off the event loop.
        self._installed_domains = await self.hass.async_add_executor_job(
            _installed_domains, self.hass
        )
        self._oui_ready = await self.hass.async_add_executor_job(
            vendor_for_mac, "00:00:00"
        )
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

        if SOURCE_BLE in self._sources:
            self._ble = BleScanner(self.hass, self._async_on_observation)
            await self._ble.async_start()

        if SOURCE_MQTT in self._sources:
            self._mqtt = MqttScanner(self.hass, self._async_on_observation)
            await self._mqtt.async_start()

        if SOURCE_SERIAL in self._sources:
            self._serial = SerialScanner(self.hass, self._async_on_observation)
            await self._serial.async_start()

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

        if self._ble is not None:
            await self._ble.async_stop()
            self._ble = None

        if self._mqtt is not None:
            await self._mqtt.async_stop()
            self._mqtt = None

        if self._serial is not None:
            await self._serial.async_stop()
            self._serial = None

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
            self._async_backfill_evidence()

    def _async_backfill_evidence(self) -> None:
        """Label pre-0.7.0 matches instead of showing a suggestion with no reason.

        Those records were resolved before evidence was stored; the fingerprint
        that produced them may no longer be broadcast, so they are marked as
        pending rather than invented.
        """
        for record in self.registry.records.values():
            if record.domain and not record.match_evidence:
                record.match_evidence = t(self.hass, "evidence.history")

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
                # Our entry can be set up before the mqtt/bluetooth integrations
                # finish; retry each round instead of staying dead until restart.
                if self._mqtt is not None and not self._mqtt.available:
                    await self._mqtt.async_start()
                if self._ble is not None and not self._ble.available:
                    await self._ble.async_start()
                if self._serial is not None and not self._serial.available:
                    await self._serial.async_start()
                if SOURCE_ARP in self._sources or SOURCE_PROBE in self._sources:
                    await self._async_collect_arp()
                if self._ssdp is not None:
                    await self._ssdp.async_scan()
                if full or self._full_sweep:
                    await self._async_sweep_subnet()
                if SOURCE_PROBE in self._sources:
                    await self._async_probe_known()
                await self._async_collect_ble()
                await self._async_collect_mqtt()
                await self._async_collect_serial()
                self._async_prune_channels()
            except Exception as err:  # noqa: BLE001 - a broken channel must not kill the loop
                _LOGGER.exception("扫描出错: %s", err)
            finally:
                self.scanning = False
                self.last_scan = _utcnow()

        self.registry.normalize_names()
        removed = self.registry.drop_noise(is_noise_ip)
        if removed:
            _LOGGER.debug("已清理容器网络地址记录 %s 条", len(removed))

        await self._async_save()
        self.hass.bus.async_fire(
            EVENT_SCAN_FINISHED, {"devices": len(self.registry.records)}
        )
        # A device found before a restart should still be surfaced once HA is
        # back up, otherwise the ledger stays silent until something new shows
        # up. The same notification id means this updates rather than stacks.
        self._schedule_notification()

    async def _async_collect_serial(self) -> None:
        """Feed serial/USB adapters mapped into the container."""
        if self._serial is None:
            return
        # SerialScanner.snapshot() reads /dev and /sys: run it off the loop.
        observations = await self.hass.async_add_executor_job(self._serial.snapshot)
        for observation in observations:
            await self._async_on_observation(observation)

    def _async_prune_channels(self) -> None:
        """Forget records that only a push channel ever saw and that channel dropped."""
        for scanner, source in (
            (self._ble, SOURCE_BLE),
            (self._mqtt, SOURCE_MQTT),
            (self._serial, SOURCE_SERIAL),
        ):
            if scanner is None or not scanner.available:
                continue
            removed = self.registry.drop_source_only(source, scanner.active_keys())
            if removed:
                _LOGGER.debug("%s 通道已消失 %s 条记录", source, len(removed))

    async def _async_collect_ble(self) -> None:
        """Feed BLE advertisements from the shared bluetooth cache."""
        if self._ble is None:
            return
        for observation in self._ble.snapshot():
            await self._async_on_observation(observation)

    async def _async_collect_mqtt(self) -> None:
        """Feed devices announced on the broker."""
        if self._mqtt is None:
            return
        for observation in self._mqtt.snapshot():
            identifiers = observation.props.get("identifiers") or []
            if _mqtt_configured(self.hass, identifiers):
                observation.props["configured"] = True
            await self._async_on_observation(observation)

    async def _async_collect_arp(self) -> None:
        cache = await self.hass.async_add_executor_job(read_arp_cache)
        if not cache:
            _LOGGER.debug("没有可用的 ARP 邻居缓存")
            return
        for ip, mac in cache.items():
            if is_noise_ip(ip):
                continue
            await self._async_on_observation(
                Observation(
                    source=SOURCE_ARP,
                    kind="neighbor",
                    detail=ip,
                    ip=ip,
                    mac=mac,
                    hint="arp",
                )
            )

    async def _async_probe_known(self) -> None:
        targets = [
            record.ip
            for record in list(self.registry.records.values())
            if record.ip and not is_noise_ip(record.ip)
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
                    detail=ip,
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
                    detail=ip,
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
        """Fold one fingerprint into the device's evidence set and decide."""
        match = self.matcher.resolve(observation)
        if match is None or not match.domain:
            return

        votes = self._match_votes.setdefault(record.device_id, {})
        entry = votes.get(match.domain)
        if entry is None:
            votes[match.domain] = {
                "match": match,
                "sources": {observation.source},
            }
        else:
            sources = entry["sources"]
            assert isinstance(sources, set)
            sources.add(observation.source)
            current = entry["match"]
            assert isinstance(current, Match)
            # A service type beats a port hint, even if the port arrived first.
            if current.confidence != "exact" and match.confidence == "exact":
                entry["match"] = match

        configured = bool(observation.props.get("configured")) or (
            self._async_is_device_configured(record)
        )

        ranked: list[tuple[tuple[int, int, int], str, Match, str, int]] = []
        for domain, candidate in votes.items():
            matched = candidate["match"]
            assert isinstance(matched, Match)
            sources = candidate["sources"]
            assert isinstance(sources, set)
            if configured:
                state = STATE_CONFIGURED
            elif self.matcher.integration_present(self.hass, domain):
                state = STATE_AVAILABLE
            elif matched.confidence == "exact":
                state = STATE_INSTALLABLE
            else:
                # A port is not enough to tell the owner to install something.
                state = STATE_UNKNOWN
            rank = (
                0 if matched.confidence == "exact" else 1,
                -STATE_ORDER.get(state, 0),
                -len(sources),
            )
            ranked.append((rank, domain, matched, state, len(sources)))

        if not ranked:
            return
        ranked.sort(key=lambda item: item[0])
        _, domain, matched, state, support = ranked[0]
        if state == STATE_UNKNOWN and record.domain != domain:
            # Keep the earlier, more actionable answer instead of replacing it
            # with a guess that cannot be acted on.
            return

        if (
            record.domain == domain
            and record.state == state
            and record.match_support == support
        ):
            return

        display = matched.integration or self.matcher.display_name(
            self.hass, domain
        )
        if matched.confidence != "exact":
            display = t(self.hass, "guess.prefix", name=display or domain)
        self.registry.set_match(
            record.device_id,
            state=state,
            domain=domain,
            integration_name=display,
            repo=matched.repo,
            match_source=matched.source,
            match_evidence=matched.evidence or None,
            match_support=support,
        )

    def _async_is_device_configured(self, record: DeviceRecord) -> bool:
        """Whether an existing device registry entry already covers this device."""
        registry = dr.async_get(self.hass)
        for device in registry.devices:
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

        self.registry.normalize_names()
        actionable = [
            record
            for record in self.registry.records.values()
            if not record.acknowledged
            and not record.ignored
            and record.state in ACTIONABLE_STATES
        ]
        if not actionable:
            return

        actionable.sort(key=lambda item: (STATE_ORDER[item.state], item.name.lower()))
        lines = []
        for record in actionable[:8]:
            integration = record.integration_name or record.domain or t(
                self.hass, "unknown.integration"
            )
            where = record.ip or record.mac or t(self.hass, "unknown.address")
            lines.append(
                t(
                    self.hass,
                    "notify.line",
                    name=record.name,
                    where=where,
                    integration=integration,
                )
            )
        if len(actionable) > 8:
            lines.append(t(self.hass, "notify.more", count=len(actionable) - 8))

        message = t(
            self.hass,
            "notify.body",
            count=len(actionable),
            lines="\n".join(lines),
        )
        try:
            persistent_notification.async_create(
                self.hass,
                message,
                title=t(self.hass, "notify.title"),
                notification_id=NOTIFICATION_ID,
            )
        except Exception as err:  # noqa: BLE001 - notification is best effort
            _LOGGER.debug("创建通知失败: %s", err)

    async def async_dismiss_notification(self) -> None:
        """Remove the summary notification once nothing needs attention."""
        remaining = [
            record
            for record in self.registry.records.values()
            if not record.acknowledged
            and not record.ignored
            and record.state in ACTIONABLE_STATES
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

    async def async_rename(self, device_id: str, name: str | None) -> bool:
        """Pin a user-chosen name to a device and persist it."""
        changed = self.registry.rename(device_id, name)
        if not name:
            # Clearing the override means "back to automatic naming": recompute
            # now, otherwise the old typed name lingers until the next scan.
            self.registry.normalize_names()
        if changed:
            await self._async_save()
            self._async_notify()
        return changed

    async def async_acknowledge(self, device_id: str) -> bool:
        """Mark one device as handled."""
        changed = self.registry.acknowledge(device_id)
        if changed:
            await self._async_save()
            await self.async_dismiss_notification()
        return changed

    async def async_forget(self, device_id: str) -> bool:
        """Hide a device from the panel for good (it stays tracked internally)."""
        changed = self.registry.ignore(device_id)
        if changed:
            await self._async_save()
            self._async_notify()
        return changed

    async def async_restore(self, device_id: str) -> bool:
        """Bring an ignored device back into the panel."""
        changed = self.registry.ignore(device_id, False)
        if changed:
            await self._async_save()
            self._async_notify()
        return changed

    # ------------------------------------------------------------------ views

    def snapshot(self, include_ignored: bool = False) -> dict[str, Any]:
        """Return the full inventory plus counters for the panel."""
        visible = [
            record
            for record in self.registry.records.values()
            if include_ignored or not record.ignored
        ]
        counts = {
            STATE_CONFIGURED: 0,
            STATE_AVAILABLE: 0,
            STATE_INSTALLABLE: 0,
            STATE_UNKNOWN: 0,
        }
        for record in visible:
            counts[record.state] = counts.get(record.state, 0) + 1

        records = sorted(
            visible,
            key=lambda item: (-STATE_ORDER.get(item.state, 0), item.name.lower()),
        )
        payload = []
        for record in records:
            item = record.as_dict(language_of(self.hass))
            try:
                item["suggestions"] = self.catalog.suggest(
                    record, self._installed_domains, language_of(self.hass)
                )
            except Exception as err:  # noqa: BLE001 - a suggestion never breaks a render
                _LOGGER.debug("生成集成建议失败 %s: %s", record.name, err)
                item["suggestions"] = []
            payload.append(item)

        return {
            "catalog": self.catalog.info(),
            "devices": payload,
            "counts": counts,
            "total": len(visible),
            "ignored_count": sum(1 for r in self.registry.records.values() if r.ignored),
            "sources": self._sources,
            "channels": {
                "mdns": {
                    "available": self._mdns is not None,
                    "reason": None
                    if self._mdns is not None
                    else t(self.hass, "channel.disabled"),
                    "types": getattr(self._mdns, "type_count", 0),
                },
                "ble": {
                    "available": bool(self._ble and self._ble.available),
                    "reason": self._ble.reason if self._ble else t(self.hass, "channel.disabled"),
                },
                "mqtt": {
                    "available": bool(self._mqtt and self._mqtt.available),
                    "reason": self._mqtt.reason if self._mqtt else t(self.hass, "channel.disabled"),
                },
                "serial": {
                    "available": bool(self._serial and self._serial.available),
                    "reason": self._serial.reason if self._serial else t(self.hass, "channel.disabled"),
                },
            },
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


def _installed_domains(hass: Any) -> set[str]:
    """Domains that exist in this installation, core or custom."""
    domains: set[str] = set()
    try:
        import homeassistant  # noqa: PLC0415

        core = Path(homeassistant.__file__).parent / "components"
        domains.update(entry.name for entry in core.iterdir() if entry.is_dir())
    except (ImportError, OSError):  # pragma: no cover
        pass
    try:
        custom = Path(hass.config.config_dir) / "custom_components"
        domains.update(entry.name for entry in custom.iterdir() if entry.is_dir())
    except (AttributeError, OSError):  # pragma: no cover
        pass
    return domains
