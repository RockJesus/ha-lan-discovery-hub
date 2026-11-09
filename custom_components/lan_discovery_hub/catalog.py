"""Integration catalog: what the market offers, and which entries fit a device.

The panel used to suggest integrations from a hand-written table with a single
row, so almost every device ended up with no suggestion. This module pulls the
same catalog the built-in marketplace uses (HACS data feed, ~5000 integrations
with domain, description, downloads and stars), caches it, and scores entries
against the evidence the scanners collected.

Scoring is deliberately conservative: an exact domain match from a protocol
fingerprint outranks a keyword hit, and plain keyword hits are reported with
their own reason so the panel can show why an entry is suggested.
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import re
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CATALOG_URL = "https://data-v2.hacs.xyz/integration/data.json"
STORAGE_KEY = f"{DOMAIN}_catalog"
STORAGE_VERSION = 1
REFRESH_AFTER = timedelta(hours=24)
MAX_SUGGESTIONS = 5

# Words that carry no signal when matching a device against a description.
_STOPWORDS = {
    "the", "and", "for", "with", "home", "assistant", "integration", "custom",
    "component", "homeassistant", "ha", "a", "an", "of", "to", "in", "on",
    "device", "devices", "support", "supports", "based", "your", "this",
    "local", "network", "lan", "api", "client", "simple", "addon", "add",
}


def _tokens(text: str | None) -> set[str]:
    """Split free text into comparable lowercase tokens."""
    if not text:
        return set()
    return {
        word
        for word in re.findall(r"[a-z0-9][a-z0-9\-_.]{2,}", str(text).lower())
        if word not in _STOPWORDS
    }


class IntegrationCatalog:
    """Cached view of the marketplace catalog plus device matching."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the catalog."""
        self.hass = hass
        self._store: Store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.entries: list[dict[str, Any]] = []
        self.updated: datetime | None = None
        self.total = 0
        self._by_domain: dict[str, dict[str, Any]] = {}
        self._ready = asyncio.Event()

    # ------------------------------------------------------------------ load

    async def async_load(self) -> None:
        """Load from disk, refresh over the network when the cache is stale."""
        stored = await self._store.async_load()
        if stored:
            self._apply(stored.get("entries") or [])
            raw_updated = stored.get("updated")
            if raw_updated:
                try:
                    self.updated = datetime.fromisoformat(raw_updated)
                except ValueError:
                    self.updated = None
        if not self.entries or not self._fresh():
            await self.async_refresh()
        self._ready.set()

    def _fresh(self) -> bool:
        if not self.updated:
            return False
        return datetime.now(self.updated.tzinfo) - self.updated < REFRESH_AFTER

    async def async_refresh(self) -> bool:
        """Fetch the catalog; keep the previous copy when the fetch fails."""
        try:
            payload = await self.hass.async_add_executor_job(_download)
        except Exception as err:  # noqa: BLE001 - offline must not break setup
            _LOGGER.debug("拉取集成目录失败: %s", err)
            return False
        entries = _compact(payload)
        if not entries:
            return False
        self._apply(entries)
        self.updated = datetime.now().astimezone()
        await self._store.async_save(
            {"updated": self.updated.isoformat(), "entries": self.entries}
        )
        _LOGGER.debug("集成目录已更新: %s 条", self.total)
        return True

    def _apply(self, entries: list[dict[str, Any]]) -> None:
        self.entries = entries
        self.total = len(entries)
        self._by_domain = {
            entry["domain"]: entry for entry in entries if entry.get("domain")
        }

    def info(self) -> dict[str, Any]:
        """Small summary for the panel."""
        return {
            "total": self.total,
            "updated": self.updated.isoformat() if self.updated else None,
        }

    # -------------------------------------------------------------- matching

    def suggest(
        self,
        record: Any,
        installed_domains: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Rank catalog entries against one device record."""
        if not self.entries:
            return []
        installed_domains = installed_domains or set()
        device_domain = getattr(record, "domain", None)
        services = getattr(record, "services", {}) or {}

        kinds: set[str] = set()
        ports: set[str] = set()
        for service in services.values():
            source = getattr(service, "source", "")
            kind = getattr(service, "kind", "") or ""
            if source == "mdns":
                kinds.add(re.sub(r"^_", "", kind).split(".")[0].replace("-", "_"))
            elif source == "ssdp":
                props = getattr(service, "props", {}) or {}
                for value in (props.get("model"), props.get("manufacturer")):
                    kinds |= _tokens(value)
            elif source == "probe":
                props = getattr(service, "props", {}) or {}
                for port in props.get("ports") or []:
                    ports.add(str(port))

        device_terms = set()
        for value in (
            getattr(record, "name", None),
            getattr(record, "manufacturer", None),
            getattr(record, "model", None),
            getattr(record, "vendor", None),
            getattr(record, "host", None),
            getattr(record, "detail_line", None),
        ):
            device_terms |= _tokens(value)
        device_terms |= kinds

        candidates: list[tuple[float, dict[str, Any]]] = []
        for entry in self.entries:
            domain = entry.get("domain") or ""
            if not domain:
                continue
            score = 0.0
            reasons: list[str] = []

            if device_domain and domain == device_domain:
                score += 60
                reasons.append("指纹命中")
            if domain in kinds:
                score += 45
                reasons.append("服务类型同名")

            domain_words = set(re.split(r"[_\-.]", domain)) - _STOPWORDS
            overlap = domain_words & device_terms
            if overlap:
                score += 14 * min(len(overlap), 2)
                reasons.append(f"域名含「{'、'.join(sorted(overlap))}」")

            topic_hits = _tokens(" ".join(entry.get("topics") or [])) & device_terms
            if topic_hits:
                score += 5 * min(len(topic_hits), 2)
                reasons.append(f"标签「{'、'.join(sorted(topic_hits))}」")

            if not score:
                desc_hits = _tokens(entry.get("description")) & device_terms
                if desc_hits:
                    score += 3 * min(len(desc_hits), 3)
                    reasons.append(f"描述含「{'、'.join(sorted(desc_hits))}」")

            if not score:
                continue

            # Popularity breaks ties but can never outrank real evidence.
            downloads = entry.get("downloads") or 0
            stars = entry.get("stars") or 0
            score += min(6.0, math.log10(downloads + 1) * 1.5 + math.log10(stars + 1))

            if domain in installed_domains:
                score -= 8

            enriched = dict(entry)
            enriched["score"] = round(score, 1)
            enriched["reason"] = "；".join(reasons) or "热度"
            enriched["installed"] = domain in installed_domains
            candidates.append((score, enriched))

        candidates.sort(key=lambda item: -item[0])
        return [entry for _, entry in candidates[:MAX_SUGGESTIONS]]


def _download() -> dict[str, Any]:
    """Blocking fetch of the HACS data feed used by the marketplace."""
    import urllib.request  # noqa: PLC0415 - imported lazily for the executor

    request = urllib.request.Request(
        CATALOG_URL,
        headers={"User-Agent": "lan-discovery-hub/1.0", "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=45) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


def _compact(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Reduce the feed to the fields the panel actually shows."""
    entries: list[dict[str, Any]] = []
    for repo_id, raw in payload.items():
        if not isinstance(raw, dict):
            continue
        domain = raw.get("domain")
        if not domain:
            continue
        description = (raw.get("description") or "").strip()
        entries.append(
            {
                "id": str(repo_id),
                "domain": domain,
                "name": raw.get("manifest_name") or raw.get("name") or domain,
                "full_name": raw.get("full_name") or "",
                "description": description[:140],
                "downloads": int(raw.get("downloads") or 0),
                "stars": int(raw.get("stargazers_count") or 0),
                "topics": list(raw.get("topics") or [])[:6],
                "updated": raw.get("last_updated"),
            }
        )
    entries.sort(key=lambda item: -item["downloads"])
    return entries
