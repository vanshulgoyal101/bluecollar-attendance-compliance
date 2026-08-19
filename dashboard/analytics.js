// Analytics view (F-45). Computes department comparisons, at-risk counts and a
// points distribution from the same `employeeData` the dashboard uses. Loaded
// after app.js so it reuses the global `esc`, `employeeData` and the reference
// "today" (2026-05-31) the compliance tab computes balances against.

(function () {
  "use strict";

  const TODAY = new Date("2026-05-31");

  // Point buckets, evaluated top-down (first match wins).
  const BUCKETS = [
    { label: "\u2264 0 (Termination)", color: "#dc2626", test: (p) => p <= 0 },
    { label: "0\u20131 (Term. Warning)", color: "#ef4444", test: (p) => p <= 1 },
    { label: "1\u20132 (Written Warning)", color: "#f59e0b", test: (p) => p <= 2 },
    { label: "2\u20134", color: "#eab308", test: (p) => p <= 4 },
    { label: "4\u20136", color: "#3b82f6", test: (p) => p <= 6 },
    { label: "6\u20137 (Good Standing)", color: "#10b981", test: () => true },
  ];

  // Mirror app.js: current balance is the last history point on/before today,
  // falling back to the record's current_points / starting_points.
  function computePoints(data) {
    if (!data) return 0;
    const past = (data.history || []).filter((h) => new Date(h.date) <= TODAY);
    if (past.length) return past[past.length - 1].balance;
    if (typeof data.current_points === "number") return data.current_points;
    return typeof data.starting_points === "number" ? data.starting_points : 7;
  }

  function bucketFor(points) {
    for (const b of BUCKETS) {
      if (b.test(points)) return b.label;
    }
    return BUCKETS[BUCKETS.length - 1].label;
  }

  function collect() {
    const rows = [];
    Object.keys(employeeData || {}).forEach((id) => {
      const data = employeeData[id];
      if (!data) return;
      rows.push({
        id: id,
        name: data.name || "",
        department: data.department || "Unassigned",
        status: data.warning_status || "",
        points: computePoints(data),
      });
    });
    return rows;
  }

  function renderAnalytics() {
    const rows = collect();
    const total = rows.length;
    const atRisk = rows.filter((r) => r.points <= 2.0);
    const avg = total ? rows.reduce((s, r) => s + r.points, 0) / total : 0;

    setText("an-total", String(total));
    setText("an-atrisk", String(atRisk.length));
    setText("an-avg", avg.toFixed(1));

    renderDepartments(rows);
    renderDistribution(rows);
    renderAtRiskList(atRisk);
  }

  function renderDepartments(rows) {
    const byDept = {};
    rows.forEach((r) => {
      const d = (byDept[r.department] = byDept[r.department] || {
        count: 0,
        sum: 0,
        atRisk: 0,
      });
      d.count += 1;
      d.sum += r.points;
      if (r.points <= 2.0) d.atRisk += 1;
    });

    const body = document.querySelector("#an-dept-table tbody");
    if (!body) return;
    body.innerHTML = "";
    Object.keys(byDept)
      .sort((a, b) => byDept[a].sum / byDept[a].count - byDept[b].sum / byDept[b].count)
      .forEach((dept) => {
        const d = byDept[dept];
        const avg = (d.sum / d.count).toFixed(1);
        const tr = document.createElement("tr");
        tr.innerHTML =
          `<td>${esc(dept)}</td>` +
          `<td>${d.count}</td>` +
          `<td><strong>${avg}</strong></td>` +
          `<td>${d.atRisk > 0 ? `<span style="color:#ef4444;font-weight:600;">${d.atRisk}</span>` : "0"}</td>`;
        body.appendChild(tr);
      });
  }

  function renderDistribution(rows) {
    const counts = {};
    BUCKETS.forEach((b) => (counts[b.label] = 0));
    rows.forEach((r) => {
      counts[bucketFor(r.points)] += 1;
    });

    const max = Math.max(1, ...Object.values(counts));
    const container = document.getElementById("an-distribution");
    if (!container) return;
    container.innerHTML = "";
    BUCKETS.forEach((b) => {
      const count = counts[b.label];
      const pct = Math.round((count / max) * 100);
      const row = document.createElement("div");
      row.className = "an-bar-row";
      row.innerHTML =
        `<span class="an-bar-label">${esc(b.label)}</span>` +
        `<span class="an-bar-track"><span class="an-bar-fill" style="width:${pct}%;background:${b.color};"></span></span>` +
        `<span class="an-bar-count">${count}</span>`;
      container.appendChild(row);
    });
  }

  function renderAtRiskList(atRisk) {
    const container = document.getElementById("an-atrisk-list");
    if (!container) return;
    container.innerHTML = "";
    if (!atRisk.length) {
      container.innerHTML =
        '<p style="color: var(--text-muted);">No employees are currently at risk.</p>';
      return;
    }
    atRisk
      .slice()
      .sort((a, b) => a.points - b.points)
      .forEach((r) => {
        const div = document.createElement("div");
        div.className = "an-risk-item";
        div.innerHTML =
          `<div><strong>${esc(r.id)}</strong> ${esc(r.name)}` +
          `<span class="an-risk-dept">${esc(r.department)}</span></div>` +
          `<div class="an-risk-pts">${r.points.toFixed(1)} pts` +
          `<span class="an-risk-status">${esc(r.status)}</span></div>`;
        container.appendChild(div);
      });
  }

  function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.innerText = text;
  }

  // Expose for switchTab() in app.js and post-hydration refresh in chat.js.
  window.renderAnalytics = renderAnalytics;
})();
