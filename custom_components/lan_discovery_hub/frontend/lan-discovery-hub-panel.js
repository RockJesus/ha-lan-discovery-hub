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
    this._grouped = true;
    this._confirm = null;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._loaded && hass) {
      this._loaded = true;
      this._load();
    }
  }

  connectedCallback() {
    this._render();
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
        "全网段扫描",
        "将逐个探测本网段每台主机，耗时约 1–2 分钟，期间面板可能变慢。",
        () => this._runScan(true)
      );
      return;
    }
    this._runScan(false);
  }

  async _runScan(full) {
    this._message = full ? "正在全网段扫描…" : "正在扫描…";
    this._render();
    await this._call("scan", { full: Boolean(full) });
    this._message = "扫描完成";
    await this._load();
  }

  async _acknowledge(device) {
    await this._call("acknowledge", { device_id: device.device_id });
    await this._load();
  }

  _forget(device) {
    this._ask(
      `不再显示「${device.name}」`,
      "它仍会被扫描跟踪，只是从列表里隐藏；随时可在工具栏勾选「显示已忽略」恢复。",
      async () => {
        await this._call("forget", { device_id: device.device_id });
        this._message = `已隐藏「${device.name}」，勾选「显示已忽略」可恢复。`;
        await this._load();
      }
    );
  }

  async _restore(device) {
    await this._call("restore", { device_id: device.device_id });
    this._message = `已恢复「${device.name}」。`;
    await this._load();
  }

  async _configure(device) {
    try {
      const result = await this._call("configure", { domain: device.domain });
      if (result && result.flow_id) {
        this._message = `已为「${device.integration_name || device.domain}」创建配置流程，正在打开「设备与服务」页…`;
        this._render();
        setTimeout(() => {
          location.href = "/config/integrations";
        }, 900);
      } else {
        this._message = "该集成当前无法启动配置流程，请到「设备与服务」页手动添加。";
        this._render();
      }
    } catch (err) {
      this._message = `启动配置流程失败：${err && err.message ? err.message : err}`;
      this._render();
    }
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
        ? `已把「${device.name}」命名为「${name}」，之后不再被自动识别改掉。`
        : "已取消手动命名，恢复自动识别。";
    } catch (err) {
      this._message = `改名失败：${err?.message || err}`;
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

  _ask(title, text, onConfirm) {
    // Native confirm()/prompt() are blocked in the companion app, so every
    // question this panel asks is drawn by the panel itself.
    this._confirm = { title, text, onConfirm };
    this._render();
  }

  _closeAsk() {
    this._confirm = null;
    this._render();
  }

  _install(device) {
    const repo = device.repo;
    if (!repo) {
      this._message = "这条设备没有已知的第三方仓库地址，只能手动搜索安装。";
      this._render();
      return;
    }
    this._ask(
      `安装「${device.integration_name || device.domain}」`,
      `将从仓库 ${repo} 安装，安装完成后需要重启 Home Assistant 才会生效。`,
      () => this._runInstall(device)
    );
  }

  async _runInstall(device) {
    const repo = device.repo;
    this._message = `正在 Marketplace 中查找 ${repo}…`;
    this._render();

    let list;
    try {
      list = await this._hass.callWS({ type: "marketplace/repositories/list" });
    } catch (err) {
      this._message =
        `当前 Home Assistant 没有可用的 Marketplace 接口（${err?.message || err}）。` +
        `请手动安装 ${repo}，或通过 HACS 安装。`;
      this._render();
      return;
    }

    let entry = this._findRepository(list, repo);
    if (!entry) {
      // The repository is not in the Marketplace yet: adding it is the whole
      // point of this button, otherwise the user is sent looking for it.
      this._message = `Marketplace 里还没有 ${repo}，正在添加自定义仓库…`;
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
      this._message =
        `Marketplace 里没有找到 ${repo}。请在 Marketplace 中搜索「${device.integration_name || device.domain}」并手动安装。`;
      this._render();
      return;
    }

    this._message = "正在刷新仓库信息…";
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

    this._message = "正在安装，这一步可能需要几分钟…";
    this._render();

    // The install command can stay unanswered for minutes even though the
    // repository is already written to disk, so success is judged from
    // repository/info, not from the reply.
    let settled = false;
    const job = this._hass
      .callWS({ type: "marketplace/repository/install", repository: repositoryId })
      .then(() => {
        settled = true;
      })
      .catch((err) => {
        settled = true;
        this._message = `安装失败：${err?.message || err}。请到 Marketplace 手动安装 ${repo}。`;
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
          this._message = `「${label}」已安装，请重启 Home Assistant 后再点「配置」。`;
          this._render();
          return;
        }
        if (info?.status === "pending-restart") {
          this._message = `「${label}」已安装，请重启 Home Assistant 后再点「配置」。`;
          this._render();
          return;
        }
      } catch (err) {
        // Keep polling: a transient failure here does not mean install failed.
      }
    }
    if (!this._message.startsWith("安装失败")) {
      this._message = `「${label}」的安装请求已提交，若几分钟后仍未出现，请到 Marketplace 查看进度。`;
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
      const key = device.channel_label || "未分类";
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(device);
    }
    return [...groups.entries()]
      .sort((a, b) => b[1].length - a[1].length)
      .map(
        ([label, items]) =>
          `<tr class="group"><td colspan="6">${label} · ${items.length} 台</td></tr>` +
          items.map((device) => this._row(device)).join("")
      )
      .join("");
  }

  _badge(device) {
    const map = {
      configured: ["已接入", "#0b8043"],
      available: ["可接入", "#1e88e5"],
      installable: ["需安装集成", "#f9a825"],
      unknown: ["未知设备", "#757575"],
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
        if (ports.length) tokens.add(`端口 ${ports.slice(0, 3).join("/")}`);
        if (!labels.includes("端口探测")) labels.push("端口探测");
      } else if (source === "ble") {
        if (!labels.includes("蓝牙广播")) labels.push("蓝牙广播");
      } else if (source === "mqtt") {
        if (!labels.includes("MQTT")) labels.push("MQTT");
      } else if (source === "arp") {
        if (!labels.includes("ARP")) labels.push("ARP");
      } else if (source === "serial") {
        if (!labels.includes("串口")) labels.push("串口");
      }
    }
    const head = labels.join(" / ") || "—";
    const tail = [...tokens].slice(0, 4).join(", ");
    return tail ? `${head}<div>${tail}</div>` : head;
  }

  _actions(device) {
    const parts = [];
    if (device.ignored) {
      parts.push(`<button data-act="restore" data-id="${device.device_id}">恢复</button>`);
      return parts.join("");
    }
    if (device.state === "available" && device.domain) {
      parts.push(`<button data-act="configure" data-id="${device.device_id}">配置</button>`);
    }
    if (device.state === "installable" && device.domain) {
      if (device.repo) {
        parts.push(`<button class="primary" data-act="install" data-id="${device.device_id}">安装集成</button>`);
      }
      parts.push(`<button data-act="manual" data-id="${device.device_id}">安装说明</button>`);
    }
    if (device.state === "unknown" && device.ip) {
      parts.push(`<button data-act="configure" data-id="${device.device_id}" disabled title="没有匹配到任何集成">无法接入</button>`);
    }
    if (!device.acknowledged) {
      parts.push(`<button data-act="ack" data-id="${device.device_id}">已处理</button>`);
    }
    parts.push(`<button class="ghost" data-act="rename" data-id="${device.device_id}" title="手动命名，之后不再被自动识别改掉">改名</button>`);
    parts.push(`<button class="ghost" data-act="forget" data-id="${device.device_id}">移除</button>`);
    return parts.join("");
  }

  _render() {
    if (!this.shadowRoot) return;
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
      </style>
      <h1>局域网发现</h1>
      <div class="sub">
        共 ${total} 台设备 · 来源：${(this._meta?.sources || []).join(" / ") || "未启用"}
        ${this._meta?.last_scan ? `· 上次扫描 ${this._meta.last_scan}` : ""}
        ${this._busy ? "· 正在处理…" : ""}
      </div>
      <div class="cards">
        <div class="card"><div class="n">${counts.configured ?? 0}</div><div class="l">已接入</div></div>
        <div class="card"><div class="n">${counts.available ?? 0}</div><div class="l">可接入</div></div>
        <div class="card"><div class="n">${counts.installable ?? 0}</div><div class="l">需装集成</div></div>
        <div class="card"><div class="n">${counts.unknown ?? 0}</div><div class="l">未知设备</div></div>
      </div>
      <div class="toolbar">
        <input type="search" placeholder="按名称 / IP / MAC / 集成筛选" value="${this._filter}">
        <button data-act="scan">重新扫描</button>
        <button data-act="sweep" class="ghost">全网段扫描</button>
        <button data-act="integrations" class="ghost">设备与服务</button>
        <label class="ignored-toggle" title="按发现渠道分组，便于看待没有 IP 的 MQTT / 蓝牙设备">
          <input type="checkbox" data-act="toggle-grouped" ${this._grouped ? "checked" : ""}>
          按协议分组
        </label>
        <label class="ignored-toggle" title="把已隐藏的设备也列出来">
          <input type="checkbox" data-act="toggle-ignored" ${this._showIgnored ? "checked" : ""}>
          显示已忽略${this._meta?.ignored_count ? `（${this._meta.ignored_count}）` : ""}
        </label>
      </div>
      ${this._message ? `<div class="msg">${this._message}</div>` : ""}
      ${this._error ? `<div class="msg">读取失败：${this._error}</div>` : ""}
      ${
        rows.length === 0
          ? `<div class="empty">还没有发现设备。首次扫描在启动约 20 秒后开始，也可以在选项里换扫描通道。</div>`
          : `<table>
              <colgroup>
                <col class="c-device"><col class="c-addr"><col class="c-proto">
                <col class="c-sugg"><col class="c-state"><col class="c-acts">
              </colgroup>
              <thead><tr><th>设备</th><th>地址</th><th>协议</th><th>建议集成</th><th>状态</th><th>操作</th></tr></thead>
              <tbody>${this._grouped ? this._groupedRows(rows) : rows.map((device) => this._row(device)).join("")}</tbody>
            </table>`
      }
      ${
        this._confirm
          ? `<div class="modal">
              <div class="box">
                <h2>${this._confirm.title}</h2>
                <div class="hint">${this._confirm.text}</div>
                <div class="row">
                  <button class="ghost" data-act="confirm-cancel">取消</button>
                  <button class="primary" data-act="confirm-ok">继续</button>
                </div>
              </div>
            </div>`
          : ""
      }
      ${
        this._renaming
          ? `<div class="modal">
              <div class="box">
                <h2>为「${this._renaming.name}」起个名字</h2>
                <input id="rename-input" value="${this._renameDraft}" maxlength="64">
                <div class="hint">这个名字会永久压过自动识别；留空则恢复自动命名。</div>
                <div class="row">
                  <button class="ghost" data-act="rename-cancel">取消</button>
                  <button class="primary" data-act="rename-commit">确定</button>
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

  _row(device) {
    const last = device.last_seen ? new Date(device.last_seen).toLocaleString() : "";
    return `<tr>
      <td>
        <div class="name">${device.name}${device.ignored ? ' <span class="badge" style="background:#788">已忽略</span>' : ""}</div>
        <div class="meta">${[device.channel_label, device.manufacturer || device.model || device.detail_line]
          .filter(Boolean)
          .join(" · ")}</div>
      </td>
      <td>
        <div>${device.ip || `<span class="noip">无 IP</span>`}</div>
        <div class="meta">${device.ip ? (device.mac || device.host || "") : (device.mac || device.detail_line || "")}</div>
      </td>
      <td class="meta"><div>${this._serviceSummary(device)}</div><div>${last}</div></td>
      <td>
        <div>${device.integration_name || device.domain || "—"}</div>
        <div class="meta">${device.repo || ""}</div>
      </td>
      <td>${this._badge(device)}</td>
      <td><div class="acts">${this._actions(device)}</div></td>
    </tr>`;
  }

  _deviceById(id) {
    return this._devices.find((device) => device.device_id === id);
  }

  _onAction(event) {
    const act = event.currentTarget.getAttribute("data-act");
    const id = event.currentTarget.getAttribute("data-id");
    const device = id ? this._deviceById(id) : null;

    if (act === "scan") return this._scan(false);
    if (act === "sweep") return this._scan(true);
    if (act === "integrations") {
      location.href = "/config/integrations";
      return undefined;
    }
    // Dialog buttons carry no device id, so they must be handled before the
    // guard below - otherwise every modal button is a no-op.
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
    this._message = repo
      ? `请安装 ${repo}\n方法一：Marketplace 搜索「${device.integration_name || device.domain}」安装；\n方法二：HACS 添加自定义仓库后安装；\n方法三：手动把集成目录放到 custom_components。安装后重启 Home Assistant。`
      : `没有匹配到已知集成。可以到 Marketplace 按设备品牌/型号搜索，或查看设备文档确认是否已有 Home Assistant 集成。`;
    this._render();
  }
}

customElements.define("lan-discovery-hub-panel", LanDiscoveryHubPanel);
