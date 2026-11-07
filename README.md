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
- **ARP 只能读缓存**，不是主动发现；DHCP 被动嗅探仍在评估。
- 内置 `integration_map.json` 只收录已验证的第三方映射，需要持续人工补充。

## 版本记录

### 0.3.6

- 面板表格改为固定列宽：状态徽章不再被压成竖排两行，操作按钮不再挤成三行，
  设备名 / 厂商行不再与地址列互相压字（真机截图发现，之前只有端点 200 的验证是看不出这类问题的）。

### 0.3.5

- **串口 / USB 适配器通道**：读 `/dev/serial/by-id` 与 `/sys/bus/usb/devices`（只读，不打开端口，
  避免复位正在工作的协调器），按 by-id 名称与 USB id 认出 Sonoff Zigbee / SkyConnect / ConBee / Aeotec Z-Stick 等，
  并给出对应的 ZHA / Z-Wave JS。认不出型号的端口照样列出，只是不指定集成。
- 通道状态同样写进 `channels.serial`，没插适配器时说明是"看不到串口映射"而不是静默无记录。

### 0.3.4

- MQTT 台账只收真实设备：`tag`（MQTT 标签扫描器，转发 NFC/二维码扫描）、`device_automation`、`scene`、`script`
  这类"能力宣告"不再被当成待接入设备。

### 0.3.3

- **通道晚于本集成就绪时的自愈**：config entry 可能先于 mqtt / bluetooth 完成建立，
  之前会一直报 `mqtt_not_setup_cannot_subscribe` 直到重启；现在每轮扫描前重试订阅与扫描器检测。
- **推送型记录会随宣告消失**：只被 MQTT 或 BLE 看见、且该通道已不再报告的记录会被清理，
  不会永远留在台账里（旧版本遗留的 18 条 MQTT 记录会因此自动收敛）。

### 0.3.2

- **MQTT 设备按"设备"归并，不再按实体**：一台机器在 broker 上宣告 14 个传感器，
  之前会变成 14 条记录（实测 18 条里 14 条都叫 ROCKJESUSPC）。识别键改用设备级 identifier（node_id 兜底），
  同一台设备的多个实体合回一条。
- 蓝牙通道的原因文案区分"未配置适配器"与"配了但当前不在线"。

### 0.3.1

- 面板 payload 增加 `channels`：蓝牙与本机 broker 两条通道是否就绪、失败原因原文，
  不必再翻日志才知道"为什么没有蓝牙设备"。

### 0.3.0

- **蓝牙（BLE）通道**：读 HA 蓝牙管理器里已缓存的广播（本地适配器或 ESPHome 代理都算），
  按厂商 ID 匹配 `xiaomi_ble` / `switchbot` / `ruuvitag_ble` / `qingping`；只保留带名字或厂商数据的广播，
  15 分钟前的缓存丢弃，避免手机随机地址堆积。
- **MQTT discovery 通道**：订阅 broker 上 `<prefix>/<component>/[node]/<object>/config`，
  把「已在 broker 宣告、HA 还没接手」的设备列出来（Tasmota / Zigbee2MQTT / MQTT 模式 ESPHome 都属于这类）。
  复用 HA 自己的 broker 连接，不另开客户端、不碰凭据。
- 两个新通道都并入同一个台账：BLE 用 MAC 与局域网记录自动合并，MQTT 用 `uniq_id` / 设备 identifiers 判定是否已配置。

### 0.2.7

- SSDP 的复合标识（`uuid:…::upnp:rootdevice`、`urn:schemas-upnp-org:…`）整体算作机器串。
  设备名里不会出现冒号，所以带冒号的一律不采用，没真名就显示 IP。

### 0.2.6

- SSDP 的 `uuid:…` 设备标识符不再被当成可读名字（之前它因带 `uuid:` 前缀绕过了 UUID 判断），
  这类设备在没有真名时直接显示 IP。

### 0.2.5

- **每轮扫描后都会汇总一次。**之前只在「发现新设备」时才弹通知，重启后已有待接入设备也不再提醒；
  现在扫描结束就更新同一条 `lan_discovery_hub_devices` 通知（同 id，不堆叠），全部处理完自动消失。
- **实在没有名字的设备用地址代替**，不再显示一串 UUID。

### 0.2.4

- **名字按「谁被更多协议承认」来定。**同一台 NAS 同时公告 `FNOS`（nut/smb）和
  `飞牛音乐-Lite`（airplay），后者只是它的一个投屏服务；现在多协议一致的名字优先，
  单一服务实例名不再抢走设备名。通知发出前也会先做一次整理，避免推出去的名字让人认不出。

### 0.2.3

- **设备名在首轮之后继续修正。**UUID 形态的实例名（HomeKit id、Matter pairing id）
  会让位给 mDNS 主机名（`rockde-ipad` 好过一串 hex）；已在台账里的旧名字也会在下一轮
  扫描后按现有证据重新挑一次，不用手工改名，也不用删库重建。

### 0.2.2

- **只看你自己的局域网。**HA 容器内部网络（supervisor `172.30.32.0/23`、
  docker 桥 `172.17.0.0/16`、回环、link-local）里的 ARP 记录不再进台账，
  已经建出来的这类空壳记录会在每轮扫描后自动清理。
- **设备名不再被机器串占住。**SSDP 的 `UPnP devices/1.8.4` 服务器横幅不再当名字；
  名字会随更好的证据自动升级（UUID → mDNS 主机名 → friendlyName / 型号）。

### 0.2.1（在真实 HA 2026.11.0 上跑通后修的三处）

- **修聚合崩塌。**0.2.0 里 ARP 邻居行和 TCP 端口探测用的是固定标签
  （`arp:neighbor:arp`、`probe:tcp:open-ports`），所有设备共用一个识别键，
  结果把整个网络的设备并成了一条记录。现在只有真正公告的服务实例
  （mDNS 实例名、SSDP USN）参与识别，合成观测一律按 IP/MAC 匹配。
- **IP 复用时不再错误合并。**当观测带 MAC、而命中记录是另一个 MAC 时，
  视为两台设备（DHCP 租约换手），并清掉指向旧地址的过期索引。
- **面板安装调用修正。**2026.11 的 `marketplace/repository/install`
  不接受 `warning_accepted` 参数（会直接 `invalid_format`）；
  同时新增「仓库不在 Marketplace 时先自动添加再安装」的流程。
- 台账存储换到 `lan_discovery_hub.registry.v3`，0.2.0 那份被错误合并的数据
  不再沿用，首次启动会重新扫描重建（确认过的「已处理」标记需要重新标）。

## 故障排查

- 面板空白：确认集成已加载、`http` 已启动；浏览器强制刷新（模块有缓存）。
- 设备过多：在选项里加忽略的 mDNS 服务类型，或关闭 TCP 探测。
- 「安装集成」失败：HA 2026.11 起 Marketplace 取代 HACS；旧版本请到 HACS 手动安装。

## License

MIT
