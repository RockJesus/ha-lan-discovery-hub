"""What is this device, actually?

Discovery alone proves that *something* answers at an address. This module
turns the raw sightings into a human identity: a device class (TV, NAS,
printer, router, camera, speaker, …) plus nickname/model evidence, and — when
the device is willing to talk — a hostname and the title of its web UI.

Every source is optional. Nothing here is guessed silently: an unknown device
stays unknown instead of being labelled "router" for having port 80 open.
"""

from __future__ import annotations

import asyncio
import logging
import re
import socket
import time
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

KIND_TV = "tv"
KIND_MEDIA = "media_player"
KIND_SPEAKER = "speaker"
KIND_NAS = "nas"
KIND_PRINTER = "printer"
KIND_ROUTER = "router"
KIND_CAMERA = "camera"
KIND_COMPUTER = "computer"
KIND_PHONE = "phone"
KIND_TABLET = "tablet"
KIND_IOT = "iot"
KIND_HUB = "hub"
KIND_SERVER = "server"
KIND_APPLIANCE = "appliance"

# Ports that reliably say something about the device class *on their own*.
PORT_KINDS: dict[int, str] = {
    9100: KIND_PRINTER,
    631: KIND_PRINTER,
    515: KIND_PRINTER,
    554: KIND_CAMERA,
    8554: KIND_CAMERA,
    37777: KIND_CAMERA,
    445: KIND_NAS,
    548: KIND_NAS,
    2049: KIND_NAS,
    32400: KIND_MEDIA,
    8200: KIND_MEDIA,
    8009: KIND_MEDIA,
    7000: KIND_MEDIA,
    8123: KIND_HUB,
    1883: KIND_IOT,
    22: KIND_COMPUTER,
    3389: KIND_COMPUTER,
    5900: KIND_COMPUTER,
}

# mDNS service types: a strong signal because the device itself announced it.
MDNS_KINDS: tuple[tuple[str, str], ...] = (
    ("_airplay", KIND_MEDIA),
    ("_raop", KIND_SPEAKER),
    ("_googlecast", KIND_MEDIA),
    ("_spotify-connect", KIND_SPEAKER),
    ("_sonos", KIND_SPEAKER),
    ("_ipp", KIND_PRINTER),
    ("_printer", KIND_PRINTER),
    ("_pdl-datastream", KIND_PRINTER),
    ("_rtsp", KIND_CAMERA),
    ("_camera", KIND_CAMERA),
    ("_smb", KIND_NAS),
    ("_afpovertcp", KIND_NAS),
    ("_nfs", KIND_NAS),
    ("_device-info", KIND_COMPUTER),
    ("_ssh", KIND_COMPUTER),
    ("_rdp", KIND_COMPUTER),
    ("_workstation", KIND_COMPUTER),
    ("_companion-link", KIND_PHONE),
    ("_homekit", KIND_IOT),
    ("_hap", KIND_IOT),
    ("_matter", KIND_IOT),
    ("_esphome", KIND_IOT),
    ("_hue", KIND_IOT),
    ("_tradfri", KIND_IOT),
    ("_miio", KIND_IOT),
    ("_ewelink", KIND_IOT),
    ("_aqara", KIND_IOT),
    ("_coap", KIND_IOT),
)

# UPnP device types are equally explicit.
SSDP_KINDS: tuple[tuple[str, str], ...] = (
    ("internetgatewaydevice", KIND_ROUTER),
    ("wanconnectiondevice", KIND_ROUTER),
    ("wancfg", KIND_ROUTER),
    ("mediarenderer", KIND_MEDIA),
    ("mediaserver", KIND_MEDIA),
    ("printer", KIND_PRINTER),
    ("scanner", KIND_PRINTER),
    ("camera", KIND_CAMERA),
)

