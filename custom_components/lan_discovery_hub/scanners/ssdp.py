"""SSDP / UPnP scanning.

We only send active ``M-SEARCH`` requests and never bind UDP 1900: Home
Assistant's own ``ssdp`` integration already owns that multicast socket and
fighting over it is fragile across platforms. An active search per scan
interval still yields a full UPnP inventory.
"""

from __future__ import annotations

import asyncio
import logging
import socket
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..const import SOURCE_SSDP
from ..registry import Observation, normalize_ip

_LOGGER = logging.getLogger(__name__)

SSDP_ADDR = ("239.255.255.250", 1900)
SEARCH_TIMEOUT = 4.0
MAX_DESCRIPTION_FETCH = 24
FETCH_CONCURRENCY = 6
MAX_DESCRIPTION_BYTES = 200_000

_XML_FIELDS = {
    "friendlyname": "friendly_name",
    "modelname": "model",
    "modelnumber": "model_number",
    "manufacturer": "manufacturer",
    "devicetype": "device_type",
}


def _parse_headers(payload: bytes) -> dict[str, str]:
    """Parse a SSDP response/notify header block."""
    text = payload.decode("utf-8", "replace")
    lines = text.replace("\r\n", "\n").split("\n")
    headers: dict[str, str] = {}
    for line in lines[1:]:
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        if key:
            headers[key] = value.strip()
    return headers


def _find_text(root: Any, local_name: str) -> str | None:
    """Find a text value by local tag name, ignoring XML namespaces."""
    for element in root.iter():
        tag = element.tag
        if not isinstance(tag, str):
            continue
        if tag.split("}")[-1].lower() == local_name:
            text = (element.text or "").strip()
            if text:
                return text
    return None


class SsdpScanner:
    """Discovers UPnP devices through an active search."""

    def __init__(
        self,
        hass: HomeAssistant,
        on_observation: Any,
        targets: tuple[str, ...] | list[str],
    ) -> None:
        """Initialize the scanner."""
        self.hass = hass
        self._on_observation = on_observation
        self._targets = list(targets)

    async def async_scan(self) -> int:
        """Run one search round and return the number of devices seen."""
        loop = asyncio.get_running_loop()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setblocking(False)
        except OSError as err:
            _LOGGER.warning("无法创建 SSDP socket: %s", err)
            return 0

        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        except OSError as err:  # pragma: no cover - platform dependent
            _LOGGER.debug("设置 SSDP socket 选项失败: %s", err)
        try:
            sock.bind(("", 0))
        except OSError as err:
            _LOGGER.warning("绑定 SSDP socket 失败: %s", err)
            sock.close()
            return 0

        responses: dict[tuple[str, str], dict[str, str]] = {}
        try:
            for target in self._targets:
                message = (
                    "M-SEARCH * HTTP/1.1\r\n"
                    f"HOST: {SSDP_ADDR[0]}:{SSDP_ADDR[1]}\r\n"
                    'MAN: "ssdp:discover"\r\n'
                    "MX: 2\r\n"
                    f"ST: {target}\r\n"
                    "\r\n"
                ).encode("ascii")
                try:
                    await loop.sock_sendto(sock, message, SSDP_ADDR)
                except OSError as err:
                    _LOGGER.debug("发送 SSDP 搜索失败 (%s): %s", target, err)

            deadline = loop.time() + SEARCH_TIMEOUT
            while (remaining := deadline - loop.time()) > 0:
                try:
                    data, addr = await asyncio.wait_for(
                        loop.sock_recvfrom(sock, 4096), remaining
                    )
                except (TimeoutError, asyncio.TimeoutError):
                    break
                except OSError as err:
                    _LOGGER.debug("接收 SSDP 响应失败: %s", err)
                    break
                headers = _parse_headers(data)
                if not headers:
                    continue
                ip = normalize_ip(addr[0])
                if not ip:
                    continue
                usn = headers.get("usn") or headers.get("st") or headers.get("nt")
                if not usn:
                    continue
                responses.setdefault((ip, usn), headers)
        finally:
            sock.close()

        if not responses:
            return 0

        # Fetch the device description in parallel, but only for a bounded
        # number of devices: a hostile or slow device must not stall the scan.
        items = list(responses.items())[:MAX_DESCRIPTION_FETCH]
        semaphore = asyncio.Semaphore(FETCH_CONCURRENCY)

        async def _enrich(headers: dict[str, str]) -> dict[str, str]:
            location = headers.get("location")
            if not location:
                return {}
            async with semaphore:
                return await self._async_fetch_description(location)

        descriptions = await asyncio.gather(
            *(_enrich(headers) for _, headers in items), return_exceptions=True
        )

        count = 0
        for ((ip, usn), headers), extra in zip(items, descriptions, strict=False):
            if isinstance(extra, BaseException):
                extra = {}
            extra = dict(extra or {})
            headers = {**headers, **extra}
            await self._dispatch(ip, usn, headers)
            count += 1

        _LOGGER.debug("SSDP 扫描完成，发现 %s 台设备", count)
        return count

    async def _async_fetch_description(self, location: str) -> dict[str, str]:
        """Fetch and parse the UPnP device description XML."""
        if not location.startswith(("http://", "https://")):
            return {}
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(
                location,
                timeout=aiohttp.ClientTimeout(total=2),
                allow_redirects=False,
            ) as resp:
                if resp.status != 200:
                    return {}
                raw = await resp.content.read(MAX_DESCRIPTION_BYTES)
        except (aiohttp.ClientError, TimeoutError, asyncio.TimeoutError, ValueError):
            return {}
        except Exception as err:  # noqa: BLE001 - unparseable location must not fail
            _LOGGER.debug("读取 UPnP 描述失败 %s: %s", location, err)
            return {}

        try:
            from defusedxml.ElementTree import fromstring  # noqa: PLC0415
        except ImportError:  # pragma: no cover - defusedxml ships with HA
            from xml.etree.ElementTree import fromstring  # noqa: PLC0415

        try:
            root = fromstring(raw)
        except Exception as err:  # noqa: BLE001 - third party XML may be broken
            _LOGGER.debug("解析 UPnP 描述失败 %s: %s", location, err)
            return {}

        out: dict[str, str] = {}
        for xml_name, key in _XML_FIELDS.items():
            value = _find_text(root, xml_name)
            if value:
                out[key] = value
        return out

    async def _dispatch(
        self, ip: str, usn: str, headers: dict[str, str]
    ) -> None:
        """Turn one SSDP response into an observation."""
        st = headers.get("st") or headers.get("nt") or "ssdp"
        friendly = headers.get("friendly_name")
        name = friendly or headers.get("model") or ""
        if not name:
            server = headers.get("server") or ""
            name = f"UPnP {server.split(' ')[-1]}" if server else ""
        observation = Observation(
            source=SOURCE_SSDP,
            kind=st,
            detail=usn,
            name=name or None,
            ip=ip,
            manufacturer=headers.get("manufacturer"),
            model=headers.get("model") or headers.get("model_number"),
            hint="upnp",
            unique_instance=True,
            props={
                "server": headers.get("server"),
                "location": headers.get("location"),
                "device_type": headers.get("device_type"),
                "friendly_name": friendly,
                "manufacturer": headers.get("manufacturer"),
                "model": headers.get("model"),
            },
        )
        result = self._on_observation(observation)
        if asyncio.iscoroutine(result):
            await result
