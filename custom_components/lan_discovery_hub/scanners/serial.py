"""Serial / USB adapter detection.

Zigbee and Z-Wave radios never show up on the network: they are a USB stick the
coordinator talks to over a serial port. Home Assistant exposes them inside the
container under ``/dev/serial/by-id/`` (a symlink per port, named after the
adapter's USB descriptors), and every USB device also appears under
``/sys/bus/usb/devices/`` with vendor and product strings.

Reading those two places is read-only and needs no privileges, so the ledger can
say "there is a Sonoff Zigbee stick on /dev/ttyUSB0, that is a ZHA device"
instead of leaving the owner to guess which dongle is which.

Nothing here opens the port: a coordinator may already hold it, and probing a
serial line can reset the radio.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from ..const import SERIAL_HINTS, SERIAL_VID_PID, SOURCE_SERIAL
from ..i18n import t
from ..registry import Observation

_LOGGER = logging.getLogger(__name__)

# Hardware names stay verbatim; only the generic role descriptions are translated.
_GENERIC_LABELS = {
    "Zigbee adapter": "serial.zigbee_adapter",
    "Z-Wave adapter": "serial.zwave_adapter",
    "Espressif serial port": "serial.esp",
}

BY_ID_DIR = Path("/dev/serial/by-id")
USB_DIR = Path("/sys/bus/usb/devices")


def classify(text: str) -> tuple[str, str | None, str | None]:
    """Return ``(domain, repo, label)`` for a by-id or product string."""
    lowered = text.lower()
    for needle, domain, repo, label in SERIAL_HINTS:
        if needle in lowered:
            return domain, repo, label
    # Unnamed sticks only expose their USB ids: "usb-0658_0200-if00".
    match = re.search(r"([0-9a-f]{4})_([0-9a-f]{4})", lowered)
    if match:
        entry = SERIAL_VID_PID.get(f"{match.group(1)}:{match.group(2)}")
        if entry:
            return entry
    return "", None, None


def pretty_name(by_id: str) -> str:
    """Turn a by-id file name into something readable."""
    name = by_id
    name = re.sub(r"^usb-", "", name)
    name = re.sub(r"-if\d+-port\d+$", "", name)
    name = re.sub(r"_[0-9A-Fa-f]{8,}", "", name)  # serial numbers
    name = name.replace("_", " ").strip()
    return name or by_id


def usb_inventory() -> dict[str, dict[str, str]]:
    """Map ``vid:pid`` to the descriptors sysfs reports."""
    found: dict[str, dict[str, str]] = {}
    try:
        entries = list(USB_DIR.glob("*"))
    except OSError:
        return found
    for entry in entries:
        try:
            vid = (entry / "idVendor").read_text(encoding="utf-8").strip()
            pid = (entry / "idProduct").read_text(encoding="utf-8").strip()
        except (OSError, ValueError):
            continue
        if not vid or not pid:
            continue
        key = f"{vid.lower()}:{pid.lower()}"
        info: dict[str, str] = {}
        for field in ("manufacturer", "product", "serial"):
            try:
                info[field] = (entry / field).read_text(encoding="utf-8").strip()
            except (OSError, ValueError):
                info[field] = ""
        found.setdefault(key, info)
    return found


class SerialScanner:
    """Reports serial/USB adapters without opening them."""

    def __init__(self, hass: Any, on_observation: Any) -> None:
        """Initialize the scanner."""
        self.hass = hass
        self._on_observation = on_observation
        self.available = False
        self.reason: str | None = None

    async def async_start(self) -> None:
        """Check whether the container can see serial devices at all."""
        try:
            self.available = BY_ID_DIR.is_dir()
        except OSError:
            self.available = False
        self.reason = (
            None
            if self.available
            else t(self.hass, "channel.serial_missing")
        )

    async def async_stop(self) -> None:
        """Nothing to release: the port is never opened."""

    def snapshot(self) -> list[Observation]:
        """Every serial adapter currently mapped into the container."""
        if not self.available:
            return []
        try:
            entries = sorted(BY_ID_DIR.iterdir())
        except OSError as err:
            _LOGGER.debug("读取串口目录失败: %s", err)
            return []

        def shown(value: str | None) -> str | None:
            """Translate the generic role names, leave hardware names alone."""
            if not value:
                return value
            key = _GENERIC_LABELS.get(value)
            return t(self.hass, key) if key else value

        usb = usb_inventory()
        out: list[Observation] = []
        for entry in entries:
            by_id = entry.name
            domain, repo, label = classify(by_id)
            # An unattributed port stays "unknown" rather than pointing the
            # owner at an integration we only guessed at.
            port = ""
            try:
                port = str(entry.resolve())
            except OSError:
                port = ""
            vid_pid = ""
            match = re.search(r"(?:usb-)?([0-9a-fA-F]{4})_([0-9a-fA-F]{4})", by_id)
            if match:
                vid_pid = f"{match.group(1).lower()}:{match.group(2).lower()}"
            usb_info = usb.get(vid_pid, {})
            out.append(
                Observation(
                    source=SOURCE_SERIAL,
                    kind="adapter",
                    detail=by_id,
                    name=pretty_name(by_id),
                    manufacturer=shown(usb_info.get("manufacturer")) or shown(label),
                    model=shown(usb_info.get("product")),
                    hint=t(self.hass, "channel.serial"),
                    unique_instance=True,
                    props={
                        "port": port,
                        "by_id": by_id,
                        "vid_pid": vid_pid or None,
                        "vendor_domain": domain or None,  # "" means unattributed
                        "vendor_repo": repo,
                    },
                )
            )
        return out

    def active_keys(self) -> set[str]:
        """Service keys for the adapters currently present."""
        return {obs.service_key for obs in self.snapshot()}
