const STRINGS = {
  "en": {
    "title": "LAN Discovery",
    "back": "‹ Back",
    "back_title": "Back to Home Assistant",
    "total": "{total} devices · Sources: {sources}",
    "sources_none": "none",
    "last_scan": "· last scan {time}",
    "busy": "· working…",
    "state_configured": "Connected",
    "state_available": "Ready",
    "state_installable": "Needs integration",
    "state_unknown": "Unknown",
    "filter": "Filter by name / IP / MAC / integration",
    "rescan": "Rescan",
    "sweep": "Full sweep",
    "services": "Devices & services",
    "group_toggle": "Group by protocol",
    "group_hint": "Group by discovery channel so MQTT / Bluetooth devices without an IP stay readable",
    "show_ignored": "Show ignored",
    "show_ignored_hint": "Also list hidden devices",
    "load_failed": "Could not load: {error}",
    "empty": "No devices yet. The first scan starts about 20 seconds after setup; you can switch channels in the options.",
    "th_device": "Device",
    "th_addr": "Address",
    "th_proto": "Protocol",
    "th_sugg": "Suggested integration",
    "th_state": "State",
    "th_acts": "Actions",
    "sweep_title": "Full sweep",
    "sweep_body": "Every host in this /24 is probed one by one; it takes about 1–2 minutes and the panel may slow down.",
    "sweeping": "Sweeping the whole subnet…",
    "scanning": "Scanning…",
    "scan_done": "Scan finished",
    "hide_title": "Hide “{name}”",
    "hide_body": "It is still tracked, just hidden from the list; tick “Show ignored” to bring it back.",
    "hidden": "“{name}” hidden; tick “Show ignored” to restore it.",
    "restored": "“{name}” restored.",
    "no_integration": "No integration matched this device yet.",
    "renamed": "Renamed “{old}” to “{name}”; automatic naming will no longer override it.",
    "rename_cleared": "Manual name cleared; automatic naming restored.",
    "rename_failed": "Rename failed: {err}",
    "rename_title": "Name “{name}”",
    "rename_hint": "This name always wins over automatic naming; leave it empty to go back to automatic.",
    "ok": "OK",
    "cancel": "Cancel",
    "continue": "Continue",
    "pick_title": "Candidate integrations for “{name}”",
    "pick_hint": "{total} integrations in the marketplace catalog, ordered by how well they fit this device. Tick several to install them in one go; Home Assistant must be restarted afterwards.",
    "pick_install": "Install selected ({count})",
    "installed": "Installed",
    "pick_none": "Nothing selected.",
    "install_many": "Installing {count} integration(s)…",
    "install_at": "Installing {i}/{total}: {name}…",
    "install_summary": "Installed {ok} integration(s){failed}. Restart Home Assistant, then press “Configure”.",
    "install_unconfirmed": "Install not confirmed: {failed}. Check the Marketplace for progress.",
    "failed_tail": ", {count} unconfirmed ({names})",
    "all_failed": "all failed",
    "no_repo": "This device has no known third-party repository; search the Marketplace manually.",
    "install_confirm_title": "Install “{name}”",
    "install_confirm_body": "It will be installed from {repo}; Home Assistant must be restarted afterwards.",
    "install_msg": "Installing; this can take a few minutes…",
    "looking": "Looking for {repo} in the Marketplace…",
    "no_market": "This Home Assistant has no usable Marketplace API ({err}). Install {repo} manually, or through HACS.",
    "adding": "{repo} is not in the Marketplace yet; adding it as a custom repository…",
    "not_found": "{repo} was not found in the Marketplace. Search “{name}” and install it manually.",
    "refreshing": "Refreshing repository information…",
    "already_installed": "“{name}” is installed. Restart Home Assistant, then press “Configure”.",
    "submitted": "The install request for “{name}” was submitted; if nothing appears after a few minutes, check the Marketplace.",
    "install_failed": "Install failed: {err}. Install {repo} manually from the Marketplace.",
    "units": "{count} devices",
    "group_row": "{label} · {count} devices",
    "port_token": "Ports {ports}",
    "port_probe": "Port probe",
    "ble_adv": "BLE advertisement",
    "serial": "Serial",
    "act_restore": "Restore",
    "act_configure": "Configure",
    "act_install": "Install integration",
    "act_manual": "Install notes",
    "act_blocked": "Can't add",
    "blocked_title": "No integration matched",
    "act_ack": "Handled",
    "act_rename": "Rename",
    "rename_title_btn": "Manual name; automatic naming will not override it",
    "act_forget": "Remove",
    "ignored": "Ignored",
    "no_ip": "no IP",
    "addr": "Address",
    "proto": "Protocol",
    "sugg": "Suggested",
    "support": " · confirmed by {count} protocols",
    "view_candidates": "View {count} candidate integrations",
    "cand_n": "{count} candidates",
    "downloads": "{count} downloads",
    "manual_title": "Install notes",
    "manual_repo": "{name} comes from {repo}. Use “Install integration” here (it calls the Marketplace), or search the Marketplace, or add the repository in HACS. Home Assistant must be restarted afterwards.",
    "manual_none": "No known integration matched. Search the Marketplace by brand/model, or check the device documentation for an existing Home Assistant integration.",
    "go_market": "Go to Marketplace",
    "this_device": "this device",
    "uncategorised": "Uncategorised"
  },
  "zh": {
    "title": "局域网发现",
    "back": "‹ 返回",
    "back_title": "回到 Home Assistant",
    "total": "共 {total} 台设备 · 来源：{sources}",
    "sources_none": "未启用",
    "last_scan": "· 上次扫描 {time}",
    "busy": "· 正在处理…",
    "state_configured": "已接入",
    "state_available": "可接入",
    "state_installable": "需安装集成",
    "state_unknown": "未知设备",
    "filter": "按名称 / IP / MAC / 集成筛选",
    "rescan": "重新扫描",
    "sweep": "全网段扫描",
    "services": "设备与服务",
    "group_toggle": "按协议分组",
    "group_hint": "按发现渠道分组，便于看待没有 IP 的 MQTT / 蓝牙设备",
    "show_ignored": "显示已忽略",
    "show_ignored_hint": "把已隐藏的设备也列出来",
    "load_failed": "读取失败：{error}",
    "empty": "还没有发现设备。首次扫描在启动约 20 秒后开始，也可以在选项里换扫描通道。",
    "th_device": "设备",
    "th_addr": "地址",
    "th_proto": "协议",
    "th_sugg": "建议集成",
    "th_state": "状态",
    "th_acts": "操作",
    "sweep_title": "全网段扫描",
    "sweep_body": "将逐个探测本网段每台主机，耗时约 1–2 分钟，期间面板可能变慢。",
    "sweeping": "正在全网段扫描…",
    "scanning": "正在扫描…",
    "scan_done": "扫描完成",
    "hide_title": "不再显示「{name}」",
    "hide_body": "它仍会被扫描跟踪，只是从列表里隐藏；随时可在工具栏勾选「显示已忽略」恢复。",
    "hidden": "已隐藏「{name}」，勾选「显示已忽略」可恢复。",
    "restored": "已恢复「{name}」。",
    "no_integration": "这台设备还没有匹配到集成。",
    "renamed": "已把「{old}」命名为「{name}」，之后不再被自动识别改掉。",
    "rename_cleared": "已取消手动命名，恢复自动识别。",
    "rename_failed": "改名失败：{err}",
    "rename_title": "为「{name}」起个名字",
    "rename_hint": "这个名字会永久压过自动识别；留空则恢复自动命名。",
    "ok": "确定",
    "cancel": "取消",
    "continue": "继续",
    "pick_title": "「{name}」的候选集成",
    "pick_hint": "来自市场目录 {total} 条集成，按与设备的匹配度排序。勾选后可一次安装多个，装完需要重启 Home Assistant。",
    "pick_install": "安装所选（{count}）",
    "installed": "已安装",
    "pick_none": "没有勾选需要安装的集成。",
    "install_many": "正在安装 {count} 个集成…",
    "install_at": "正在安装 {i}/{total}：{name}…",
    "install_summary": "已安装 {ok} 个集成{failed}。请重启 Home Assistant 后再点「配置」。",
    "install_unconfirmed": "安装未确认：{failed}。请到 Marketplace 查看进度。",
    "failed_tail": "，{count} 个未确认（{names}）",
    "all_failed": "全部失败",
    "no_repo": "这条设备没有已知的第三方仓库地址，只能手动搜索安装。",
    "install_confirm_title": "安装「{name}」",
    "install_confirm_body": "将从仓库 {repo} 安装，安装完成后需要重启 Home Assistant 才会生效。",
    "install_msg": "正在安装，这一步可能需要几分钟…",
    "looking": "正在 Marketplace 中查找 {repo}…",
    "no_market": "当前 Home Assistant 没有可用的 Marketplace 接口（{err}）。请手动安装 {repo}，或通过 HACS 安装。",
    "adding": "Marketplace 里还没有 {repo}，正在添加自定义仓库…",
    "not_found": "Marketplace 里没有找到 {repo}。请在 Marketplace 中搜索「{name}」并手动安装。",
    "refreshing": "正在刷新仓库信息…",
    "already_installed": "「{name}」已安装，请重启 Home Assistant 后再点「配置」。",
    "submitted": "「{name}」的安装请求已提交，若几分钟后仍未出现，请到 Marketplace 查看进度。",
    "install_failed": "安装失败：{err}。请到 Marketplace 手动安装 {repo}。",
    "units": "{count} 台",
    "group_row": "{label} · {count} 台",
    "port_token": "端口 {ports}",
    "port_probe": "端口探测",
    "ble_adv": "蓝牙广播",
    "serial": "串口",
    "act_restore": "恢复",
    "act_configure": "配置",
    "act_install": "安装集成",
    "act_manual": "安装说明",
    "act_blocked": "无法接入",
    "blocked_title": "没有匹配到任何集成",
    "act_ack": "已处理",
    "act_rename": "改名",
    "rename_title_btn": "手动命名，之后不再被自动识别改掉",
    "act_forget": "移除",
    "ignored": "已忽略",
    "no_ip": "无 IP",
    "addr": "地址",
    "proto": "协议",
    "sugg": "建议",
    "support": " · {count} 种协议互证",
    "view_candidates": "查看 {count} 个候选集成",
    "cand_n": "{count} 个候选",
    "downloads": "{count} 次下载",
    "manual_title": "安装说明",
    "manual_repo": "{name} 来自 {repo}。安装方式：本面板的「安装集成」直接调 Marketplace 安装；也可以到 Marketplace 搜索安装，或用 HACS 添加自定义仓库。安装完成后必须重启 Home Assistant。",
    "manual_none": "没有匹配到已知集成。可以到 Marketplace 按设备品牌/型号搜索，或查看设备文档确认是否已有 Home Assistant 集成。",
    "go_market": "去 Marketplace",
    "this_device": "该设备",
    "uncategorised": "未分类"
  }
};

class LanDiscoveryHubPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._devices = [];
    this._counts = {};
    this._meta = {};
    this._loaded = false;
    this._busy = false;
    this._message = "";
    this._filter = "";
    this._showIgnored = false;
    this._grouped = false;
    this._narrow = false;
    this._confirm = null;
    this._picking = null;
    this._catalog = {};
    this._render();
  }

  _t(key, vars) {
    const lang = String((this._hass && this._hass.language) || "en").toLowerCase().startsWith("zh")
      ? "zh"
      : "en";
    const table = STRINGS[lang] || STRINGS.en;
    let text = table[key] ?? STRINGS.en[key] ?? key;
    if (vars) {
      for (const [name, value] of Object.entries(vars)) {
        text = text.split(`{${name}}`).join(String(value ?? ""));
      }
    }
    return text;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._loaded && hass) {
      this._loaded = true;
      this._load();
    }
  }

  connectedCallback() {
    this._applyWidth();
    this._render();
  }

  disconnectedCallback() {
    if (this._onResize) {
      window.removeEventListener("resize", this._onResize);
      this._onResize = null;
    }
  }

  _applyWidth() {
    const narrow = (window.innerWidth || 1024) < 760;
    this._narrow = narrow;
    if (!this._onResize) {
      this._onResize = () => {
        const next = (window.innerWidth || 1024) < 760;
        if (next !== this._narrow) {
          this._narrow = next;
          this._render();
        }
      };
      window.addEventListener("resize", this._onResize);
    }
  }

  // ------------------------------------------------------------------ data

  async _load() {
    if (!this._hass) return;
    try {
      const result = await this._hass.callWS({
        type: "lan_discovery_hub/devices",
        include_ignored: this._showIgnored,
      });
      this._devices = result.devices || [];
      this._counts = result.counts || {};
      this._meta = result || {};
      this._catalog = (result && result.catalog) || this._catalog || {};
      this._error = "";
    } catch (err) {
      this._error = err && err.message ? err.message : String(err);
    }
    this._render();
  }

  async _call(type, payload) {
    this._busy = true;
    this._render();
    try {
      return await this._hass.callWS({ type: `lan_discovery_hub/${type}`, ...payload });
    } finally {
      this._busy = false;
    }
  }

  _scan(full) {
    if (full) {
      this._ask(
        this._t("sweep_title"),
        this._t("sweep_body"),
        () => this._runScan(true)
      );
      return;
    }
    this._runScan(false);
  }

  async _runScan(full) {
    this._message = full ? this._t("sweeping") : this._t("scanning");
    this._render();
    await this._call("scan", { full: Boolean(full) });
    this._message = this._t("scan_done");
    await this._load();
  }

  async _acknowledge(device) {
    await this._call("acknowledge", { device_id: device.device_id });
    await this._load();
  }

  _forget(device) {
    this._ask(
      this._t("hide_title", { name: device.name }),
      this._t("hide_body"),
      async () => {
        await this._call("forget", { device_id: device.device_id });
        this._message = this._t("hidden", { name: device.name });
        await this._load();
      }
    );
  }

  async _restore(device) {
    await this._call("restore", { device_id: device.device_id });
    this._message = this._t("restored", { name: device.name });
    await this._load();
  }

  _integrationUrl(domain) {
    return `/config/integrations/integration/${encodeURIComponent(domain)}`;
  }

  async _configure(device) {
    // HA 的集成详情页会把这个设备的「已发现」条目和「添加」按钮直接摆在最上面，
    // 比落到总览页让人自己找强得多。
    if (device.domain) {
      location.href = this._integrationUrl(device.domain);
      return;
    }
    this._message = this._t("no_integration");
    this._render();
  }

  _rename(device) {
    // A native prompt() is blocked in the companion app and cannot be styled;
    // the panel draws its own small dialog instead.
    this._renaming = device;
    this._renameDraft = device.name_override || device.name || "";
    this._render();
    const field = this.shadowRoot.querySelector("#rename-input");
    if (field) {
      field.focus();
      field.select();
    }
  }

  _cancelRename() {
    this._renaming = null;
    this._renameDraft = "";
    this._render();
  }

  async _commitRename() {
    const device = this._renaming;
    if (!device) return;
    const name = (this._renameDraft || "").trim().slice(0, 64);
    this._renaming = null;
    try {
      await this._hass.callWS({
        type: "lan_discovery_hub/rename",
        device_id: device.device_id,
        name,
      });
      this._message = name
        ? this._t("renamed", { old: device.name, name })
        : this._t("rename_cleared");
    } catch (err) {
      this._message = this._t("rename_failed", { err: err?.message || err });
    }
    await this._load();
  }

  // ------------------------------------------------------------- marketplace

  _findRepository(list, fullName) {
    const items = Array.isArray(list)
      ? list
      : list?.repositories || list?.repos || list?.data || list?.items || [];
    const target = String(fullName || "").toLowerCase();
    if (!target) return null;
    return (
      items.find((item) => {
        const full =
          item?.full_name ||
          item?.repository?.full_name ||
          item?.fullName ||
          item?.name ||
          "";
        return String(full).toLowerCase() === target;
      }) || null
    );
  }

  _ask(title, text, onConfirm, confirmLabel) {
    // Native confirm()/prompt() are blocked in the companion app, so every
    // question this panel asks is drawn by the panel itself.
    this._confirm = { title, text, onConfirm, confirmLabel };
    this._render();
  }

  _closeAsk() {
    this._confirm = null;
    this._render();
  }

  _install(device) {
    const repo = device.repo;
    if (!repo) {
      this._message = this._t("no_repo");
      this._render();
      return;
    }
    this._ask(
      this._t("install_confirm_title", { name: device.integration_name || device.domain }),
      this._t("install_confirm_body", { repo }),
      () => this._runInstall(device)
    );
  }

  async _runInstall(device) {
    const repo = device.repo;
    this._message = this._t("looking", { repo });
    this._render();

    let list;
    try {
      list = await this._hass.callWS({ type: "marketplace/repositories/list" });
    } catch (err) {
      this._message = this._t("no_market", { err: err?.message || err, repo });
      this._render();
      return;
    }

    let entry = this._findRepository(list, repo);
    if (!entry) {
      // The repository is not in the Marketplace yet: adding it is the whole
      // point of this button, otherwise the user is sent looking for it.
      this._message = this._t("adding", { repo });
      this._render();
      try {
        await this._hass.callWS({
          type: "marketplace/repositories/add",
          repository: `https://github.com/${repo}`,
          category: "integration",
        });
        list = await this._hass.callWS({ type: "marketplace/repositories/list" });
        entry = this._findRepository(list, repo);
      } catch (err) {
        console.warn("marketplace add repository failed", err);
      }
    }

    const repositoryId =
      entry?.repository_id ?? entry?.id ?? entry?.repository?.id ?? null;
    if (!entry || repositoryId === null) {
      this._message = this._t("not_found", {
        repo,
        name: device.integration_name || device.domain,
      });
      this._render();
      return;
    }

    this._message = this._t("refreshing");
    this._render();
    try {
      await this._hass.callWS({
        type: "marketplace/repository/refresh",
        repository: repositoryId,
      });
    } catch (err) {
      // Refresh is an optimisation, installation can still be attempted.
      console.warn("marketplace refresh failed", err);
    }

    this._message = this._t("install_msg");
    this._render();

    // The install command can stay unanswered for minutes even though the
    // repository is already written to disk, so success is judged from
    // repository/info, not from the reply.
    let settled = false;
    let failed = false;
    const job = this._hass
      .callWS({ type: "marketplace/repository/install", repository: repositoryId })
      .then(() => {
        settled = true;
      })
      .catch((err) => {
        settled = true;
        failed = true;
        this._message = this._t("install_failed", { err: err?.message || err, repo });
        this._render();
      });

    const label = device.integration_name || device.domain;
    for (let attempt = 0; attempt < 24 && !settled; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 15000));
      try {
        const info = await this._hass.callWS({
          type: "marketplace/repository/info",
          // The websocket schema wants a string; a numeric id is rejected.
          repository_id: String(repositoryId),
        });
        // `installed` is a boolean, the version itself is installed_version;
        // mixing the two makes the comparison never succeed.
        const installed = info?.installed_version || null;
        const available = info?.available_version || null;
        if (installed && (installed === available || info?.status === "pending-restart" || (info?.installed === true && !info?.pending_upgrade))) {
          this._message = this._t("already_installed", { name: label });
          this._render();
          return;
        }
        if (info?.status === "pending-restart") {
          this._message = this._t("already_installed", { name: label });
          this._render();
          return;
        }
      } catch (err) {
        // Keep polling: a transient failure here does not mean install failed.
      }
    }
    if (!failed) {
      this._message = this._t("submitted", { name: label });
      this._render();
    }
    await job;
  }

  // ------------------------------------------------------------------ view

  _rows() {
    const filter = this._filter.trim().toLowerCase();
    return this._devices.filter((device) => {
      if (!filter) return true;
      const haystack = [
        device.name,
        device.ip,
        device.mac,
        device.host,
        device.integration_name,
        device.domain,
        (device.hints || []).join(" "),
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return haystack.includes(filter);
    });
  }

  _groupedRows(rows) {
    const groups = new Map();
    for (const device of rows) {
      const key = device.channel_label || this._t("uncategorised");
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(device);
    }
    return [...groups.entries()]
      .sort((a, b) => b[1].length - a[1].length)
      .map(
        ([label, items]) =>
          `<tr class="group"><td colspan="6">${this._t("group_row", { label, count: items.length })}</td></tr>` +
          items.map((device) => this._row(device)).join("")
      )
      .join("");
  }

  _badge(device) {
    const map = {
      configured: [this._t("state_configured"), "#0b8043"],
      available: [this._t("state_available"), "#1e88e5"],
      installable: [this._t("state_installable"), "#f9a825"],
      unknown: [this._t("state_unknown"), "#757575"],
    };
    const [label, color] = map[device.state] || map.unknown;
    return `<span class="badge" style="background:${color}">${label}</span>`;
  }

  _serviceSummary(device) {
    const services = Object.values(device.services || {});
    const tokens = new Set();
    const labels = [];
    for (const service of services) {
      const source = service.source || "";
      const kind = service.kind || "";
      if (source === "mdns") {
        const name = kind.replace(/^_/, "").replace(/\.(?:_tcp|_udp)\.local\.?$/, "");
        if (name) tokens.add(name);
        if (!labels.includes("mDNS")) labels.push("mDNS");
      } else if (source === "ssdp") {
        if (!labels.includes("SSDP")) labels.push("SSDP");
      } else if (source === "probe") {
        const ports = (service.props && service.props.ports) || [];
        if (ports.length) tokens.add(this._t("port_token", { ports: ports.slice(0, 3).join("/") }));
        if (!labels.includes(this._t("port_probe"))) labels.push(this._t("port_probe"));
      } else if (source === "ble") {
        if (!labels.includes(this._t("ble_adv"))) labels.push(this._t("ble_adv"));
      } else if (source === "mqtt") {
        if (!labels.includes("MQTT")) labels.push("MQTT");
      } else if (source === "arp") {
        if (!labels.includes("ARP")) labels.push("ARP");
      } else if (source === "serial") {
        if (!labels.includes(this._t("serial"))) labels.push(this._t("serial"));
      }
    }
    const head = labels.join(" / ") || "—";
    const tail = [...tokens].slice(0, 4).join(", ");
    return tail ? `${head}<div>${tail}</div>` : head;
  }

  _actions(device) {
    const parts = [];
    if (device.ignored) {
      parts.push(`<button data-act="restore" data-id="${device.device_id}">${this._t("act_restore")}</button>`);
      return parts.join("");
    }
    if (device.state === "available" && device.domain) {
      parts.push(`<button data-act="configure" data-id="${device.device_id}">${this._t("act_configure")}</button>`);
    }
    if (device.state === "installable" && device.domain) {
      if (device.repo) {
        parts.push(`<button class="primary" data-act="install" data-id="${device.device_id}">${this._t("act_install")}</button>`);
      }
      parts.push(`<button data-act="manual" data-id="${device.device_id}">${this._t("act_manual")}</button>`);
    }
    if (device.state === "unknown" && device.ip) {
      parts.push(`<button data-act="configure" data-id="${device.device_id}" disabled title="${this._t("blocked_title")}">${this._t("act_blocked")}</button>`);
    }
    if (!device.acknowledged) {
      parts.push(`<button data-act="ack" data-id="${device.device_id}">${this._t("act_ack")}</button>`);
    }
    parts.push(`<button class="ghost" data-act="rename" data-id="${device.device_id}" title="${this._t("rename_title_btn")}">${this._t("act_rename")}</button>`);
    parts.push(`<button class="ghost" data-act="forget" data-id="${device.device_id}">${this._t("act_forget")}</button>`);
    return parts.join("");
  }

  _render() {
    if (!this.shadowRoot) return;
    this._applyWidth();
    const counts = this._counts || {};
    const rows = this._rows();
    const total = this._meta?.total ?? this._devices.length;

    this.shadowRoot.innerHTML = `
      <style>
        :host { display:block; padding:16px; color: var(--primary-text-color); }
        h1 { font-size: 20px; font-weight: 500; margin: 0 0 4px; }
        .sub { color: var(--secondary-text-color); font-size: 13px; margin-bottom: 14px; }
        .cards { display:flex; gap:10px; flex-wrap:wrap; margin-bottom:14px; }
        .card { background: var(--card-background-color); border-radius: 10px; padding: 10px 14px; min-width: 96px;
                box-shadow: var(--ha-card-box-shadow, 0 1px 3px rgba(0,0,0,.12)); }
        .card .n { font-size: 22px; font-weight: 600; }
        .card .l { font-size: 12px; color: var(--secondary-text-color); }
        .toolbar { display:flex; gap:8px; align-items:center; margin-bottom:12px; flex-wrap:wrap; }
        input[type=search] { flex:1 1 220px; padding:8px 10px; border-radius:8px;
                border:1px solid var(--divider-color); background: var(--card-background-color); color: inherit; }
        button { font: inherit; padding:6px 10px; border-radius:8px; cursor:pointer;
                border:1px solid var(--divider-color); background: var(--card-background-color); color: inherit; }
        button.primary { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: transparent; }
        button.ghost { background: transparent; }
        button[disabled] { opacity:.5; cursor:not-allowed; }
        table { width:100%; border-collapse: collapse; font-size: 13px; table-layout: fixed; }
        th, td { text-align:left; padding:8px 8px; border-bottom:1px solid var(--divider-color);
                 vertical-align: top; overflow-wrap:anywhere; }
        th { color: var(--secondary-text-color); font-weight:500; font-size:12px; }
        col.c-device { width:23% } col.c-addr { width:13% } col.c-proto { width:21% }
        col.c-sugg { width:12% } col.c-state { width:8% } col.c-acts { width:23% }
        .badge { display:inline-block; color:#fff; border-radius:999px; padding:2px 8px;
                 font-size:11px; white-space:nowrap; }
        .name { font-weight:500; }
        .noip { color: var(--secondary-text-color); font-size:12px; }
        tr.group td { background: var(--secondary-background-color); font-weight:500; font-size:12px;
                      color: var(--secondary-text-color); padding:6px 8px; }
        .meta { color: var(--secondary-text-color); font-size:12px; }
        .msg { margin: 8px 0 12px; padding:8px 10px; border-radius:8px; background: var(--secondary-background-color); font-size:13px; }
        .empty { padding: 24px 6px; color: var(--secondary-text-color); }
        .acts { display:flex; gap:6px; flex-wrap:nowrap; }
        .acts button { padding: 4px 9px; font-size: 12px; white-space: nowrap; }
        .modal { position:fixed; inset:0; background:rgba(0,0,0,.45); display:flex;
                 align-items:center; justify-content:center; z-index:9; }
        .modal .box { background: var(--card-background-color); border-radius:12px; padding:16px;
                      width:min(420px, 90vw); box-shadow: 0 8px 30px rgba(0,0,0,.35); }
        .modal h2 { font-size:16px; margin:0 0 10px; font-weight:500; }
        .modal input { width:100%; box-sizing:border-box; padding:8px 10px; border-radius:8px;
                       border:1px solid var(--divider-color); background: var(--primary-background-color);
                       color: var(--primary-text-color); font-size:14px; }
        .modal .hint { color: var(--secondary-text-color); font-size:12px; margin:8px 0 14px; }
        .modal .row { display:flex; gap:8px; justify-content:flex-end; }
        .acts button { padding:4px 8px; font-size:12px; white-space:nowrap; }
        .head { display:flex; align-items:center; gap:10px; margin:0 0 4px; }
        .head h1 { margin:0; flex:1 1 auto; }
        .head .back { padding:4px 10px; font-size:13px; white-space:nowrap; }
        .modal .box.wide { width:min(560px, 94vw); }
        .cands { max-height: 58vh; overflow:auto; margin: 6px 0 12px; }
        .cand { display:flex; gap:10px; align-items:flex-start; padding:8px 4px;
                border-bottom:1px solid var(--divider-color); cursor:pointer; }
        .cand input { margin-top:4px; }
        .cand img, .cand .cand-noicon { width:28px; height:28px; border-radius:6px; flex:0 0 auto;
                background: var(--secondary-background-color); }
        .cand-body { display:flex; flex-direction:column; gap:2px; min-width:0; }
        .cand-name { font-weight:500; font-size:14px; }
        .cand-meta { font-size:12px; color: var(--secondary-text-color); }
        .cand-desc { font-size:12px; color: var(--secondary-text-color); }
        button.cand { margin-top:6px; }
        .devcard { background: var(--card-background-color); border-radius:10px; padding:10px 12px; margin-bottom:10px;
                   box-shadow: var(--ha-card-box-shadow, 0 1px 2px rgba(0,0,0,.1)); }
        .devcard .top { display:flex; align-items:baseline; gap:8px; flex-wrap:wrap; }
        .devcard .top .n { font-weight:500; }
        .devcard .line { font-size:12px; color: var(--secondary-text-color); margin-top:4px; }
        .devcard .line b { color: var(--primary-text-color); font-weight:500; }
        .devcard .acts { margin-top:8px; flex-wrap:wrap; }
      </style>
      <div class="head">
        <h1>${this._t("title")}</h1>
        <button class="ghost back" data-act="back" title="${this._t("back_title")}">${this._t("back")}</button>
      </div>
      <div class="sub">
        ${this._t("total", {
          total,
          sources: (this._meta?.sources || []).join(" / ") || this._t("sources_none"),
        })}
        ${this._meta?.last_scan ? this._t("last_scan", { time: this._meta.last_scan }) : ""}
        ${this._busy ? this._t("busy") : ""}
      </div>
      <div class="cards">
        <div class="card"><div class="n">${counts.configured ?? 0}</div><div class="l">${this._t("state_configured")}</div></div>
        <div class="card"><div class="n">${counts.available ?? 0}</div><div class="l">${this._t("state_available")}</div></div>
        <div class="card"><div class="n">${counts.installable ?? 0}</div><div class="l">${this._t("state_installable")}</div></div>
        <div class="card"><div class="n">${counts.unknown ?? 0}</div><div class="l">${this._t("state_unknown")}</div></div>
      </div>
      <div class="toolbar">
        <input type="search" placeholder="${this._t("filter")}" value="${this._filter}">
        <button data-act="scan">${this._t("rescan")}</button>
        <button data-act="sweep" class="ghost">${this._t("sweep")}</button>
        <button data-act="integrations" class="ghost">${this._t("services")}</button>
        <label class="ignored-toggle" title="${this._t("group_hint")}">
          <input type="checkbox" data-act="toggle-grouped" ${this._grouped ? "checked" : ""}>
          ${this._t("group_toggle")}
        </label>
        <label class="ignored-toggle" title="${this._t("show_ignored_hint")}">
          <input type="checkbox" data-act="toggle-ignored" ${this._showIgnored ? "checked" : ""}>
          ${this._t("show_ignored")}${this._meta?.ignored_count ? `（${this._meta.ignored_count}）` : ""}
        </label>
      </div>
      ${this._message ? `<div class="msg">${this._message}</div>` : ""}
      ${this._error ? `<div class="msg">${this._t("load_failed", { error: this._error })}</div>` : ""}
      ${
        rows.length === 0
          ? `<div class="empty">${this._t("empty")}</div>`
          : this._narrow
            ? `<div class="cards-list">${rows.map((device) => this._card(device)).join("")}</div>`
            : `<table>
              <colgroup>
                <col class="c-device"><col class="c-addr"><col class="c-proto">
                <col class="c-sugg"><col class="c-state"><col class="c-acts">
              </colgroup>
              <thead><tr><th>${this._t("th_device")}</th><th>${this._t("th_addr")}</th><th>${this._t("th_proto")}</th><th>${this._t("th_sugg")}</th><th>${this._t("th_state")}</th><th>${this._t("th_acts")}</th></tr></thead>
              <tbody>${this._grouped ? this._groupedRows(rows) : rows.map((device) => this._row(device)).join("")}</tbody>
            </table>`
      }
      ${
        this._picking
          ? `<div class="modal">
              <div class="box wide">
                <h2>${this._t("pick_title", { name: this._picking.device.name })}</h2>
                <div class="hint">${this._t("pick_hint", { total: this._catalog?.total ?? 0 })}</div>
                <div class="cands">
                  ${(this._picking.device.suggestions || []).map((c) => this._candRow(c)).join("")}
                </div>
                <div class="row">
                  <button class="ghost" data-act="pick-cancel">${this._t("cancel")}</button>
                  <button class="primary" data-act="pick-install">${this._t("pick_install", { count: this._picking.selected.size })}</button>
                </div>
              </div>
            </div>`
          : ""
      }
      ${
        this._confirm
          ? `<div class="modal">
              <div class="box">
                <h2>${this._confirm.title}</h2>
                <div class="hint">${this._confirm.text}</div>
                <div class="row">
                  <button class="ghost" data-act="confirm-cancel">${this._t("cancel")}</button>
                  <button class="primary" data-act="confirm-ok">${this._confirm.confirmLabel || this._t("continue")}</button>
                </div>
              </div>
            </div>`
          : ""
      }
      ${
        this._renaming
          ? `<div class="modal">
              <div class="box">
                <h2>${this._t("rename_title", { name: this._renaming.name })}</h2>
                <input id="rename-input" value="${this._renameDraft}" maxlength="64">
                <div class="hint">${this._t("rename_hint")}</div>
                <div class="row">
                  <button class="ghost" data-act="rename-cancel">${this._t("cancel")}</button>
                  <button class="primary" data-act="rename-commit">${this._t("ok")}</button>
                </div>
              </div>
            </div>`
          : ""
      }
    `;

    this.shadowRoot.querySelectorAll("button[data-act]").forEach((button) => {
      button.addEventListener("click", (event) => this._onAction(event));
    });
    const groupedToggle = this.shadowRoot.querySelector("input[data-act=toggle-grouped]");
    if (groupedToggle) {
      groupedToggle.addEventListener("change", (event) => {
        this._grouped = event.target.checked;
        this._render();
      });
    }
    const toggle = this.shadowRoot.querySelector("input[data-act=toggle-ignored]");
    if (toggle) {
      toggle.addEventListener("change", (event) => {
        this._showIgnored = event.target.checked;
        this._load();
      });
    }
    this.shadowRoot.querySelectorAll("input[data-act=pick-toggle]").forEach((box) => {
      box.addEventListener("change", (event) => {
        this._toggleCandidate(box.getAttribute("data-domain"), event.target.checked);
      });
    });
    const renameField = this.shadowRoot.querySelector("#rename-input");
    if (renameField) {
      renameField.addEventListener("input", (event) => {
        this._renameDraft = event.target.value;
      });
      renameField.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          this._commitRename();
        } else if (event.key === "Escape") {
          event.preventDefault();
          this._cancelRename();
        }
      });
    }
    const input = this.shadowRoot.querySelector("input[type=search]");
    if (input) {
      input.addEventListener("input", (event) => {
        this._filter = event.target.value;
        const caret = event.target.selectionStart;
        this._render();
        const next = this.shadowRoot.querySelector("input[type=search]");
        if (next) {
          next.focus();
          next.setSelectionRange(caret, caret);
        }
      });
    }
  }

  _card(device) {
    const last = device.last_seen ? new Date(device.last_seen).toLocaleString() : "";
    const evidence = device.match_evidence
      ? `${device.match_evidence}${device.match_support > 1 ? this._t("support", { count: device.match_support }) : ""}`
      : device.repo || "—";
    return `<div class="devcard">
      <div class="top">
        <span class="n">${device.name}${device.ignored ? ` <span class="badge" style="background:#788">${this._t("ignored")}</span>` : ""}</span>
        ${this._badge(device)}
      </div>
      <div class="line">${[device.channel_label, device.vendor || device.manufacturer || device.model]
        .filter(Boolean)
        .join(" · ") || device.detail_line || ""}</div>
      <div class="line">${this._t("addr")} <b>${device.ip || this._t("no_ip")}</b>${device.ip && (device.mac || device.host) ? ` · ${device.mac || device.host}` : ""}</div>
      <div class="line">${this._t("proto")} <b>${this._serviceSummary(device)}</b></div>
      <div class="line">${this._t("sugg")} <b>${device.integration_name || device.domain || "—"}</b> · ${evidence}</div>
      ${(device.suggestions || []).length
        ? `<div class="line"><button class="ghost cand" data-act="pick" data-id="${device.device_id}">${this._t("view_candidates", { count: device.suggestions.length })}</button></div>`
        : ""}
      <div class="line">${last}</div>
      <div class="acts">${this._actions(device)}</div>
    </div>`;
  }

  _row(device) {
    const last = device.last_seen ? new Date(device.last_seen).toLocaleString() : "";
    return `<tr>
      <td>
        <div class="name">${device.name}${device.ignored ? ` <span class="badge" style="background:#788">${this._t("ignored")}</span>` : ""}</div>
        <div class="meta">${[device.channel_label, device.vendor || device.manufacturer || device.model || device.detail_line]
          .filter(Boolean)
          .join(" · ")}</div>
      </td>
      <td>
        <div>${device.ip || `<span class="noip">${this._t("no_ip")}</span>`}</div>
        <div class="meta">${device.ip ? (device.mac || device.host || "") : (device.mac || device.detail_line || "")}</div>
      </td>
      <td class="meta"><div>${this._serviceSummary(device)}</div><div>${last}</div></td>
      <td>
        <div>${device.integration_name || device.domain || "—"}</div>
        <div class="meta" title="${device.match_evidence || ""}">${
          device.match_evidence
            ? `${device.match_evidence}${device.match_support > 1 ? this._t("support", { count: device.match_support }) : ""}`
            : device.repo || ""
        }</div>
        ${
          (device.suggestions || []).length
            ? `<button class="ghost cand" data-act="pick" data-id="${device.device_id}">${this._t("cand_n", { count: device.suggestions.length })}</button>`
            : ""
        }
      </td>
      <td>${this._badge(device)}</td>
      <td><div class="acts">${this._actions(device)}</div></td>
    </tr>`;
  }

  _goBack() {
    if (history.length > 1) {
      history.back();
      return;
    }
    location.assign("/lovelace");
  }

  _candRow(candidate) {
    const checked = this._picking?.selected?.has(candidate.domain) ? "checked" : "";
    const icon = candidate.full_name
      ? `https://github.com/${candidate.full_name.split("/")[0]}.png?size=64`
      : "";
    const install = candidate.installed
      ? `<span class="badge" style="background:#0b8043">${this._t("installed")}</span>`
      : "";
    return `<label class="cand">
      <input type="checkbox" data-act="pick-toggle" data-domain="${candidate.domain}" ${checked}>
      ${icon ? `<img src="${icon}" alt="" width="28" height="28">` : `<span class="cand-noicon"></span>`}
      <span class="cand-body">
        <span class="cand-name">${candidate.name || candidate.domain} ${install}</span>
        <span class="cand-meta">${candidate.domain} · ★ ${candidate.stars ?? 0} · ⤓ ${this._t("downloads", { count: candidate.downloads ?? 0 })} · ${candidate.reason || ""}</span>
        <span class="cand-desc">${candidate.description || ""}</span>
      </span>
    </label>`;
  }

  _openCandidates(device) {
    const selected = new Set();
    for (const candidate of device.suggestions || []) {
      if (!candidate.installed) selected.add(candidate.domain);
    }
    this._picking = { device, selected };
    this._render();
  }

  _toggleCandidate(domain, checked) {
    if (!this._picking) return;
    const selected = this._picking.selected;
    if (checked) selected.add(domain);
    else selected.delete(domain);
    // Update only the counter so the list keeps its scroll position.
    const button = this.shadowRoot.querySelector("button[data-act=pick-install]");
    if (button) button.textContent = this._t("pick_install", { count: selected.size });
  }

  async _installPicked() {
    const picking = this._picking;
    if (!picking) return;
    const chosen = (picking.device.suggestions || []).filter(
      (c) => picking.selected.has(c.domain) && !c.installed
    );
    if (!chosen.length) {
      this._message = this._t("pick_none");
      this._picking = null;
      this._render();
      return;
    }
    const total = chosen.length;
    this._picking = null;
    this._message = this._t("install_many", { count: total });
    this._render();

    let ok = 0;
    const failed = [];
    for (let index = 0; index < chosen.length; index += 1) {
      const candidate = chosen[index];
      this._message = this._t("install_at", {
        i: index + 1,
        total,
        name: candidate.name || candidate.domain,
      });
      this._render();
      try {
        await this._hass.callWS({
          type: "marketplace/repository/install",
          repository: String(candidate.id),
        });
      } catch (err) {
        console.warn("install failed", candidate.domain, err);
      }
      // The install reply is unreliable, so confirm from the repository state.
      let done = false;
      for (let attempt = 0; attempt < 20 && !done; attempt += 1) {
        await new Promise((resolve) => setTimeout(resolve, 8000));
        try {
          const info = await this._hass.callWS({
            type: "marketplace/repository/info",
            repository_id: String(candidate.id),
          });
          if (
            info?.status === "pending-restart" ||
            (info?.installed_version && info?.installed_version === info?.available_version)
          ) {
            done = true;
          }
        } catch (err) {
          // keep polling
        }
      }
      if (done) ok += 1;
      else failed.push(candidate.name || candidate.domain);
    }

    if (ok) {
      const tail = failed.length
        ? this._t("failed_tail", { count: failed.length, names: failed.join("、") })
        : "";
      this._message = this._t("install_summary", { ok, failed: tail });
    } else {
      this._message = this._t("install_unconfirmed", {
        failed: failed.join("、") || this._t("all_failed"),
      });
    }
    this._render();
  }

  _deviceById(id) {
    return this._devices.find((device) => device.device_id === id);
  }

  _onAction(event) {
    const act = event.currentTarget.getAttribute("data-act");
    const id = event.currentTarget.getAttribute("data-id");
    const device = id ? this._deviceById(id) : null;

    if (act === "back") return this._goBack();
    if (act === "scan") return this._scan(false);
    if (act === "sweep") return this._scan(true);
    if (act === "integrations") {
      location.href = "/config/integrations";
      return undefined;
    }
    // Dialog buttons carry no device id, so they must be handled before the
    // guard below - otherwise every modal button is a no-op.
    if (act === "pick-cancel") {
      this._picking = null;
      this._render();
      return undefined;
    }
    if (act === "pick-install") return this._installPicked();
    if (act === "pick-toggle") {
      this._toggleCandidate(event.currentTarget.getAttribute("data-domain"));
      return undefined;
    }
    if (act === "pick" && device) return this._openCandidates(device);
    if (act === "confirm-cancel") return this._closeAsk();
    if (act === "confirm-ok") {
      const action = this._confirm?.onConfirm;
      this._confirm = null;
      this._render();
      return action ? action() : undefined;
    }
    if (act === "rename-cancel") return this._cancelRename();
    if (act === "rename-commit") return this._commitRename();

    if (!device) return undefined;
    if (act === "configure") return this._configure(device);
    if (act === "rename") return this._rename(device);
    if (act === "install") return this._install(device);
    if (act === "manual") return this._manual(device);
    if (act === "ack") return this._acknowledge(device);
    if (act === "forget") return this._forget(device);
    if (act === "restore") return this._restore(device);
    return undefined;
  }

  _manual(device) {
    const repo = device.repo;
    const name = device.integration_name || device.domain || this._t("this_device");
    this._ask(
      this._t("manual_title"),
      repo ? this._t("manual_repo", { name, repo }) : this._t("manual_none"),
      () => {
        location.href = "/config/integrations/dashboard";
      },
      this._t("go_market")
    );
  }
}

customElements.define("lan-discovery-hub-panel", LanDiscoveryHubPanel);
