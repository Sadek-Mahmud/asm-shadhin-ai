/**
 * dashboard.js — Q-Vigilance AI Defense Dashboard Controller
 * Clean enterprise polling, chart animation, navigation, and form handling.
 */

// ─── Chart Setup ─────────────────────────────────────────────────────────────
const throughputHistory = new Array(40).fill(860);
let chartCanvas, chartCtx;

function initChart() {
  chartCanvas = document.getElementById("networkCanvas");
  if (!chartCanvas) return;
  chartCtx = chartCanvas.getContext("2d");
  window.addEventListener("resize", () => {
    chartCanvas.width  = chartCanvas.parentElement.clientWidth;
    chartCanvas.height = chartCanvas.parentElement.clientHeight;
    drawChart();
  });
  chartCanvas.width  = chartCanvas.parentElement.clientWidth;
  chartCanvas.height = chartCanvas.parentElement.clientHeight;
  drawChart();
}

function drawChart() {
  if (!chartCtx || !chartCanvas) return;
  const w = chartCanvas.width;
  const h = chartCanvas.height;
  const min = 600, max = 1050;
  const step = w / (throughputHistory.length - 1);

  chartCtx.clearRect(0, 0, w, h);

  // Grid lines
  chartCtx.strokeStyle = "rgba(0,0,0,0.05)";
  chartCtx.lineWidth = 1;
  for (let i = 1; i < 4; i++) {
    const y = (h / 4) * i;
    chartCtx.beginPath();
    chartCtx.moveTo(0, y);
    chartCtx.lineTo(w, y);
    chartCtx.stroke();
  }

  // Fill gradient
  const grad = chartCtx.createLinearGradient(0, 0, 0, h);
  grad.addColorStop(0, "rgba(37,99,235,0.18)");
  grad.addColorStop(1, "rgba(37,99,235,0.01)");

  chartCtx.beginPath();
  throughputHistory.forEach((val, i) => {
    const norm = (val - min) / (max - min);
    const x = i * step;
    const y = h - norm * (h - 20) - 10;
    i === 0 ? chartCtx.moveTo(x, y) : chartCtx.lineTo(x, y);
  });
  chartCtx.lineTo(w, h);
  chartCtx.lineTo(0, h);
  chartCtx.closePath();
  chartCtx.fillStyle = grad;
  chartCtx.fill();

  // Line
  chartCtx.beginPath();
  chartCtx.strokeStyle = "#2563eb";
  chartCtx.lineWidth = 2.5;
  chartCtx.lineJoin = "round";
  throughputHistory.forEach((val, i) => {
    const norm = (val - min) / (max - min);
    const x = i * step;
    const y = h - norm * (h - 20) - 10;
    i === 0 ? chartCtx.moveTo(x, y) : chartCtx.lineTo(x, y);
  });
  chartCtx.stroke();
}

// ─── Page Navigation ─────────────────────────────────────────────────────────
const pageTitles = {
  dashboard: "Dashboard Overview",
  threats:   "Threat Events",
  blocked:   "Blocked IP Registry",
  tarpit:    "AI Tarpit Monitor",
  terminal:  "Live System Terminal",
  pqc:       "Post-Quantum Cryptography"
};

function showPage(name) {
  document.querySelectorAll("[id^='page-']").forEach(el => el.style.display = "none");
  const target = document.getElementById("page-" + name);
  if (target) target.style.display = "";

  document.getElementById("pageTitle").textContent = pageTitles[name] || name;

  document.querySelectorAll(".nav-item").forEach(el => el.classList.remove("active"));
  event?.currentTarget?.classList.add("active");
}

// ─── API Polling ─────────────────────────────────────────────────────────────
function formatUptime(seconds) {
  const h = Math.floor(seconds / 3600).toString().padStart(2, "0");
  const m = Math.floor((seconds % 3600) / 60).toString().padStart(2, "0");
  const s = (seconds % 60).toString().padStart(2, "0");
  return `Uptime: ${h}:${m}:${s}`;
}

async function fetchStatus() {
  try {
    const r = await fetch("/api/status");
    if (!r.ok) return;
    const d = await r.json();
    const m = d.metrics;

    setText("valThroughput", `${m.throughput_mbps} Mbps`);
    setText("valDropped",    m.total_packets_dropped.toLocaleString());
    setText("valBlocked",    m.active_blocked_ips);
    setText("valTarpit",     `${m.tarpit_trapped_bots} bots`);
    setText("valTarpit2",    `${m.tarpit_trapped_bots} bots`);
    setText("valTokens",     `Tokens drained: ${m.tokens_drained.toLocaleString()}`);
    setText("valTokens2",    m.tokens_drained.toLocaleString());
    setText("valCpu",        `${m.cpu_usage_pct}%`);
    setText("valRam",        `${m.ram_usage_pct}%`);
    setText("systemUptime",  formatUptime(d.uptime_seconds));

    throughputHistory.shift();
    throughputHistory.push(m.throughput_mbps);
    drawChart();
  } catch (_) {}
}

