"""LAN device discovery: mDNS listeners, bookkeeping and integration guidance.

设计要点：
- 推送型：不引入轮询 coordinator，mDNS 回调即为数据源。
- 服务类型 → 集成域的映射直接复用 HA 的 hassfest 生成表
  （``homeassistant.generated.zeroconf.ZEROCONF``，114 种），不再手写，
  避免映射过时或缺漏。
- 发现设备后创建 issue；若该集成尚未安装，issue 的修复流会引导用户
  通过 ``config_entries/flow`` 走官方安装流程。
"""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import logging
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.issue_registry import (
    async_create_issue,
    async_delete_issue,
    IssueSeverity,
)
from homeassistant.helpers.storage import Store

from .const import (
    CONF_IGNORED_TYPES,
    DEFAULT_IGNORED_TYPES,
    DOMAIN,
    ISSUE_NEW_DEVICE,
)

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
STORAGE_KEY = "lan_discovery_hub/devices"

# 记录结构版本。升级逻辑时 +1，旧记录会在下次广播时自动重算，
# 这样就不必要求用户清存储才能看到新的集成判定结果。
RECORD_SCHEMA = 2

# HA 启动时不会马上跑完 zeroconf 的初始扫描，留一点时间再发「新设备」提示，
# 免得开机瞬间弹出一堆其实已经在配置中的设备。
SETTLE_DELAY = 60


def _issue_id(device_key: str) -> str:
    """Derive a stable issue id from a device key.

    ``hash()`` 受 PYTHONHASHSEED 影响，进程重启后结果会变，用它做 issue id
    会导致旧 issue 永远删不掉、并且越积越多。改用 sha1 摘要的前 16 位。
    """
    digest = hashlib.sha1(device_key.encode()).hexdigest()[:16]
    return f"{ISSUE_NEW_DEVICE}_{digest}"


def _match_name(name: str, pattern: str) -> bool:
    """Match a service instance name against a hassfest name pattern.

    hassfest 的 name 字段用的是 fnmatch 风格（``shelly*``、``pblr-*``），
    这里直接用 fnmatch，避免自己造轮子。
    """
    from fnmatch import fnmatch  # noqa: PLC0415

    return fnmatch(name.lower(), pattern.lower())


def _match_properties(matcher: dict[str, Any], props: dict[str, Any]) -> bool:
    """Check mDNS TXT properties against a hassfest matcher."""
    expected = matcher.get("properties")
    if not expected:
        return True
    for prop_key, pattern in expected.items():
        actual = props.get(prop_key)
        if actual is None:
            return False
        actual = str(actual).lower()
        pattern = str(pattern).lower()
        if pattern.endswith("*"):
            if not actual.startswith(pattern[:-1]):
                return False
        elif actual != pattern:
            return False
    return True


def resolve_domain(
    service_type: str, name: str, props: dict[str, Any]
) -> str | None:
    """Return the integration domain HA would use for this announcement.

    按 hassfest 生成的完整映射表匹配；``_http`` 这类一个服务类型对应几十个
    集成的，必须同时匹配 ``name`` 与 ``properties`` 才能确定，否则不乱猜。
    """
    try:
        from homeassistant.generated.zeroconf import (  # noqa: PLC0415
            ZEROCONF as ZEROCONF_MATCHERS,
        )
    except ImportError:  # pragma: no cover - 极老版本兜底
        return None

    matchers = ZEROCONF_MATCHERS.get(service_type)
    if not matchers:
        return None

    # 只按顺序取第一个全部条件都匹配上的 matcher，与 HA 自身行为一致。
    for matcher in matchers:
        domain = matcher.get("domain")
        if not domain:
            continue
        if pattern := matcher.get("name"):
            if not _match_name(name, pattern):
                continue
        if not _match_properties(matcher, props):
            continue
        return domain
    return None


