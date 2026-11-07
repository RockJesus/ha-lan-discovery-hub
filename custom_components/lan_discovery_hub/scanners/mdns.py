"""mDNS scanning on top of Home Assistant's shared zeroconf instance.

Using the shared instance keeps a single mDNS responder/listener in the
process, which is what HA itself does. We browse an explicit list of service
types (the generated core table plus a handful of extras) instead of ``None``
so a noisy network does not turn into an unbounded flood of browsers.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.core import HomeAssistant, callback

from ..const import SOURCE_MDNS
from ..registry import Observation, normalize_ip, normalize_mac

_LOGGER = logging.getLogger(__name__)

MAC_TXT_KEYS = ("mac", "macaddress", "mac_address", "hwaddr", "device_mac", "mid")
RESOLVE_TIMEOUT_MS = 2500


class MdnsScanner:
    """Browses mDNS service types and turns announcements into observations."""

    def __init__(
        self,
        hass: HomeAssistant,
        on_observation: Any,
        service_types: list[str],
        ignored_types: list[str],
    ) -> None:
        """Initialize the scanner."""
        self.hass = hass
        self._on_observation = on_observation
        self._service_types = service_types
        self._ignored = {str(item).lower() for item in ignored_types}
        self._browser: Any = None
        self._zeroconf: Any = None
        self._inflight: set[tuple[str, str]] = set()

    async def async_start(self) -> None:
        """Start browsing."""
        from homeassistant.components.zeroconf import async_get_instance  # noqa: PLC0415
        from zeroconf.asyncio import AsyncServiceBrowser  # noqa: PLC0415

        self._zeroconf = await async_get_instance(self.hass)
        types = list(self._service_types) or None

        @callback
        def _on_service_state_change(
            *, zeroconf: Any, service_type: str, name: str, state_change: Any
        ) -> None:
            """Handle any browser callback (signature is fixed by zeroconf)."""
            if state_change not in ("added", "updated") and not str(
                state_change
            ).endswith(("Added", "Updated")):
                return
            self.hass.async_create_task(
                self._async_handle_service(service_type, name)
            )

        self._browser = AsyncServiceBrowser(
            self._zeroconf, types, handlers=[_on_service_state_change]
        )
        _LOGGER.debug("mDNS 浏览已启动，service types: %s", len(types or []))

    async def async_stop(self) -> None:
        """Stop browsing and release the browser."""
        if self._browser is not None:
            try:
                await self._browser.async_cancel()
            except Exception as err:  # noqa: BLE001 - best effort shutdown
                _LOGGER.debug("关闭 mDNS 浏览器失败: %s", err)
            self._browser = None

    async def _async_handle_service(self, service_type: str, name: str) -> None:
        """Resolve one announcement and hand it to the hub."""
        if service_type.lower() in self._ignored:
            return
        key = (service_type, name)
        if key in self._inflight:
            return
        self._inflight.add(key)
        try:
            from zeroconf.asyncio import AsyncServiceInfo  # noqa: PLC0415

            info = AsyncServiceInfo(service_type, name)
            if self._zeroconf is None:
                return
            if not await info.async_request(
                self._zeroconf, RESOLVE_TIMEOUT_MS
            ):
                _LOGGER.debug("mDNS 解析超时: %s", name)
                return

            props = _decode_properties(getattr(info, "properties", None))
            ip = _first_ipv4(info)
            mac = _mac_from_props(props)
            label = _instance_label(name, service_type)
            hint = _hint_for(service_type)
            model = props.get("model") or props.get("md") or props.get("am")

            await self._dispatch(
                Observation(
                    source=SOURCE_MDNS,
                    kind=service_type,
                    detail=label,
                    name=_unescape(label) or label,
                    ip=ip,
                    mac=mac,
                    host=getattr(info, "server", None),
                    model=model,
                    hint=hint,
                    props=props,
                    unique_instance=True,
                )
            )
        except Exception as err:  # noqa: BLE001 - one bad device must not stop the scan
            _LOGGER.debug("处理 mDNS 公告失败 %s: %s", name, err)
        finally:
            self._inflight.discard(key)

    async def _dispatch(self, observation: Observation) -> None:
        result = self._on_observation(observation)
        if asyncio.iscoroutine(result):
            await result


def _decode_properties(raw: Any) -> dict[str, str]:
    """Decode the TXT record into plain strings."""
    out: dict[str, str] = {}
    if not isinstance(raw, dict):
        return out
    for key, value in raw.items():
        key_str = key.decode("utf-8", "replace") if isinstance(key, bytes) else str(key)
        if value is None:
            out[key_str] = ""
        elif isinstance(value, bytes):
            out[key_str] = value.decode("utf-8", "replace")
        else:
            out[key_str] = str(value)
    return out


def _first_ipv4(info: Any) -> str | None:
    """Return the first IPv4 address of the resolved service."""
    addresses: list[str] = []
    parsed = getattr(info, "parsed_addresses", None)
    if callable(parsed):
        try:
            addresses = list(parsed())
        except (AttributeError, TypeError):  # pragma: no cover
            addresses = []
    if not addresses:
        for raw in getattr(info, "addresses", None) or []:
            if isinstance(raw, bytes):
                addresses.append(".".join(str(part) for part in raw))
    for address in addresses:
        normalized = normalize_ip(address)
        if normalized:
            return normalized
    return None


def _mac_from_props(props: dict[str, str]) -> str | None:
    """Some devices publish their MAC in the TXT record."""
    for key, value in props.items():
        if key.lower() in MAC_TXT_KEYS:
            mac = normalize_mac(value)
            if mac:
                return mac
    return None


def _instance_label(name: str, service_type: str) -> str:
    """Strip the service suffix from the full DNS name."""
    suffix = f".{service_type}"
    if name.endswith(suffix):
        return name[: -len(suffix)]
    marker = f".{service_type}"
    index = name.find(marker)
    if index > 0:
        return name[:index]
    return name


def _unescape(label: str) -> str:
    """Undo the escaping mDNS applies to instance names."""
    return (
        label.replace("\\032", " ")
        .replace("\\(", "(")
        .replace("\\)", ")")
        .replace("\\\\", "\\")
    )


def _hint_for(service_type: str) -> str:
    """Turn ``_airplay._tcp.local.`` into ``airplay``."""
    first = service_type.split(".")[0]
    return first.strip("_").replace("_", "-")
