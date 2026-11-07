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
      const result = await this._hass.callWS({ type: "lan_discovery_hub/devices" });
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

  async _scan(full) {
    if (full && !confirm("将逐个探测本网段每台主机，耗时约 1–2 分钟。继续？")) return;
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

  async _forget(device) {
    if (!confirm(`从台账中移除「${device.name}」？下次扫描若再次发现会重新出现。`)) return;
    await this._call("forget", { device_id: device.device_id });
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

  async _rename(device) {
    const current = device.name_override || device.name || "";
    const typed = prompt(
      `为这台设备起一个名字${device.name_override ? "（留空恢复自动命名）" : ""}`,
      current
    );
    if (typed === null) return;
    try {
      await this._hass.callWS({
        type: "lan_discovery_hub/rename",
        device_id: device.device_id,
        name: typed.trim(),
      });
      this._message = typed.trim()
        ? `已把 ${device.device_id} 命名为「${typed.trim()}」。`
        : "已取消手动命名，恢复自动识别。";
      this._render();
      this._load();
    } catch (err) {
      this._message = `改名失败：${err?.message || err}`;
      this._render();
    }
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

  async _install(device) {
    const repo = device.repo;
    if (!repo) {
      this._message = "这条设备没有已知的第三方仓库地址，只能手动搜索安装。";
      this._render();
      return;
    }
    const warning =
      `将从仓库 ${repo} 安装「${device.integration_name || device.domain}」集成。\n\n` +
      "安装完成后需要重启 Home Assistant 才会生效。是否继续？";
    if (!confirm(warning)) return;

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
    try {
      await this._hass.callWS({
        type: "marketplace/repository/install",
        repository: repositoryId,
      });
    } catch (err) {
      this._message = `安装失败：${err?.message || err}。请到 Marketplace 手动安装 ${repo}。`;
      this._render();
      return;
    }

    this._message = `「${device.integration_name || device.domain}」已安装，请重启 Home Assistant 后再点「配置」。`;
    this._render();
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
    const services = device.services || {};
    const kinds = Object.values(services)
      .map((service) => service.kind || service.source)
      .filter(Boolean);
    return [...new Set(kinds)].join(", ") || "—";
  }

  _actions(device) {
    const parts = [];
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
        col.c-device { width:24% } col.c-addr { width:14% } col.c-proto { width:22% }
        col.c-sugg { width:13% } col.c-state { width:8% } col.c-acts { width:19% }
        .badge { display:inline-block; color:#fff; border-radius:999px; padding:2px 8px;
                 font-size:11px; white-space:nowrap; }
        .name { font-weight:500; }
        .meta { color: var(--secondary-text-color); font-size:12px; }
        .msg { margin: 8px 0 12px; padding:8px 10px; border-radius:8px; background: var(--secondary-background-color); font-size:13px; }
        .empty { padding: 24px 6px; color: var(--secondary-text-color); }
        .acts { display:flex; gap:6px; flex-wrap:wrap; }
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
              <tbody>${rows.map((device) => this._row(device)).join("")}</tbody>
            </table>`
      }
    `;

    this.shadowRoot.querySelectorAll("button[data-act]").forEach((button) => {
      button.addEventListener("click", (event) => this._onAction(event));
    });
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
        <div class="name">${device.name}</div>
        <div class="meta">${device.manufacturer || ""} ${device.model || ""}</div>
      </td>
      <td>
        <div>${device.ip || "—"}</div>
        <div class="meta">${device.mac || device.host || ""}</div>
      </td>
      <td class="meta">${this._serviceSummary(device)}<div>${last}</div></td>
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
    if (!device) return undefined;
    if (act === "configure") return this._configure(device);
    if (act === "rename") return this._rename(device);
    if (act === "install") return this._install(device);
    if (act === "manual") return this._manual(device);
    if (act === "ack") return this._acknowledge(device);
    if (act === "forget") return this._forget(device);
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
