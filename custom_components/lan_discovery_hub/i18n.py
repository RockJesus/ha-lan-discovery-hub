"""Bilingual runtime strings.

Home Assistant translates config flows / entities through ``translations``, but
text the integration *generates at runtime* (panel payload, notification body,
match evidence, catalog reasons) never passes through that machinery. This
module is the single place those strings live, so every one of them exists in
both English and Simplified Chinese.
."""

from __future__ import annotations

from typing import Any

EN = "en"
ZH = "zh-Hans"

STRINGS: dict[str, dict[str, str]] = {
    # ------------------------------------------------------------- panel shell
    "panel.title": {EN: "LAN Discovery", ZH: "局域网发现"},
    # ---------------------------------------------------------------- channels
    "channel.mdns": {EN: "LAN · mDNS", ZH: "局域网 · mDNS"},
    "channel.ssdp": {EN: "LAN · SSDP", ZH: "局域网 · SSDP"},
    "channel.probe": {EN: "LAN · port probe", ZH: "局域网 · 探测"},
    "channel.mqtt": {EN: "MQTT device", ZH: "MQTT 设备"},
    "channel.ble": {EN: "Bluetooth device", ZH: "蓝牙设备"},
    "channel.serial": {EN: "Serial device", ZH: "串口设备"},
    "channel.arp": {EN: "LAN · ARP neighbour", ZH: "局域网 · ARP 邻居"},
    "channel.none": {EN: "Uncategorised", ZH: "未分类"},
    "channel.disabled": {EN: "not enabled", ZH: "未启用"},
    "channel.ble_no_scanner": {
        EN: "Bluetooth adapter/proxy configured ({count}), but no scanner is online right now",
        ZH: "蓝牙适配器/代理已配置 {count} 个，但当前没有在线扫描器",
    },
    "channel.ble_no_entries": {
        EN: "No Bluetooth scanner enabled (no adapter or proxy configured)",
        ZH: "没有已启用的蓝牙扫描器（未配置适配器或代理）",
    },
    "channel.serial_missing": {
        EN: "/dev/serial/by-id is not visible inside the container (no adapter plugged in, or the port is not mapped)",
        ZH: "容器内看不到 /dev/serial/by-id（未插适配器或串口未映射进容器）",
    },
    # ------------------------------------------------------------- port labels
    "port.445": {EN: "SMB file share", ZH: "SMB 文件共享"},
    "port.554": {EN: "RTSP stream", ZH: "RTSP 视频流"},
    "port.631": {EN: "IPP printing", ZH: "IPP 打印"},
    "port.9100": {EN: "Print service", ZH: "打印服务"},
    "port.49152": {EN: "Private port", ZH: "私有端口"},
    "port.3493": {EN: "NUT monitor", ZH: "NUT 监控服务"},
    "port.1883": {EN: "MQTT broker", ZH: "MQTT 消息代理"},
    "port.32400": {EN: "Plex media server", ZH: "Plex 媒体服务器"},
    "port.6053": {EN: "ESPHome native API", ZH: "ESPHome 原生 API"},
    # ---------------------------------------------------------------- evidence
    "evidence.vendor_domain": {EN: "Vendor domain reported by the device", ZH: "设备自报厂商域"},
    "evidence.mqtt_claim": {EN: "Adopted by MQTT", ZH: "MQTT 自动认领"},
    "evidence.mqtt_topic": {EN: "MQTT discovery topic", ZH: "MQTT 发现主题"},
    "evidence.port": {EN: "Port {port} ({label})", ZH: "端口 {port}（{label}）"},
    "evidence.history": {EN: "Earlier match · not seen this round", ZH: "历史判定 · 本轮未复现"},
    "evidence.support": {EN: " · confirmed by {count} protocols", ZH: " · {count} 种协议互证"},
    "guess.prefix": {EN: "Guess · {name}", ZH: "推测 · {name}"},
    "unknown.integration": {EN: "Unknown integration", ZH: "未知集成"},
    "unknown.address": {EN: "Unknown address", ZH: "未知地址"},
    "unknown.device": {EN: "Unknown device", ZH: "未知设备"},
    # ------------------------------------------------------------------ detail
    "detail.ble_rssi": {EN: "Signal {rssi} dBm", ZH: "信号 {rssi} dBm"},
    "detail.ble_plain": {EN: "Bluetooth advertisement", ZH: "蓝牙广播"},
    "detail.mqtt_auto": {EN: "MQTT auto-discovery", ZH: "MQTT 自动发现"},
    "detail.serial": {EN: "Serial device", ZH: "串口设备"},
    "detail.ports": {EN: "Ports {ports}", ZH: "端口 {ports}"},
    # ------------------------------------------------------------- notification
    "notify.title": {EN: "LAN Discovery", ZH: "局域网发现"},
    "notify.line": {EN: "- **{name}** ({where}) → {integration}", ZH: "- **{name}**（{where}）→ {integration}"},
    "notify.more": {EN: "- {count} more in the panel", ZH: "- 其余 {count} 台见面板"},
    "notify.body": {
        EN: "**{count}** device(s) can be added now:\n\n{lines}\n\nOpen the “LAN Discovery” panel in the sidebar to see every device, configure it or install the matching integration.",
        ZH: "发现 **{count}** 台可接入的设备：\n\n{lines}\n\n打开侧栏「局域网发现」面板可查看全部设备、一键配置或安装对应集成。",
    },
    # ------------------------------------------------------------------ names
    "registry.unknown": {EN: "Unknown device", ZH: "未知设备"},
    "ws.not_loaded": {EN: "The integration is not running yet", ZH: "集成尚未启动"},
    # ------------------------------------------------------------------ serial
    "serial.zigbee_adapter": {EN: "Zigbee adapter", ZH: "Zigbee 适配器"},
    "serial.zwave_adapter": {EN: "Z-Wave adapter", ZH: "Z-Wave 适配器"},
    "serial.esp": {EN: "Espressif serial port", ZH: "Espressif 串口"},
    # ------------------------------------------------------------ config labels
    "source.mdns": {EN: "mDNS (AirPlay, Cast, printers, HomeKit…)", ZH: "mDNS（AirPlay、Cast、打印机、HomeKit…）"},
    "source.ssdp": {EN: "SSDP / UPnP (TVs, speakers, routers, NAS…)", ZH: "SSDP / UPnP（电视、音箱、路由、NAS…）"},
    "source.probe": {EN: "TCP port probe + ARP cache (fills in IP and MAC)", ZH: "TCP 端口探测 + ARP 缓存（补齐 IP 与 MAC）"},
    "source.arp": {EN: "ARP neighbour cache only", ZH: "仅 ARP 邻居缓存"},
    # ---------------------------------------------------------- catalog reasons
    "catalog.reason.fingerprint": {EN: "integration domain matches the device", ZH: "指纹命中"},
    "catalog.reason.kind_same": {EN: "same service type", ZH: "服务类型同名"},
    "catalog.reason.domain_kind": {EN: "domain shares “{terms}”", ZH: "域名与「{terms}」同源"},
    "catalog.reason.domain_vendor": {EN: "domain carries vendor “{terms}”", ZH: "域名含厂商「{terms}」"},
    "catalog.reason.topic": {EN: "tagged “{terms}”", ZH: "标签「{terms}」"},
    "catalog.reason.description": {EN: "described with “{terms}”", ZH: "描述含「{terms}」"},
    "catalog.reason.popular": {EN: "popularity", ZH: "热度"},
    "catalog.joiner": {EN: "; ", ZH: "；"},
}


def language_of(hass: Any) -> str:
    """Return the string table language for this installation."""
    lang = None
    try:
        lang = getattr(hass.config, "language", None)
    except AttributeError:  # pragma: no cover - hass may be None in tests
        lang = None
    if not lang:
        return EN
    return ZH if str(lang).lower().startswith("zh") else EN


def t(hass: Any, key: str, **fmt: Any) -> str:
    """Translate one runtime string, falling back to English."""
    entry = STRINGS.get(key)
    if not entry:
        return key
    text = entry.get(language_of(hass)) or entry.get(EN) or key
    if fmt:
        try:
            return text.format(**fmt)
        except (KeyError, IndexError):  # pragma: no cover - defensive
            return text
    return text
