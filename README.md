# LAN Discovery Hub

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
![HA Version](https://img.shields.io/badge/Home%20Assistant-2026.10%2B-03A9F4)

监听局域网 mDNS 广播，发现新设备时通过 **Repairs（修复）** 提示用户，并给出建议接入的集成。
**不会自动添加任何设备**——接入动作始终由用户确认，符合 HA 安全架构。

## 功能

- 监听 10 种常见 mDNS 服务类型（Cast / HomeKit / ESPHome / Shelly / Tuya / Matter / IPP 等）
- 新设备 → `Repairs` 弹提示（含建议集成的名称）
- `sensor.lan_discovery_hub_discovered_devices`：已发现设备数 + 清单属性
- 动作 `lan_discovery_hub.acknowledge`：确认设备（消除对应修复提示）
- 选项页可配置忽略的服务类型
- 诊断接口自动脱敏 token / password

## 安装（HACS）

1. HACS → 自定义存储库 → 类别选 `Integration` → 填入本仓库地址
2. 安装后重启 Home Assistant
3. 设置 → 设备与服务 → 添加集成 → 搜索 **LAN Discovery Hub**

## 手动安装

复制 `custom_components/lan_discovery_hub/` 到 HA 配置目录同名路径下，重启。

## 已知限制

- 目前只覆盖 mDNS（zeroconf）；SSDP / DHCP 通道规划中
- 服务类型匹配是「提示」而非接入，不代替各集成的 config flow

## License

MIT