class DiscoveryStore:
    """Persist seen devices across restarts."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.data: dict[str, dict[str, Any]] = {}

    async def async_load(self) -> None:
        self.data = await self._store.async_load() or {}

    async def async_save(self) -> None:
        await self._store.async_save(self.data)


class DiscoveryHub:
    """Tracks LAN devices seen via mDNS and guides the user to integrations."""

    def __init__(self, hass: HomeAssistant, entry) -> None:
        self.hass = hass
        self.entry = entry
        self.store = DiscoveryStore(hass)
        self._browser = None
        self._ignored: list[str] = list(
            entry.options.get(CONF_IGNORED_TYPES, DEFAULT_IGNORED_TYPES)
        )

    async def async_start(self) -> None:
        """Load persisted state and subscribe to zeroconf browsing."""
        await self.store.async_load()

        from homeassistant.components.zeroconf import (  # noqa: PLC0415
            async_get_instance,
        )

        zc = await async_get_instance(self.hass)

        from zeroconf import (  # noqa: PLC0415
            ServiceStateChange,
            Zeroconf,
        )
        from zeroconf.asyncio import (  # noqa: PLC0415
            AsyncServiceBrowser,
        )

        # 注意：zeroconf 的 Signal.fire 只以 **kwargs 调用处理器，且参数名固定为
        # zeroconf / service_type / name / state_change，必须逐一对应；
        # 签名不匹配会在 AsyncServiceBrowser 构造期间（回放缓存记录时）直接抛
        # TypeError，导致整个 config entry setup 失败。
        @callback
        def _on_service_state_change(
            *,
            zeroconf: Zeroconf,
            service_type: str,
            name: str,
            state_change: ServiceStateChange,
        ) -> None:
            if state_change is not ServiceStateChange.Added:
                return
            self.hass.async_create_task(
                self._async_handle_service(zeroconf, service_type, name)
            )

        # 浏览全部已知类型（None = 全量），否则像 _smb / _http 这类没有对应
        # 集成的设备永远不会被发现。
        self._browser = AsyncServiceBrowser(
            zc, list(_all_service_types()) or None, handlers=[_on_service_state_change]
        )
        _LOGGER.info("LAN discovery listener started")

    async def async_stop(self) -> None:
        """Tear down the browser."""
        if self._browser is not None:
            await self._browser.async_cancel()
            self._browser = None

    async def _async_handle_service(
        self, zc, service_type: str, name: str
    ) -> None:
        """Bookkeep one mDNS announcement and guide the user."""
        if service_type in self._ignored:
            return

        key = f"{service_type}::{name}"
        existing = self.store.data.get(key)
        if existing is not None and existing.get("schema") == RECORD_SCHEMA:
            # 同一套逻辑记录过，不重复处理（避免每次广播都刷 issue）
            return

        # 需要完整信息才能判断该用哪个集成（_airplay 要靠 model 区分
        # apple_tv 与 samsungtv），所以这里主动解析一次。
        props: dict[str, Any] = {}
        host = port = None
        try:
            from zeroconf.asyncio import (  # noqa: PLC0415
                AsyncServiceInfo,
            )

            info = AsyncServiceInfo(service_type, name)
            if await info.async_request(zc, 3000):
                props = {
                    k.decode(errors="replace"): (v.decode(errors="replace") if v else None)
                    for k, v in (info.properties or {}).items()
                }
                host = info.server
                port = info.port
        except Exception as err:  # noqa: BLE001 - 单个设备解析失败不该影响整体
            _LOGGER.debug("无法解析 mDNS 信息 %s: %s", name, err)

        target_domain = resolve_domain(service_type, name, props)
        record = {
            "schema": RECORD_SCHEMA,
            "service_type": service_type,
            "name": name.rsplit(".", 1)[0],
            "host": host,
            "port": port,
            "properties": props,
            "first_seen": (existing or {}).get(
                "first_seen", datetime.now(UTC).isoformat()
            ),
            "suggested_integration": target_domain,
            # 从旧结构迁移过来时保留用户「已知悉」的意愿，不要重新弹提示
            "acknowledged": bool((existing or {}).get("acknowledged", False)),
        }
        self.store.data[key] = record
        await self.store.async_save()

        self.hass.bus.async_fire(
            "lan_discovery_hub_device_seen",
            {
                "key": key,
                "service_type": service_type,
                "name": record["name"],
                "integration": target_domain,
            },
        )

        if record["acknowledged"]:
            _LOGGER.debug("已忽略的设备重新出现，跳过提示: %s", name)
            return

        self._async_create_issue(key, record)
        _LOGGER.debug("New LAN device: %s (%s) -> %s", name, service_type, target_domain)

    @callback
    def _async_create_issue(self, key: str, record: dict[str, Any]) -> None:
        """Create a repair issue, marking it fixable when we know the target."""
        domain = record.get("suggested_integration")
        installed = domain is not None and self.hass.config_entries.async_entries(domain)

        # 已装但还没配这个设备 / 没装但知道该装什么 → 都可以给「修复」按钮。
        # 完全不认识的设备只能提示，不做虚假引导。
        fixable = domain is not None

        async_create_issue(
            self.hass,
            DOMAIN,
            _issue_id(key),
            is_fixable=fixable,
            severity=IssueSeverity.WARNING,
            translation_key=ISSUE_NEW_DEVICE,
            translation_placeholders={
                "name": record["name"],
                "service_type": record["service_type"],
                "integration": domain or "未知",
                "state": "已安装，可直接添加" if installed else (
                    "尚未安装，点击修复可前往安装" if domain else "无法自动识别"
                ),
            },
            data={
                "device_key": key,
                "integration": domain or "",
                "installed": installed,
            },
        )

    async def async_acknowledge(self, key: str) -> None:
        """User acknowledged a device: drop its issue but keep the record."""
        if key not in self.store.data:
            return
        self.store.data[key]["acknowledged"] = True
        await self.store.async_save()
        async_delete_issue(self.hass, DOMAIN, _issue_id(key))


def _all_service_types() -> set[str]:
    """All mDNS service types HA knows about, plus a few we still want to show."""
    try:
        from homeassistant.generated.zeroconf import (  # noqa: PLC0415
            ZEROCONF as ZEROCONF_MATCHERS,
        )
    except ImportError:  # pragma: no cover
        return set()

    types = set(ZEROCONF_MATCHERS)
    # 这些类型 HA 不认识、但用户常想看到（NAS、打印机、网页管理口）
    types.update({"_smb._tcp.local.", "_http._tcp.local.", "_https._tcp.local."})
    return types