# Vendor prefixes: only used when no protocol told us what the device is.
VENDOR_KINDS: tuple[tuple[str, str], ...] = (
    ("synology", KIND_NAS),
    ("qnap", KIND_NAS),
    ("ugreen", KIND_NAS),
    ("terramaster", KIND_NAS),
    ("western digital", KIND_NAS),
    ("asustor", KIND_NAS),
    ("brother", KIND_PRINTER),
    ("canon", KIND_PRINTER),
    ("epson", KIND_PRINTER),
    ("ricoh", KIND_PRINTER),
    ("kyocera", KIND_PRINTER),
    ("dahua", KIND_CAMERA),
    ("hikvision", KIND_CAMERA),
    ("uniview", KIND_CAMERA),
    ("reolink", KIND_CAMERA),
    ("ezviz", KIND_CAMERA),
    ("xiaomi", KIND_IOT),
    ("haier", KIND_APPLIANCE),
    ("midea", KIND_APPLIANCE),
    ("gree", KIND_APPLIANCE),
    ("roborock", KIND_APPLIANCE),
    ("ecovacs", KIND_APPLIANCE),
    ("dreame", KIND_APPLIANCE),
    ("espressif", KIND_IOT),
    ("tuya", KIND_IOT),
    ("sonoff", KIND_IOT),
    ("shelly", KIND_IOT),
    ("tenda", KIND_ROUTER),
    ("netgear", KIND_ROUTER),
    ("tp-link", KIND_ROUTER),
    ("d-link", KIND_ROUTER),
    ("ruijie", KIND_ROUTER),
    ("h3c", KIND_ROUTER),
)

# Words in the model or web UI title that name the class outright.
TEXT_KINDS: tuple[tuple[str, str], ...] = (
    ("路由器", KIND_ROUTER),
    ("router", KIND_ROUTER),
    ("gateway", KIND_ROUTER),
    ("access point", KIND_ROUTER),
    ("无线", KIND_ROUTER),
    ("摄像头", KIND_CAMERA),
    ("摄像机", KIND_CAMERA),
    ("camera", KIND_CAMERA),
    ("ipc", KIND_CAMERA),
    ("打印机", KIND_PRINTER),
    ("printer", KIND_PRINTER),
    ("mfp", KIND_PRINTER),
    ("电视", KIND_TV),
    ("tv", KIND_TV),
    ("bravia", KIND_TV),
    ("电视盒子", KIND_MEDIA),
    ("机顶盒", KIND_MEDIA),
    ("投影", KIND_MEDIA),
    ("投影仪", KIND_MEDIA),
    ("projector", KIND_MEDIA),
    ("nas", KIND_NAS),
    ("网络存储", KIND_NAS),
    ("群晖", KIND_NAS),
    ("音响", KIND_SPEAKER),
    ("音箱", KIND_SPEAKER),
    ("speaker", KIND_SPEAKER),
    ("soundbar", KIND_SPEAKER),
    ("扫地机", KIND_APPLIANCE),
    ("冰箱", KIND_APPLIANCE),
    ("空调", KIND_APPLIANCE),
    ("洗衣机", KIND_APPLIANCE),
    ("iphone", KIND_PHONE),
    ("ipad", KIND_TABLET),
    ("macbook", KIND_COMPUTER),
    ("imac", KIND_COMPUTER),
    ("windows", KIND_COMPUTER),
    ("ubuntu", KIND_COMPUTER),
    ("linux", KIND_COMPUTER),
    ("home assistant", KIND_HUB),
)

WEB_PORTS: tuple[int, ...] = (80, 443, 8080, 8000, 8081, 8888, 5000, 5001)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.S)
MAX_TITLE_CHARS = 70
_CACHE: dict[str, dict[str, Any]] = {}
_CACHE_TTL = 6 * 3600
_TITLE_TIMEOUT = 4
_MAX_BODY = 96_000


def _props(services: dict[str, Any]) -> list[dict[str, Any]]:
    """All service properties a record carries."""
    out: list[dict[str, Any]] = []
    for service in services.values():
        props = getattr(service, "props", None)
        if isinstance(props, dict):
            out.append(props)
    return out


def _service_kinds(services: dict[str, Any]) -> list[str]:
    kinds = [str(getattr(service, "kind", "") or "").lower() for service in services.values()]
    return kinds


def _port_list(services: dict[str, Any]) -> list[int]:
    ports: list[int] = []
    for props in _props(services):
        for value in props.get("ports") or ():
            if isinstance(value, int):
                ports.append(value)
    return ports


