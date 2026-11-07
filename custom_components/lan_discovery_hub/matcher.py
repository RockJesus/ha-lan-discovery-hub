"""Resolve LAN fingerprints to Home Assistant integrations.

Three layers are consulted, in this order:

1. a user supplied map (``<config>/lan_discovery_hub_map.json``) so the owner
   can always override anything;
2. Home Assistant's own generated matcher tables, so a fingerprint is mapped to
   exactly the integration core would have used;
3. this repository's curated ``integration_map.json``, which covers third-party
   integrations that are not part of the core image — the gap the official
   discovery cannot fill.
"""

from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatch
import json
import logging
from pathlib import Path
from typing import Any

from .const import SOURCE_BLE, SOURCE_MDNS, SOURCE_MQTT, SOURCE_SSDP

_LOGGER = logging.getLogger(__name__)

MATCH_CORE = "core"
MATCH_CURATED = "curated"
MATCH_USER = "user"

USER_MAP_FILENAME = "lan_discovery_hub_map.json"


@dataclass(slots=True)
class Match:
    """The integration a device should be added through."""

    domain: str
    integration: str | None
    repo: str | None
    source: str


def _load_json(path: Path) -> list[dict[str, Any]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except (OSError, ValueError) as err:
        _LOGGER.warning("无法读取映射文件 %s: %s", path, err)
        return []
    if not isinstance(raw, list):
        _LOGGER.warning("映射文件 %s 顶层必须是数组", path)
        return []
    return [entry for entry in raw if isinstance(entry, dict)]


class IntegrationMatcher:
    """Matches observations against known integrations."""

    def __init__(self, config_dir: str) -> None:
        """Load curated and user maps."""
        package_dir = Path(__file__).parent
        self._curated = _load_json(package_dir / "integration_map.json")
        self._user = _load_json(Path(config_dir) / USER_MAP_FILENAME)
        self._display_names: dict[str, str | None] = {}

    # ------------------------------------------------------------------ core

    @staticmethod
    def _zeroconf_table() -> dict[str, list[dict[str, Any]]]:
        try:
            from homeassistant.generated.zeroconf import (  # noqa: PLC0415
                ZEROCONF as ZEROCONF_MATCHERS,
            )
        except ImportError:  # pragma: no cover - very old core
            return {}
        return ZEROCONF_MATCHERS if isinstance(ZEROCONF_MATCHERS, dict) else {}

    @staticmethod
    def _ssdp_table() -> dict[str, list[dict[str, Any]]]:
        try:
            from homeassistant.generated.ssdp import (  # noqa: PLC0415
                SSDP as SSDP_MATCHERS,
            )
        except ImportError:  # pragma: no cover - very old core
            return {}
        return SSDP_MATCHERS if isinstance(SSDP_MATCHERS, dict) else {}

    def mdns_service_types(self) -> list[str]:
        """Every mDNS service type worth browsing.

        The generated core table gives us the types HA itself would listen to;
        curated and user entries add third-party ones that core does not know.
        """
        types = {str(key) for key in self._zeroconf_table()}
        for entry in (*self._curated, *self._user):
            if entry.get("source") != SOURCE_MDNS:
                continue
            kind = entry.get("kind")
            if kind and str(kind) != "*":
                types.add(str(kind))
        return sorted(types)

    # --------------------------------------------------------------- matching

    def resolve(self, observation: Any) -> Match | None:
        """Return the integration this observation belongs to."""
        if observation.source == SOURCE_BLE:
            domain = observation.props.get("vendor_domain")
            if domain:
                return Match(
                    domain=str(domain),
                    integration=None,
                    repo=observation.props.get("vendor_repo"),
                    source=MATCH_CURATED,
                )
            return None
        if observation.source == SOURCE_MQTT:
            # Anything announced on the broker is adopted by the MQTT integration
            # itself; the row is here so the owner can see it before it lands.
            return Match(
                domain="mqtt", integration="MQTT 自动认领", repo=None, source=MATCH_CORE
            )

        for layer, entries in (
            (MATCH_USER, self._user),
            (MATCH_CURATED, self._curated),
        ):
            match = self._match_entries(entries, observation, layer)
            if match is not None:
                return match

        if observation.source == SOURCE_MDNS:
            return self._match_mdns_core(observation)
        if observation.source == SOURCE_SSDP:
            return self._match_ssdp_core(observation)
        return None

    def _match_mdns_core(self, observation: Any) -> Match | None:
        matchers = self._zeroconf_table().get(observation.kind) or []
        for matcher in matchers:
            domain = matcher.get("domain")
            if not domain:
                continue
            name_pattern = matcher.get("name")
            if name_pattern and not fnmatch(
                observation.detail.lower(), str(name_pattern).lower()
            ):
                continue
            if not self._props_match(matcher.get("properties"), observation.props):
                continue
            return Match(domain=domain, integration=None, repo=None, source=MATCH_CORE)
        return None

    def _match_ssdp_core(self, observation: Any) -> Match | None:
        matchers = self._ssdp_table().get(observation.kind) or []
        headers = {
            "st": observation.kind,
            "usn": observation.detail,
            "server": str(observation.props.get("server") or ""),
            "manufacturer": str(observation.props.get("manufacturer") or ""),
            "model": str(observation.props.get("model") or ""),
            "devicetype": str(observation.props.get("device_type") or ""),
        }
        for matcher in matchers:
            domain = matcher.get("domain")
            if not domain:
                continue
            if self._ssdp_matcher_matches(matcher, headers):
                return Match(
                    domain=domain, integration=None, repo=None, source=MATCH_CORE
                )
        return None

    @staticmethod
    def _ssdp_matcher_matches(
        matcher: dict[str, Any], headers: dict[str, str]
    ) -> bool:
        checked = False
        for key, pattern in matcher.items():
            if key == "domain":
                continue
            actual = headers.get(key.lower())
            if actual is None:
                return False
            checked = True
            expected = str(pattern).lower()
            if expected.endswith("*"):
                if not actual.lower().startswith(expected[:-1]):
                    return False
            elif actual.lower() != expected:
                return False
        return checked

    def _match_entries(
        self, entries: list[dict[str, Any]], observation: Any, layer: str
    ) -> Match | None:
        for entry in entries:
            source = entry.get("source")
            if source and source != observation.source:
                continue
            kind = entry.get("kind")
            if kind and str(kind) != "*" and not fnmatch(
                observation.kind.lower(), str(kind).lower()
            ):
                continue
            name_pattern = entry.get("name")
            if name_pattern and not fnmatch(
                observation.detail.lower(), str(name_pattern).lower()
            ):
                continue
            if not self._props_match(entry.get("props"), observation.props):
                continue
            domain = entry.get("domain")
            if not domain:
                continue
            return Match(
                domain=str(domain),
                integration=entry.get("integration"),
                repo=entry.get("repo"),
                source=layer,
            )
        return None

    @staticmethod
    def _props_match(
        expected: dict[str, Any] | None, actual: dict[str, Any]
    ) -> bool:
        if not expected:
            return True
        for key, pattern in expected.items():
            value = actual.get(key)
            if value is None:
                return False
            value_str = str(value).lower()
            pattern_str = str(pattern).lower()
            if pattern_str.endswith("*"):
                if not value_str.startswith(pattern_str[:-1]):
                    return False
            elif value_str != pattern_str:
                return False
        return True

    # ------------------------------------------------------------- available

    def integration_present(self, hass: Any, domain: str) -> bool:
        """Whether the integration exists in this HA installation at all.

        This mirrors what official discovery can reach: core integrations ship
        with the image, custom ones only after they were downloaded. Checking
        the filesystem is the cheapest reliable way that does not require
        starting a config flow.
        """
        if not domain:
            return False
        try:
            import homeassistant  # noqa: PLC0415

            core = Path(homeassistant.__file__).parent / "components" / domain
            if core.is_dir():
                return True
        except (ImportError, OSError):  # pragma: no cover
            pass
        try:
            custom = Path(hass.config.config_dir) / "custom_components" / domain
            return custom.is_dir()
        except (AttributeError, OSError):  # pragma: no cover
            return False

    def display_name(self, hass: Any, domain: str) -> str | None:
        """Human readable integration name from its manifest."""
        if not domain:
            return None
        if domain in self._display_names:
            return self._display_names[domain]

        name: str | None = None
        paths: list[Path] = []
        try:
            import homeassistant  # noqa: PLC0415

            paths.append(
                Path(homeassistant.__file__).parent / "components" / domain
            )
        except (ImportError, OSError):  # pragma: no cover
            pass
        try:
            paths.append(Path(hass.config.config_dir) / "custom_components" / domain)
        except (AttributeError, OSError):  # pragma: no cover
            pass

        for path in paths:
            manifest = path / "manifest.json"
            if not manifest.is_file():
                continue
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            name = data.get("name") or domain
            break

        self._display_names[domain] = name or domain
        return self._display_names[domain]
