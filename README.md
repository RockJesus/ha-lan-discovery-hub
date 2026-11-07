# LAN Discovery Hub

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
![HA Version](https://img.shields.io/badge/Home%20Assistant-2026.10%2B-03A9F4)

给 Home Assistant 补上官方「发现」看不见的那一块：**把局域网里所有设备收进一张台账，
并告诉你每台设备该用哪个集成接入——包括你还没装过的第三方集成。**

官方发现只对「镜像里已有 manifest 的集成」生效：core 集成本来就能发现，
真正漏掉的是从未下载过的第三方自定义集成，以及没有任何集成认领的设备。
本集成用 mDNS + SSDP + TCP/ARP 三个通道把这些设备找出来。

**不会自动添加任何设备。**接入动作始终由你确认，符合 HA 的安全模型。

## 它解决什么问题

| 场景 | 官方发现 | 本集成 |
| --- | --- | --- |
| Shelly / ESPHome / Cast / Matter 等 core 集成设备 | ✅ | ✅（并聚合到同一台账） |
| 已安装的第三方自定义集成设备 | ✅ | ✅ |
| **未安装的第三方集成设备**（如 Sonoff/eWeLink） | ❌ 完全不发现 | ✅ 匹配到仓库并引导安装 |
| **没有集成认领的设备**（未知 NAS、摄像头、IoT） | ❌ | ⚠️ 记录 + 标注「未知」，不能接入 |
| 一台设备被多个协议公告（Apple TV 三条记录） | 三条 | **一条**，附带全部服务 |
| 全局清单 / 导出 / 历史 | ❌ | ✅ 侧栏面板 |

## 三个扫描通道

- **mDNS**：复用 HA 自己的 zeroconf 实例，浏览 core 生成表里的全部服务类型，
  外加 `_smb` / `_http` / `_https` / `_afpovertcp` / `_nfs` / `_ssh` 等官方不映射的类型。
- **SSDP / UPnP**：主动 `M-SEARCH`（`ssdp:all` + 常用 ST），并读取 device description
  拿到 friendlyName / manufacturer / model。不占用 1900 端口，不与官方 ssdp 抢 socket。
- **TCP 探测 + ARP 缓存**：对已发现的 IP 试 15 个常见端口做指纹，并读取
  `/proc/net/arp` 补上 MAC —— 这是把「mDNS 的一条」「SSDP 的一条」「ARP 的一条」
  合并成一体的关键。

可选的「全网段扫描」会对本机 `/24` 逐主机探测 80/443/22，默认关闭。

## 三态与动作

| 状态 | 含义 | 面板动作 |
| --- | --- | --- |
| 已接入 | device registry 里已有这台设备 | — |
| 可接入 | 集成已在镜像里（core 或已装） | **配置接入**：直接拉起该集成的官方 config flow |
| 需安装集成 | 匹配到第三方集成但本地没有 | **安装集成**：调用内置 Marketplace 安装（需确认，装完提示重启）/ 安装说明 |
| 未知设备 | 没有任何集成认领 | 只能记录；给出手动排查建议 |

「配置接入」不会静默创建配置项：它启动目标集成的 flow，然后把你带到
**设置 → 设备与服务**，在那里完成剩余的步骤。你始终是决定者。

## 面板

侧栏 **局域网发现**：设备列表（名称 / IP / MAC / 协议 / 建议集成 / 状态），
支持按名称、IP、MAC、集成筛选，可重新扫描、全网段扫描、标记已处理、移除。

`sensor.lan_discovery_hub_discovered_devices` 只保留汇总数字与需要关注的设备，
完整清单在面板里。

## 通知

新设备进入「可接入 / 需安装集成」时，发一条**汇总**持久通知
（「发现 3 台可接入设备」+ 前 8 台），不再逐台刷屏，也不再塞满 Repairs。

## 安装

HACS → 自定义存储库 → 类别 `Integration` → 填入本仓库 → 安装 → 重启 HA →
设置 → 设备与服务 → 添加集成 → **LAN Discovery Hub**。

手动安装：复制 `custom_components/lan_discovery_hub/` 到配置目录同名路径，重启。

首次扫描在启动约 20 秒后开始，之后按选项里的间隔（默认 300 秒）重复。

## 自定义映射

想让某类指纹指向你自己的集成，在配置目录放 `lan_discovery_hub_map.json`：

```json
[
  {
    "source": "mdns",
    "kind": "_mydevice._tcp.local.",
    "name": "*",
    "domain": "my_integration",
    "integration": "My Integration",
    "repo": "owner/repo"
  }
]
```

`source` 可为 `mdns` / `ssdp` / `probe` / `arp`，`kind` 支持 fnmatch 通配，
可选的 `props` 用于匹配 TXT 记录（例如 `{"type": "*"}`）。用户映射优先级最高，
其次是 core 生成表，最后是内置的 `integration_map.json`。

## 已知限制

- **没有集成认领的设备无法接入。**HA 没有通用设备驱动，本集成只能把它记进台账。
- **不做 ICMP 扫段。**容器通常没有 `NET_RAW`，用 TCP connect 代替。
- **不做 Wi‑Fi 邻近扫描。**系统接口给不到周边 AP/STA 列表；BLE 请用官方 `bluetooth`。
- **ARP 只能读缓存**，不是主动发现；DHCP 被动嗅探排在 0.2.1。
- 内置 `integration_map.json` 只收录已验证的第三方映射，需要持续人工补充。

## 故障排查

- 面板空白：确认集成已加载、`http` 已启动；浏览器强制刷新（模块有缓存）。
- 设备过多：在选项里加忽略的 mDNS 服务类型，或关闭 TCP 探测。
- 「安装集成」失败：HA 2026.11 起 Marketplace 取代 HACS；旧版本请到 HACS 手动安装。

## License

MIT