def _first_text(props: list[dict[str, Any]], keys: tuple[str, ...]) -> str | None:
    for item in props:
        for key in keys:
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def classify(
    services: dict[str, Any],
    *,
    manufacturer: str | None = None,
    model: str | None = None,
    vendor: str | None = None,
    web_title: str | None = None,
) -> str | None:
    """Best device class from everything already known, without any network IO."""
    kinds = _service_kinds(services)
    for token, kind in MDNS_KINDS:
        if any(token in kind_name for kind_name in kinds):
            return kind
    for props in _props(services):
        device_type = str(props.get("device_type") or "").lower()
        for token, kind in SSDP_KINDS:
            if token in device_type:
                return kind

    for port in _port_list(services):
        if port in PORT_KINDS:
            return PORT_KINDS[port]

    for text in (model, manufacturer, vendor, web_title):
        lowered = (text or "").lower()
        if not lowered:
            continue
        for token, kind in TEXT_KINDS:
            if token in lowered:
                return kind

    for text in (vendor, manufacturer):
        lowered = (text or "").lower()
        if not lowered:
            continue
        for token, kind in VENDOR_KINDS:
            if token in lowered:
                return kind
        if "apple" in lowered:
            return KIND_COMPUTER
        if any(brand in lowered for brand in ("huawei", "zte", "asus", "tplink")):
            return KIND_ROUTER
    return None


def _reverse_dns_sync(ip: str) -> str | None:
    try:
        name = socket.gethostbyaddr(ip)[0]
    except (OSError, socket.herror):
        return None
    return name if name and name != ip else None


async def _async_reverse_dns(hass: HomeAssistant, ip: str) -> str | None:
    try:
        return await asyncio.wait_for(
            hass.async_add_executor_job(_reverse_dns_sync, ip), timeout=3
        )
    except (asyncio.TimeoutError, OSError, ValueError):
        return None


def _clean_title(raw: str) -> str | None:
    text = re.sub(r"<[^>]+>", "", raw)
    text = re.sub(r"\s+", " ", text).strip()
    if not text or len(text) > MAX_TITLE_CHARS:
        return None
    return text


async def _async_web_title(hass: HomeAssistant, ip: str, ports: list[int]) -> str | None:
    """Page title of the device's own web UI, when it has one."""
    candidates = [port for port in ports if port in WEB_PORTS]
    if not candidates:
        return None
    session = async_get_clientsession(hass)
    for port in candidates[:2]:
        scheme = "https" if port == 443 else "http"
        url = f"{scheme}://{ip}:{port}/"
        try:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=_TITLE_TIMEOUT),
                ssl=False,
                allow_redirects=True,
                headers={"User-Agent": "HomeAssistant-LanDiscovery/1.0"},
            ) as response:
                if response.status >= 400:
                    continue
                body = await response.content.read(_MAX_BODY)
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, OSError):
            continue
        match = TITLE_RE.search(body.decode("utf-8", "replace"))
        if match:
            title = _clean_title(match.group(1))
            if title:
                return title
    return None


async def async_enrich(
    hass: HomeAssistant,
    records: list[Any],
    *,
    concurrency: int = 6,
    limit: int = 40,
) -> dict[str, dict[str, Any]]:
    """Resolve hostnames and web titles for records that have an address.

    Results are cached per IP for a few hours: a scan every 30 seconds must not
    hammer the same NAS with HTTP requests.
    """
    now = time.time()
    results: dict[str, dict[str, Any]] = {}
    todo: list[tuple[Any, str]] = []
    for record in records:
        ip = getattr(record, "ip", None)
        if not ip:
            continue
        cached = _CACHE.get(ip)
        if cached and now - cached.get("at", 0) < _CACHE_TTL:
            results[ip] = cached
            continue
        if len(todo) >= limit:
            continue
        todo.append((record, ip))

    if not todo:
        return results

    semaphore = asyncio.Semaphore(concurrency)

    async def one(record: Any, ip: str) -> None:
        async with semaphore:
            ports: list[int] = []
            for service in getattr(record, "services", {}).values():
                props = getattr(service, "props", None)
                if isinstance(props, dict):
                    for value in props.get("ports") or ():
                        if isinstance(value, int):
                            ports.append(value)
            hostname = None
            if not getattr(record, "host", None):
                hostname = await _async_reverse_dns(hass, ip)
            title = await _async_web_title(hass, ip, ports)
            entry = {"at": now, "hostname": hostname, "web_title": title}
            _CACHE[ip] = entry
            results[ip] = entry

    await asyncio.gather(*(one(record, ip) for record, ip in todo))
    return results
