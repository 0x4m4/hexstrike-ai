let MANIFEST = { tools: [], categories: {}, total: 0 };
let activeTool = null;
let expandedPid = null;
let liveOutputTimer = null;

async function fetchJSON(url, opts) {
  const r = await fetch(url, opts);
  return r.json();
}

function toolMatches(tool, query) {
  if (!query) return true;
  const q = query.toLowerCase();
  return tool.name.toLowerCase().includes(q) ||
         (tool.doc || "").toLowerCase().includes(q) ||
         tool.category.toLowerCase().includes(q);
}

function renderSidebar(query) {
  const root = document.getElementById("category-list");
  root.innerHTML = "";
  const cats = Object.keys(MANIFEST.categories).sort();
  for (const cat of cats) {
    const tools = MANIFEST.categories[cat].filter(t => toolMatches(t, query));
    if (tools.length === 0) continue;
    const group = document.createElement("div");
    group.className = "category-group";
    const title = document.createElement("div");
    title.className = "category-title";
    title.textContent = `${cat} (${tools.length})`;
    group.appendChild(title);
    for (const tool of tools) {
      const item = document.createElement("div");
      item.className = "tool-item" + (tool.composite ? " composite" : "") +
        (activeTool && activeTool.name === tool.name ? " active" : "");
      item.innerHTML = `<span>${tool.name}</span><span class="tag">${tool.composite ? "composite" : tool.method}</span>`;
      item.onclick = () => selectTool(tool.name);
      group.appendChild(item);
    }
    root.appendChild(group);
  }
}

function renderForm(tool) {
  const form = document.getElementById("tool-form");
  form.innerHTML = "";
  for (const p of tool.params) {
    const field = document.createElement("div");
    field.className = "field";
    const label = document.createElement("label");
    label.innerHTML = `${p.name}${p.required ? ' <span class="req">*</span>' : ""} <span class="muted">(${p.type})</span>`;
    const input = document.createElement("input");
    input.type = "text";
    input.name = p.name;
    input.placeholder = p.default !== null && p.default !== undefined ? String(p.default) : (p.required ? "required" : "");
    if (p.default !== null && p.default !== undefined && p.default !== "") {
      input.value = p.default;
    }
    field.appendChild(label);
    field.appendChild(input);
    form.appendChild(field);
  }
}

function selectTool(name) {
  activeTool = MANIFEST.tools.find(t => t.name === name);
  if (!activeTool) return;

  document.getElementById("empty-state").classList.add("hidden");
  document.getElementById("tool-panel").classList.remove("hidden");
  document.getElementById("tool-name").textContent = activeTool.name;
  document.getElementById("tool-route").textContent = activeTool.composite
    ? "composite (no direct route)"
    : `${activeTool.method} /${activeTool.route}`;
  document.getElementById("tool-doc").textContent = activeTool.doc;
  document.getElementById("output-wrap").classList.add("hidden");
  document.getElementById("run-status").textContent = "";

  renderForm(activeTool);

  const runBtn = document.getElementById("run-btn");
  runBtn.disabled = !!activeTool.composite;
  runBtn.title = activeTool.composite
    ? "Composite workflow tool - orchestrates several calls internally, not supported for direct execution here."
    : "";

  renderSidebar(document.getElementById("search").value);
}

async function runTool() {
  if (!activeTool) return;
  const form = document.getElementById("tool-form");
  const params = {};
  for (const input of form.querySelectorAll("input")) {
    if (input.value !== "") params[input.name] = input.value;
  }

  const runBtn = document.getElementById("run-btn");
  const statusEl = document.getElementById("run-status");
  const outputWrap = document.getElementById("output-wrap");
  const output = document.getElementById("output");

  runBtn.disabled = true;
  statusEl.textContent = "Running…";
  outputWrap.classList.remove("hidden");
  output.textContent = "";

  const start = performance.now();
  try {
    const res = await fetchJSON("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tool: activeTool.name, params }),
    });
    const elapsed = ((performance.now() - start) / 1000).toFixed(2);
    statusEl.textContent = `Done in ${elapsed}s`;
    output.textContent = JSON.stringify(res, null, 2);
  } catch (e) {
    statusEl.textContent = "Error";
    output.textContent = String(e);
  } finally {
    runBtn.disabled = false;
  }
}

