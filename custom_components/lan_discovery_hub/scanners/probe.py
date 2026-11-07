"""TCP port probing and ARP cache reading.

Two constraints shaped this module:

* ICMP (and raw sockets in general) usually needs ``CAP_NET_RAW``, which the
  Home Assistant container does not have — so reachability is checked with
  plain TCP connects instead;
* ARP cannot be enumerated actively from user space, we can only read the
  kernel's neighbour cache. That cache is still useful: it pairs IPs with MACs,
  which is what lets a device seen through mDNS, SSDP and DHCP collapse into a
  single record.
"""

from __future__ import annotations

import asyncio
import logging
import socket
from pathlib import Path

_LOGGER = logging.getLogger(__name__)

ARP_PATH = Path("/proc/net/arp")
MAX_PROBE_IPS = 96
PROBE_CONCURRENCY = 32


def local_ipv4() -> str | None:
    """Return the machine's primary IPv4 address without sending traffic."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError as err:  # pragma: no cover - offline container
        _LOGGER.debug("无法获取本机 IPv4: %s", err)
        return None
    finally:
        sock.close()


def local_prefix() -> str | None:
    """Return the /24 prefix (``192.168.1``) of the primary interface."""
    address = local_ipv4()
    if not address:
        return None
    parts = address.split(".")
    if len(parts) != 4:
        return None
    return ".".join(parts[:3])


def read_arp_cache(path: Path = ARP_PATH) -> dict[str, str]:
    """Read the kernel neighbour cache as ``{ip: mac}``.

    ``/proc/net/arp`` is Linux-only; on other hosts this returns an empty map
    and the hub simply loses the MAC pairing, not the scan itself.
    """
    entries: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except (FileNotFoundError, OSError, PermissionError):
        return entries
    for line in lines[1:]:
        fields = line.split()
        if len(fields) < 4:
            continue
        ip, _hw_type, flags, mac = fields[0], fields[1], fields[2], fields[3]
        if flags == "0x0" or mac == "00:00:00:00:00:00":
            continue
        entries[ip] = mac.lower()
    return entries


async def _async_port_open(ip: str, port: int, timeout: float) -> bool:
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, port), timeout
        )
    except (OSError, TimeoutError, asyncio.TimeoutError):
        return False
    except Exception as err:  # noqa: BLE001 - one port must not break the sweep
        _LOGGER.debug("探测 %s:%s 失败: %s", ip, port, err)
        return False
    writer.close()
    try:
        await writer.wait_closed()
    except (OSError, TimeoutError, asyncio.TimeoutError):
        pass
    del reader
    return True


async def async_probe_ips(
    ips: list[str],
    ports: tuple[int, ...] | list[int],
    timeout: float = 1.0,
    concurrency: int = PROBE_CONCURRENCY,
) -> dict[str, list[int]]:
    """Check a small port set on every given IP."""
    semaphore = asyncio.Semaphore(concurrency)
    results: dict[str, list[int]] = {}

    async def _probe(ip: str, port: int) -> tuple[str, int, bool]:
        async with semaphore:
            return ip, port, await _async_port_open(ip, port, timeout)

    tasks = [
        asyncio.create_task(_probe(ip, port))
        for ip in ips[:MAX_PROBE_IPS]
        for port in ports
    ]
    if not tasks:
        return results
    for task in asyncio.as_completed(tasks):
        ip, port, is_open = await task
        results.setdefault(ip, [])
        if is_open:
            results[ip].append(port)
    return results


async def async_sweep_subnet(
    prefix: str,
    ports: tuple[int, ...] | list[int],
    timeout: float = 0.6,
    concurrency: int = 128,
    min_host: int = 1,
    max_host: int = 254,
) -> dict[str, list[int]]:
    """Probe a /24 range for a very small port set.

    This is intentionally opt-in: it is the only path that touches hosts which
    never announced themselves, which is noisy and slow on a big network.
    """
    ips = [f"{prefix}.{host}" for host in range(min_host, max_host + 1)]
    return await async_probe_ips(ips, ports, timeout=timeout, concurrency=concurrency)