async function fetchEvents() {
  try {
    const r = await fetch("/api/events");
    if (!r.ok) return;
    const d = await r.json();
    const tbody = document.getElementById("eventTableBody");
    if (!tbody) return;

    tbody.innerHTML = d.events.slice(0, 20).map(ev => {
      const vClass  = ev.verdict === "MALICIOUS" ? "badge-red" : "badge-amber";
      const aClass  = ev.ebpf_action === "XDP_DROP" ? "badge-red" : "badge-amber";
      const conf    = `${Math.round(ev.confidence * 100)}%`;
      return `
        <tr>
          <td style="color:var(--text-muted); font-family:var(--font-mono);">${ev.timestamp}</td>
          <td><span class="ip-code">${ev.source_ip}</span></td>
          <td style="font-family:var(--font-mono);">${ev.target_port || "—"}</td>
          <td>${ev.threat_type}</td>
          <td><span class="badge ${vClass}">${ev.verdict}</span></td>
          <td style="font-family:var(--font-mono); font-weight:600;">${conf}</td>
          <td><span class="badge ${aClass}">${ev.ebpf_action}</span></td>
        </tr>`;
    }).join("");
  } catch (_) {}
}

async function fetchBlocked() {
  try {
    const r = await fetch("/api/blocked");
    if (!r.ok) return;
    const d = await r.json();
    const tbody = document.getElementById("blockedTableBody");
    if (!tbody) return;

    tbody.innerHTML = d.blocked_ips.map(b => `
      <tr>
        <td><span class="ip-code">${b.ip}</span></td>
        <td>${b.drop_count.toLocaleString()} pkts</td>
        <td>${b.ttl_remaining}s</td>
        <td style="color:var(--text-secondary);">${b.reason_text}</td>
        <td><button class="btn btn-danger btn-sm" onclick="unblockIp('${b.ip}')">Unblock</button></td>
      </tr>`).join("");
  } catch (_) {}
}

// Colour-code terminal log lines by source tag
function colourLine(line) {
  if (line.includes("[KERNEL]") || line.includes("[XDP-FILTER]")) return "kernel";
  if (line.includes("[PQC]"))     return "pqc";
  if (line.includes("[AI-ENGINE]") || line.includes("[AI]")) return "ai";
  if (line.includes("[TARPIT]"))  return "tarpit";
  if (line.includes("[OPERATOR]"))return "op";
  if (line.includes("[WARN]"))    return "warn";
  if (line.includes("[DAEMON]") || line.includes("[INFO]")) return "daemon";
  return "";
}

async function fetchTerminal() {
  try {
    const r = await fetch("/api/terminal-logs");
    if (!r.ok) return;
    const d = await r.json();
    const lines = d.lines || [];

    const html = lines.map(l => {
      const cls = colourLine(l);
      return `<div class="log-line ${cls}">${escapeHtml(l)}</div>`;
    }).join("");

    ["dashTerminal", "fullTerminal"].forEach(id => {
      const el = document.getElementById(id);
      if (!el) return;
      el.innerHTML = html;
      el.scrollTop = el.scrollHeight;
    });
  } catch (_) {}
}

function escapeHtml(str) {
  return str.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

// ─── Block / Unblock ─────────────────────────────────────────────────────────
async function submitBlock(e) {
  e.preventDefault();
  const ip     = document.getElementById("inputIp").value.trim();
  const ttl    = parseInt(document.getElementById("inputTtl").value, 10);
  const reason = document.getElementById("inputReason").value.trim();

  try {
    const r = await fetch("/api/block", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ip, ttl, reason})
    });
    const resp = await r.json();
    document.getElementById("blockModal").style.display = "none";
    if (!resp.success) alert("Error: " + (resp.error || "Unknown"));
  } catch (err) {
    alert("Network error: " + err);
  }
}

window.unblockIp = async function(ip) {
  if (!confirm(`Unblock ${ip}?`)) return;
  try {
    await fetch("/api/unblock", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ip})
    });
    await fetchBlocked();
  } catch (err) {
    alert("Error: " + err);
  }
};

// Close modal on backdrop click
document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("blockModal").addEventListener("click", function(e) {
    if (e.target === this) this.style.display = "none";
  });

  initChart();

  // Initial load
  fetchStatus();
  fetchEvents();
  fetchBlocked();
  fetchTerminal();

  // Polling intervals
  setInterval(fetchStatus,   1500);
  setInterval(fetchEvents,   3000);
  setInterval(fetchBlocked,  4000);
  setInterval(fetchTerminal, 2000);
});
