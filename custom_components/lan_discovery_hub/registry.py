"""Device aggregation.

The v0.1 integration keyed every record by ``service_type::instance name``, so
one physical device (an Apple TV with `_airplay`, `_raop` and `_companion-link`)
produced three entries and the "how many devices are on my LAN" number was
meaningless. This module merges observations into one record per device.

Identity is resolved with a priority order — MAC, then IP, then hostname, then
the announcing service — and every alias ever seen is kept in an index so that
a later observation through another protocol lands on the same record.

The module is deliberately free of Home Assistant imports so it can be unit
tested with plain Python.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import hashlib
import re
from typing import Any

MAC_RE = re.compile(r"^(?:[0-9a-f]{2}:){5}[0-9a-f]{2}$")
IPV4_RE = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")

# Device states, in ascending order of "the user should look at this".
STATE_CONFIGURED = "configured"  # a matching integration entry already exists
STATE_AVAILABLE = "available"  # matching integration is present and can be set up
STATE_INSTALLABLE = "installable"  # matching integration is third-party and missing
STATE_UNKNOWN = "unknown"  # nothing recognised the device

STATE_ORDER = {
    STATE_UNKNOWN: 0,
    STATE_INSTALLABLE: 1,
    STATE_AVAILABLE: 2,
    STATE_CONFIGURED: 3,
}


def normalize_mac(value: Any) -> str | None:
    """Return a lower-case ``aa:bb:cc:dd:ee:ff`` MAC, or None."""
    if not value or not isinstance(value, str):
        return None
    candidate = value.strip().lower().replace("-", ":")
    if MAC_RE.match(candidate):
        return candidate
    return None


def normalize_ip(value: Any) -> str | None:
    """Return a plausible IPv4 address, or None."""
    if not value or not isinstance(value, str):
        return None
    candidate = value.strip()
    if IPV4_RE.match(candidate):
        parts = [int(part) for part in candidate.split(".")]
        if all(0 <= part <= 255 for part in parts):
            return candidate
    return None


def normalize_host(value: Any) -> str | None:
    """Return a lower-case hostname without the trailing dot."""
    if not value or not isinstance(value, str):
        return None
    return value.strip().lower().rstrip(".") or None


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _stable_id(primary_alias: str) -> str:
    return hashlib.sha1(primary_alias.encode("utf-8")).hexdigest()[:12]


@dataclass(slots=True)
class Observation:
    """One sighting of a device through one protocol."""

    source: str
    kind: str
    detail: str
    name: str | None = None
    ip: str | None = None
    mac: str | None = None
    host: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    hint: str | None = None
    props: dict[str, Any] = field(default_factory=dict)

    @property
    def service_key(self) -> str:
        """Stable identifier of the announced service."""
        return f"{self.source}:{self.kind}:{self.detail}"

    def aliases(self) -> list[str]:
        """All identity keys this observation can be matched by."""
        out: list[str] = []
        mac = normalize_mac(self.mac)
        if mac:
            out.append(f"mac:{mac}")
        ip = normalize_ip(self.ip)
        if ip:
            out.append(f"ip:{ip}")
        host = normalize_host(self.host)
        if host:
            out.append(f"host:{host}")
        out.append(f"svc:{self.service_key}")
        return out


@dataclass(slots=True)
class ServiceRecord:
    """Bookkeeping for one announced service."""

    source: str
    kind: str
    detail: str
    props: dict[str, Any]
    first_seen: str
    last_seen: str

    @property
    def key(self) -> str:
        """Stable identifier."""
        return f"{self.source}:{self.kind}:{self.detail}"

    def as_dict(self) -> dict[str, Any]:
        """Serialize for storage."""
        return {
            "source": self.source,
            "kind": self.kind,
            "detail": self.detail,
            "props": dict(self.props),
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ServiceRecord:
        """Restore from storage."""
        return cls(
            source=data.get("source", ""),
            kind=data.get("kind", ""),
            detail=data.get("detail", ""),
            props=dict(data.get("props") or {}),
            first_seen=data.get("first_seen") or _now(),
            last_seen=data.get("last_seen") or _now(),
        )


@dataclass(slots=True)
class DeviceRecord:
    """One physical device, as seen through one or more protocols."""

    device_id: str
    name: str
    first_seen: str
    last_seen: str
    ip: str | None = None
    mac: str | None = None
    host: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    state: str = STATE_UNKNOWN
    domain: str | None = None
    integration_name: str | None = None
    repo: str | None = None
    match_source: str | None = None
    acknowledged: bool = False
    hints: set[str] = field(default_factory=set)
    services: dict[str, ServiceRecord] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        """Serialize for storage and for the websocket API."""
        return {
            "device_id": self.device_id,
            "name": self.name,
            "ip": self.ip,
            "mac": self.mac,
            "host": self.host,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "state": self.state,
            "domain": self.domain,
            "integration_name": self.integration_name,
            "repo": self.repo,
            "match_source": self.match_source,
            "acknowledged": self.acknowledged,
            "hints": sorted(self.hints),
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "services": {
                key: service.as_dict() for key, service in self.services.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeviceRecord:
        """Restore from storage."""
        record = cls(
            device_id=data["device_id"],
            name=data.get("name") or data["device_id"],
            first_seen=data.get("first_seen") or _now(),
            last_seen=data.get("last_seen") or _now(),
            ip=data.get("ip"),
            mac=data.get("mac"),
            host=data.get("host"),
            manufacturer=data.get("manufacturer"),
            model=data.get("model"),
            state=data.get("state", STATE_UNKNOWN),
            domain=data.get("domain"),
            integration_name=data.get("integration_name"),
            repo=data.get("repo"),
            match_source=data.get("match_source"),
            acknowledged=bool(data.get("acknowledged")),
            hints=set(data.get("hints") or []),
        )
        for key, service in (data.get("services") or {}).items():
            record.services[key] = ServiceRecord.from_dict(service)
        return record


class DeviceRegistry:
    """Holds device records and keeps the alias index in sync."""

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self.records: dict[str, DeviceRecord] = {}
        self._index: dict[str, str] = {}

    # ------------------------------------------------------------------ load

    def load(self, payload: Any) -> None:
        """Restore a registry from ``Store`` payload."""
        self.records = {}
        self._index = {}
        if not isinstance(payload, dict):
            return
        for raw in payload.get("devices") or []:
            try:
                record = DeviceRecord.from_dict(raw)
            except (KeyError, TypeError):
                continue
            self.records[record.device_id] = record
            self._reindex(record)

    def as_payload(self) -> dict[str, Any]:
        """Serialize for ``Store``."""
        return {"schema": 2, "devices": [r.as_dict() for r in self.records.values()]}

    # ------------------------------------------------------------------ index

    def _reindex(self, record: DeviceRecord) -> None:
        if record.mac:
            self._index[f"mac:{record.mac}"] = record.device_id
        if record.ip:
            self._index[f"ip:{record.ip}"] = record.device_id
        if record.host:
            self._index[f"host:{record.host}"] = record.device_id
        for service in record.services.values():
            self._index[f"svc:{service.key}"] = record.device_id

    # ------------------------------------------------------------------ upsert

    def upsert(self, observation: Observation) -> tuple[DeviceRecord, bool]:
        """Fold one observation into the registry.

        Returns the record plus a flag telling the caller whether this is a
        device it had not seen before.
        """
        now = _now()
        observation.mac = normalize_mac(observation.mac) or observation.mac
        observation.ip = normalize_ip(observation.ip) or observation.ip
        observation.host = normalize_host(observation.host) or observation.host

        aliases = observation.aliases()
        candidates = {
            self._index[alias] for alias in aliases if alias in self._index
        }
        candidates.discard(None)

        created = not candidates
        if created:
            record = DeviceRecord(
                device_id=_stable_id(aliases[0]),
                name=self._pick_name(observation, None),
                first_seen=now,
                last_seen=now,
            )
            self.records[record.device_id] = record
            target = record
        else:
            target = self._merge_candidates(candidates, observation)

        self._apply(target, observation, now)
        self._reindex(target)
        return target, created

    def _merge_candidates(
        self,
        candidates: set[str],
        observation: Observation,
    ) -> DeviceRecord:
        """Merge every candidate record into the strongest one."""
        records = [self.records[cid] for cid in candidates if cid in self.records]
        if not records:
            record = DeviceRecord(
                device_id=_stable_id(observation.aliases()[0]),
                name=self._pick_name(observation, None),
                first_seen=_now(),
                last_seen=_now(),
            )
            self.records[record.device_id] = record
            return record

        def rank(item: DeviceRecord) -> tuple[int, str]:
            # A record with a MAC is the strongest identity we can have; the
            # oldest record wins ties so history is preserved.
            return (0 if item.mac else 1, item.first_seen)

        target = sorted(records, key=rank)[0]
        for other in records:
            if other.device_id == target.device_id:
                continue
            self._absorb(target, other)
            # Every alias of the absorbed record must now point at the target.
            for alias, device_id in list(self._index.items()):
                if device_id == other.device_id:
                    self._index[alias] = target.device_id
            self.records.pop(other.device_id, None)
        return target

    def _absorb(self, target: DeviceRecord, other: DeviceRecord) -> None:
        """Copy everything useful from ``other`` into ``target``."""
        target.first_seen = min(target.first_seen, other.first_seen)
        target.last_seen = max(target.last_seen, other.last_seen)
        target.ip = target.ip or other.ip
        target.mac = target.mac or other.mac
        target.host = target.host or other.host
        target.manufacturer = target.manufacturer or other.manufacturer
        target.model = target.model or other.model
        target.hints |= other.hints
        target.services.update(other.services)
        target.acknowledged = target.acknowledged or other.acknowledged
        if STATE_ORDER[other.state] > STATE_ORDER.get(target.state, 0):
            target.state = other.state
            target.domain = other.domain or target.domain
            target.integration_name = other.integration_name or target.integration_name
            target.repo = other.repo or target.repo
            target.match_source = other.match_source or target.match_source

    def _apply(
        self, record: DeviceRecord, observation: Observation, now: str
    ) -> None:
        """Apply a single observation to ``record``."""
        record.last_seen = max(record.last_seen, now)
        if observation.mac:
            if record.mac and record.mac != observation.mac:
                # Same IP, conflicting MAC: believe the newest sighting, the
                # DHCP lease may simply have moved to another device.
                self._index.pop(f"mac:{record.mac}", None)
            record.mac = observation.mac
        if observation.ip:
            record.ip = observation.ip
        if observation.host:
            record.host = observation.host
        record.manufacturer = record.manufacturer or observation.manufacturer
        record.model = record.model or observation.model
        if observation.hint:
            record.hints.add(observation.hint)

        service = ServiceRecord(
            source=observation.source,
            kind=observation.kind,
            detail=observation.detail,
            props=dict(observation.props),
            first_seen=record.services[observation.service_key].first_seen
            if observation.service_key in record.services
            else now,
            last_seen=now,
        )
        record.services[service.key] = service

        chosen = self._pick_name(observation, record)
        if chosen:
            record.name = chosen

    @staticmethod
    def _pick_name(
        observation: Observation, record: DeviceRecord | None
    ) -> str:
        """Choose the most human friendly name available."""
        if observation.name and observation.name.strip():
            return observation.name.strip()
        if record is not None and record.name:
            return record.name
        if observation.host:
            return observation.host.split(".")[0]
        if observation.ip:
            return observation.ip
        return "未知设备"

    # ------------------------------------------------------------------ updates

    def set_match(
        self,
        device_id: str,
        *,
        state: str,
        domain: str | None,
        integration_name: str | None,
        repo: str | None,
        match_source: str | None,
    ) -> DeviceRecord | None:
        """Store the integration match decided by the matcher."""
        record = self.records.get(device_id)
        if record is None:
            return None
        record.state = state
        record.domain = domain
        record.integration_name = integration_name
        record.repo = repo
        record.match_source = match_source
        return record

    def acknowledge(self, device_id: str, acknowledged: bool = True) -> bool:
        """Mark a device as acknowledged by the user."""
        record = self.records.get(device_id)
        if record is None:
            return False
        record.acknowledged = acknowledged
        return True

    def remove(self, device_id: str) -> bool:
        """Drop a device and forget its aliases."""
        record = self.records.pop(device_id, None)
        if record is None:
            return False
        for alias, mapped in list(self._index.items()):
            if mapped == device_id:
                self._index.pop(alias, None)
        return True

    def get(self, device_id: str) -> DeviceRecord | None:
        """Return a record by id."""
        return self.records.get(device_id)
