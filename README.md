# LAN Discovery Hub

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
![HA Version](https://img.shields.io/badge/Home%20Assistant-2026.10%2B-03A9F4)

> English summary: LAN Discovery Hub fills the gap left by Home Assistant's built-in discovery —
> it lists every device on the LAN (mDNS, SSDP, TCP/ARP, MQTT, Bluetooth, serial), merges each
> device into one row, and tells you which integration can add it, including third-party
> integrations you have not installed yet. The sidebar panel and notifications are bilingual
> (English / 简体中文) and follow your Home Assistant language. It never adds anything without
> your confirmation.


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

### 0.9.2

- **中英双语**：侧栏面板、汇总通知、设备渠道/端口/协议依据、候选集成打分理由全部随 Home Assistant 的语言切换（英文 / 简体中文）。Runtime 文案集中在 `i18n.py`，面板文案在 `STRINGS` 表里，config flow / 实体 / 服务仍走 `translations/`。
- README 顶部补英文摘要。

### 0.9.1

- 建议打分收紧：只用「服务类型 / 厂商 / 型号」作为匹配词元，不再拿用户起的设备名去撞描述；补充去噪词表（limited、electronics、intelligent、group、sync、helper 等）。
- 「服务类型出现在标签里」加权到 8 分，域名同源 24 分；厂商域名命中 16 分，避免 `climate_group_helper` 这类词根撞车。

### 0.9.0

- **集成目录**：内置拉取市场同源目录（HACS 数据源，约 5000 个集成，含 domain、描述、下载量、星标、仓库地址），缓存 24 小时，断网时继续用旧副本。面板会显示目录条数与更新时间。
- **按设备类型给建议**：把设备的 mDNS 服务类型、SSDP model/manufacturer、端口、厂商、型号拆成词元，和市场目录的域名/标签/描述比对打分——指纹命中 > 服务类型同名 > 域名关键词 > 标签 > 描述 > 热度。每台设备最多给 5 个候选，并写明依据。
- **多选安装**：每行新增「N 个候选」，点开是候选列表（集成图标、★星标、⤓下载量、匹配依据、已安装标记），可勾选多个后一次安装；安装仍是逐个走 Marketplace，完成提示重启。
- 新增 WS：`lan_discovery_hub/catalog`（按关键词搜目录）、`lan_discovery_hub/catalog/refresh`（立刻重拉）。

### 0.8.2

- **手机端可用**：面板在窄屏（<760px）切换成卡片列表，不再把六列表格硬塞进手机，徽章、建议依据、操作按钮都能正常读。
- 标题旁新增「‹ 返回」：Companion App 从侧栏进入面板后，点它回上一页；没有历史时落到 `/lovelace`。

### 0.8.1

- **MAC 厂商标注**：内置 IEEE OUI 全表（45,192 个前缀，来自 nmap-mac-prefixes），ARP/探测/蓝牙行只要有 MAC 就能显示厂商（实测 Synology Incorporated、Huawei Technologies 等）。官方发现没有 OUI 库，这一点是纯增量。
- 面板设备名下方优先显示厂商，其次才是广播里的 manufacturer / model / 线索行。

### 0.8.0

- **mDNS 全类型枚举**：启动时先向 `_services._dns-sd._udp.local.` 发一条 meta 查询，把网络里**实际在用的每一个服务类型**都加进浏览列表（上限 80 个）。官方发现只浏览它自己编译表里认识的那几十种，所以打印机、NAS、各家 SDK 的私有服务类型在官方侧根本不会出现。
- mDNS 观察记录额外带上 TXT 里的 `manufacturer` / `mn` / `vendor`，面板的设备名下方可以直接看到厂牌。
- 通道状态新增 `mdns` 项，报告当前浏览的服务类型数量。

### 0.7.1

- 旧版本留下的建议（当时还没记录依据）现在标「历史判定 · 本轮未复现」，不再出现只有名字、没有出处的行；设备下次再广播相同指纹时会自动换成实时依据。

### 0.7.0

- **「建议集成」现在带依据**：每行下方显示判定来源（`mDNS _nut._tcp.local.`、`SSDP MediaRenderer`、`端口 445（SMB 文件共享）`…），多协议互证时追加「N 种协议互证」。
- **证据仲裁取代「先到先得」**：同一台设备的多条指纹会累积成候选，按「服务类型 > 端口推测」、再按可达状态、再按互证协议数排序，最后才决定建议；不再由最先到的那条包拍板。
- **端口推测分级**：仅凭端口得出的建议标为「推测 · 」，且**只在对应集成已安装时**才置为「可接入」；集成没装时保留「未知设备」，绝不引导安装一个靠端口猜出来的集成。
- 仅靠端口的设备，地址下会写「端口 3493（NUT 监控服务）」这类带服务名的说明。

### 0.6.2

- 「按协议分组」默认关闭，面板首屏回到平铺列表；需要看渠道分布时在工具栏勾选即可。

### 0.6.1

- **「配置」直接进对应集成的配置入口**：不再跳到「设备与服务」总览页，而是打开 `/config/integrations/integration/<domain>`。该页顶部就是这台设备的「已发现」条目和「添加」按钮，点一下即可进入配置流程。
- 「安装说明」改成面板内弹窗，并给一个可点的「去 Marketplace」。

### 0.6.0

- **协议列改成看得懂的话**：不再直接怼 `advertisement` / `neighbor` / `_mass._tcp.local.`，改为「蓝牙广播」「ARP」「mDNS」「SSDP」「端口探测」「MQTT」这些标签，下面再列短路点（mDNS 服务名、探测到的端口）。

### 0.5.9

- 只有 ARP 邻居表的设备（`arp:neighbor`）归到「局域网 · ARP 邻居」，不再落进「未分类」。

### 0.5.8

- **没有 IP 的设备不再只剩一串 MAC**：面板按发现渠道分组（mDNS / SSDP / 探测 / MQTT / 蓝牙 / 串口），地址栏如实写「无 IP」，名字下面补一行可读线索（MQTT 的厂商或型号、蓝牙的信号强度 dBm）。分组开关在工具栏，默认开启。

### 0.5.7

- **把 `_2` 后缀改回干净 id**：删掉遗留传感器后，幸存的那个仍带着 Home Assistant 追加的 `_2`。setup 时若原 id 已空出来，自动把实体改名回 `sensor.lan_discovery_hub_discovered_devices`。

### 0.5.6

- **清理遗留的汇总传感器**：早期版本的 `unique_id` 是 `<entry>_discovered_devices`，现在换成了 `<entry>_devices`，旧实体因此永久显示「不可用」，新实体还被挤成 `_2`。setup 时自动移除这类遗留实体，只保留一个。

### 0.5.5

- **补 0.5.4 的判据**：service kind 实际是 `_mass._tcp.local.` 这样的完整类型串，直接拿去和名字比永远不相等。现在把类型串拆成裸词（`mass` / `matter`）再比较，`mass` 这类名字才真正降级。

### 0.5.4

- **名字等于协议服务名的一律降级**：`_mass._tcp.local` 会把实例名播成 `mass`，这同样不是设备名。现在凡是与记录里的 service kind 字面相同的候选都按最低质量处理，最终回落到 IP（写入路径也不会采纳它）。

### 0.5.3

- **修 hassfest 的 DEPENDENCIES 报错**：蓝牙与 MQTT 扫描器通过 `homeassistant.components.bluetooth` / `.mqtt` 懒加载，但 manifest 里没声明依赖，hassfest 因此判红。两路都是可选通道，改用 `after_dependencies` 声明，缺这两个集成时只是通道降级，不会拖住启动。

### 0.5.2

- **修命名回退**：Matter 这次把 `AE774E6EA872D696-000000000001B669` 当成 announced name 播出来，`_apply()` 写入新名字时没做质量比较，把原来的可读名顶掉了。现在写入前也比质量，纯机器句柄一律降级（最终回落到 IP）。

### 0.5.1

- **修 0.5.0 的成功判断**：`repository/info` 里的 `installed` 是布尔值，版本号在 `installed_version`；混用之后比较永远不成立，轮询照样走过 24 次也不给结论。现在分开取值，并用 `pending_upgrade` 兜住「已装但待升级」的情形。

### 0.5.0

- **修 0.4.9 的轮询空转**：`marketplace/repository/info` 的 `repository_id` 必须是字符串，传数字会被拒（`expected str at 'repository_id'`），异常又被静默忽略，于是面板一直停在「正在安装…」。现在统一转字符串再查。

### 0.4.9

- **安装成功不再等 install 的回复**：真机实测 Marketplace 的 `repository/install` 可以几分钟都不回包（仓库其实已写好），面板会卡在「正在安装…」。现在改为每 15 秒查一次 `repository/info`，看到 `installed == available` 或 `pending-restart` 就给出「已安装，请重启 Home Assistant 后再点「配置」」。

### 0.4.8

- **修 0.4.7 的致命回归**：动作分发里 `if (!device) return` 排在弹窗按钮之前，弹窗的「取消/继续」点了没反应（按钮不带 device_id）。现在弹窗分支前置，取消/继续真正生效。

### 0.4.7

- **所有确认改为面板内弹窗**：安装第三方集成、隐藏设备、全网段扫描这三处原来用原生 `confirm()`，在伴侣 App 里会被拦截（点了没反应）。现在统一用面板自己的弹窗，标题 + 说明 + 取消/继续。
- **清空改名立即生效**：留空恢复自动命名时当场重算，不用等下一轮扫描。
- 配置按钮回到 `/config/integrations`（HA 会丢弃 `?domain=` 参数，那页的「已发现」卡片才是落点）。

### 0.4.6

- **修 0.4.5 引入的回归**：扫描时写入名字的两处代码（`_apply` 与合并路径）没有避让人工命名，导致设过的
  `FNOS` 在下一轮扫描里又被改回 `飞牛音乐-Lite`。现在任何观测都不再覆盖用户设的名字。

### 0.4.5

真浏览器逐个点按钮后的一轮修补：

- **改名改为面板内对话框**：手机 App / 部分浏览器会拦截原生 `prompt()`，点「改名」没反应。现在用内置弹窗 + 回车确认、Esc 取消。
- **移除不再"删了又回来"**：之前的移除只是把记录从台账删掉，下次扫描又出现。现在移除 = 隐藏（记录继续跟踪），工具栏新增「显示已忽略（n）」，隐藏的行给出「恢复」。
- **配置跳准**：创建配置流程后跳到 `/config/integrations?domain=<集成>`，直接落在对应集成页，而不是空白的总览页。
- 操作列 19%→23% 且按钮更紧凑，四个按钮（配置/已处理/改名/移除）回到一行。
- 新增 WebSocket 命令 `lan_discovery_hub/restore`；`devices` 支持 `include_ignored`。

### 0.4.4

- AirPlay 下发的实例名形如 `4d3fa0f5-airplay-5`（16 进制前缀 + 服务后缀），既不是纯 16 进制也不带冒号，
  之前会被当成可读名字。现在与 Matter 节点 id 一样按机器句柄降级。

### 0.4.3

- **面板可手动改名**（操作列新增「改名」）：有些盒子自己就宣告两个同样合法的名字（如 NAS 同时报 `fnos`
  与音乐服务的 `飞牛音乐-Lite`），自动识别只能二选一且会随扫描摆动。手动命名一旦设置就永久压过自动命名，
  留空即恢复自动。名字写入存储，重启后仍在。
- 新增 WebSocket 命令 `lan_discovery_hub/rename`，供面板与脚本调用。

### 0.4.2

- 机器串识别扩展到 `AE774E6EA872D696-0000000` 这类带后缀的形式（Matter / Thread 节点 id 的常见写法），
  它们与纯 16 进制串同样按噪声处理。

### 0.4.1

- **实例名永不胜出**：同一台设备上，来自协议实例的名字（AirPlay/DLNA 的 `飞牛音乐-Lite`）在评分里固定排在
  器件自身名字之后。之前 NAS（192.168.1.49）的名字会在 `FNOS` 与 `飞牛音乐-Lite` 之间随扫描变化来回翻。

### 0.4.0

- 操作列加宽到 19%，"配置 / 已处理 / 移除"三个按钮在可接入设备行里回到同一行。

### 0.3.9

- 0.3.8 的"按来源层级加权"在真机上反而更糟：Apple TV 的 UPnP friendly name 是默认值 `computer`，
  HA 主机名是 `74563ca029490000`，两者都被加权成了设备名。改为按"名字本身是否可信"降级：
  默认名（computer / localhost / device / nas …）与纯 16 进制串一律当噪声（quality=1），
  其余仍按"被几种协议同时承认"排序。真机结果：`客厅电视` / `Home Assistant` / `FNOS` 三个都正确。

### 0.3.8

- 命名按"名字来源的层级"加权：宿主名 4、SSDP friendly name 3、常规协议 2、媒体服务实例名 1。
  真机上 NAS（192.168.1.49）曾被 AirPlay 实例名「飞牛音乐-Lite」抢走整台设备的名字，现在回到 `FNOS`。
- 操作列文案缩短（配置 / 已处理 / 移除），三个按钮回到一行。

### 0.3.7

- 面板模块 URL 带版本号（`...panel.js?v=<version>`）。0.3.6 修了布局但真机上浏览器仍渲染旧版本，
  因为 `module_url` 是固定路径、浏览器按旧缓存加载。

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