async function pollHealth() {
  const dot = document.getElementById("health-dot");
  const text = document.getElementById("health-text");
  try {
    const res = await fetchJSON("/api/health");
    if (res.reachable) {
      const d = res.data || {};
      dot.className = "dot ok";
      text.textContent = `online · ${d.total_tools_available || "?"}/${d.total_tools_count || "?"} tools · ${Math.round(d.uptime || 0)}s uptime`;
    } else {
      dot.className = "dot bad";
      text.textContent = "server unreachable";
    }
  } catch (e) {
    dot.className = "dot bad";
    text.textContent = "server unreachable";
  }
}

async function pollProcesses() {
  const list = document.getElementById("process-list");
  try {
    const res = await fetchJSON("/api/processes");
    const procs = (res && res.processes) || res.active_processes || [];
    if (!procs || procs.length === 0) {
      list.innerHTML = '<p class="muted">No active processes.</p>';
      expandedPid = null;
      return;
    }
    list.innerHTML = "";
    for (const p of procs) {
      const pid = p.pid || p.id;
      const isOpen = expandedPid === pid;

      const row = document.createElement("div");
      row.className = "process-row" + (isOpen ? " open" : "");
      row.innerHTML = `
        <div class="process-summary">
          <span>
            <span class="pid">#${pid}</span>
            <span class="status-badge status-${p.status || "running"}">${p.status || "running"}</span>
            ${p.command || p.name || ""}
          </span>
          <span class="process-meta">${p.progress_percent || ""} · ${p.runtime || ""}</span>
          <span>
            <button data-action="view">${isOpen ? "Hide live view" : "View live"}</button>
            <button data-action="pause">Pause</button>
            <button data-action="resume">Resume</button>
            <button data-action="terminate">Kill</button>
          </span>
        </div>
        <div class="process-live hidden">
          <pre class="process-output">Loading live output…</pre>
        </div>`;

      row.querySelector('[data-action="view"]').onclick = () => {
        expandedPid = isOpen ? null : pid;
        pollProcesses();
      };
      row.querySelectorAll('button[data-action="pause"], button[data-action="resume"], button[data-action="terminate"]').forEach(btn => {
        btn.onclick = async () => {
          await fetchJSON(`/api/process/${btn.dataset.action}/${pid}`, { method: "POST" });
          pollProcesses();
        };
      });

      if (isOpen) {
        row.querySelector(".process-live").classList.remove("hidden");
        pollLiveOutput(pid, row.querySelector(".process-output"));
      }

      list.appendChild(row);
    }
  } catch (e) {
    list.innerHTML = '<p class="muted">Unable to load processes.</p>';
  }
}

async function pollLiveOutput(pid, outEl) {
  if (liveOutputTimer) clearInterval(liveOutputTimer);
  const tick = async () => {
    if (expandedPid !== pid) {
      clearInterval(liveOutputTimer);
      return;
    }
    try {
      const res = await fetchJSON(`/api/process/${pid}/output`);
      if (res.success) {
        outEl.textContent =
          `status: ${res.status}  progress: ${Math.round((res.progress || 0) * 100)}%  ` +
          `runtime: ${res.runtime_formatted}  eta: ${res.eta_formatted}\n\n` +
          (res.last_output || "(no output yet)");
      } else {
        outEl.textContent = res.error || "Process finished or not found.";
        clearInterval(liveOutputTimer);
      }
    } catch (e) {
      outEl.textContent = "Unable to fetch live output.";
    }
  };
  await tick();
  liveOutputTimer = setInterval(tick, 1500);
}

document.getElementById("search").addEventListener("input", (e) => renderSidebar(e.target.value));
document.getElementById("run-btn").addEventListener("click", runTool);
document.getElementById("copy-btn").addEventListener("click", () => {
  navigator.clipboard.writeText(document.getElementById("output").textContent);
});

(async function init() {
  MANIFEST = await fetchJSON("/api/manifest");
  const stats = document.getElementById("stats");
  const composite = MANIFEST.tools.filter(t => t.composite).length;
  stats.innerHTML = `
    <div class="stat"><div class="n">${MANIFEST.total}</div><div class="l">Total tools</div></div>
    <div class="stat"><div class="n">${Object.keys(MANIFEST.categories).length}</div><div class="l">Categories</div></div>
    <div class="stat"><div class="n">${MANIFEST.total - composite}</div><div class="l">Directly runnable</div></div>
  `;
  renderSidebar("");
  pollHealth();
  pollProcesses();
  setInterval(pollHealth, 5000);
  setInterval(pollProcesses, 7000);
})();
