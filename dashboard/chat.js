// Attendance Assistant chat widget + live-data hydration.
// Loads after app.js/analytics.js, so it reuses the globals `esc`,
// `employeeData`, `currentEmployeeId`, `renderDashboard`, `renderAnalytics`,
// `apiFetch` and `updateAuthUI` defined there.

(function () {
  "use strict";

  const fab = document.getElementById("chat-fab");
  const panel = document.getElementById("chat-panel");
  const closeBtn = document.getElementById("chat-close");
  const messagesEl = document.getElementById("chat-messages");
  const form = document.getElementById("chat-form");
  const textarea = document.getElementById("chat-text");
  const sendBtn = document.getElementById("chat-send");
  const statusEl = document.getElementById("chat-status");
  const usageEl = document.getElementById("chat-usage");
  const suggestions = document.getElementById("chat-suggestions");

  // Conversation history sent back to the server for context.
  const history = [];
  const MAX_HISTORY = 12;
  const EMP_ID_RE = /EMP\d{2,6}/i;
  let greeted = false;

  // 401-aware fetch (app.js). Falls back to plain fetch if not yet defined.
  const http = typeof apiFetch === "function" ? apiFetch : fetch;

  // Minimal, XSS-safe markdown: escape everything, then re-apply a few marks.
  function renderMarkdown(text) {
    let html = esc(text);
    html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
    return html;
  }

  function addMessage(role, text, meta) {
    const el = document.createElement("div");
    el.className = "chat-msg " + (role === "user" ? "user" : "bot");
    el.innerHTML = role === "user" ? esc(text) : renderMarkdown(text);
    if (meta) {
      const m = document.createElement("span");
      m.className = "meta";
      m.innerText = meta;
      el.appendChild(m);
    }
    messagesEl.appendChild(el);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return el;
  }

  function metaText(provider, model) {
    if (!provider || provider === "none" || provider === "stream") return "";
    if (provider === "offline") return "direct data lookup";
    if (provider === "error") return "";
    return "via " + provider + (model ? " · " + model : "");
  }

  function openPanel() {
    panel.hidden = false;
    fab.style.display = "none";
    if (!greeted) {
      addMessage(
        "bot",
        "Hi! I can answer questions about any employee's attendance and " +
          "compliance status. Try a suggestion below or ask your own."
      );
      greeted = true;
    }
    textarea.focus();
  }

  function closePanel() {
    panel.hidden = true;
    fab.style.display = "inline-flex";
  }

  async function refreshStatus() {
    try {
      const res = await fetch("/api/health");
      if (!res.ok) return;
      const data = await res.json();
      if (typeof updateAuthUI === "function") updateAuthUI(data.auth_required);
      if (data.llm_configured && data.providers && data.providers.length) {
        const names = data.providers.map((p) => p.name).join(", ");
        statusEl.innerText = "Grounded in live data · " + names;
      } else {
        statusEl.innerText = "Offline data-lookup mode (no LLM keys)";
      }
    } catch (_) {
      statusEl.innerText = "Run server.py to enable the assistant";
    }
    refreshUsage();
  }

  async function refreshUsage() {
    if (!usageEl) return;
    try {
      const res = await fetch("/api/usage");
      if (!res.ok) return;
      const u = await res.json();
      const reqs = u.requests || 0;
      const tokens =
        u.total_tokens != null
          ? u.total_tokens
          : (u.prompt_tokens || 0) + (u.completion_tokens || 0);
      usageEl.innerText = reqs
        ? "LLM usage · " +
          reqs +
          " request" +
          (reqs === 1 ? "" : "s") +
          " · " +
          tokens +
          " tokens"
        : "";
    } catch (_) {
      // leave the footer as-is
    }
  }

  // Stream tokens into `el` via SSE. Resolves with {text, provider, model} or
  // throws so the caller can fall back to the non-streaming endpoint.
  async function streamInto(el, question, hist) {
    const res = await http("/api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: question, history: hist }),
    });
    if (!res.ok || !res.body) throw new Error("stream unavailable");

    el.classList.remove("typing");
    el.innerHTML = "";
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let text = "";
    let meta = { provider: "", model: null };

    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let idx;
      while ((idx = buffer.indexOf("\n\n")) >= 0) {
        const frame = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        const dataStr = frame
          .split("\n")
          .filter((l) => l.startsWith("data:"))
          .map((l) => l.slice(5).trim())
          .join("");
        if (!dataStr) continue;
        let evt;
        try {
          evt = JSON.parse(dataStr);
        } catch (_) {
          continue;
        }
        if (evt.error) throw new Error(evt.error);
        if (evt.delta) {
          text += evt.delta;
          el.innerHTML = renderMarkdown(text);
          messagesEl.scrollTop = messagesEl.scrollHeight;
        }
        if (evt.done) {
          meta.provider = evt.provider;
          meta.model = evt.model;
        }
      }
    }
    if (!text) throw new Error("empty stream");
    return { text: text, provider: meta.provider, model: meta.model };
  }

  async function send(question) {
    question = (question || "").trim();
    if (!question) return;

    addMessage("user", question);
    history.push({ role: "user", content: question });
    textarea.value = "";
    textarea.style.height = "auto";
    sendBtn.disabled = true;

    const hist = history.slice(0, -1).slice(-MAX_HISTORY);
    const bot = addMessage("bot", "Thinking…");
    bot.classList.add("typing");

    let answerText = "";
    let meta = { provider: "", model: null };
    let ok = false;

    // Prefer streaming; fall back to the non-streaming endpoint on any failure.
    try {
      const streamed = await streamInto(bot, question, hist);
      answerText = streamed.text;
      meta = streamed;
      ok = true;
    } catch (_) {
      ok = false;
    }

    if (!ok) {
      try {
        const res = await http("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: question, history: hist }),
        });
        const data = await res.json();
        bot.classList.remove("typing");
        if (!res.ok) {
          bot.innerHTML = renderMarkdown(
            data.error || "Something went wrong. Please try again."
          );
          sendBtn.disabled = false;
          textarea.focus();
          return;
        }
        answerText = data.answer;
        meta = { provider: data.provider, model: data.model };
        bot.innerHTML = renderMarkdown(answerText);
        ok = true;
      } catch (_) {
        bot.classList.remove("typing");
        bot.innerHTML = renderMarkdown(
          "I couldn't reach the assistant. Make sure the server is running " +
            "(`python server.py`) and reload this page over http://, not file://."
        );
        sendBtn.disabled = false;
        textarea.focus();
        return;
      }
    }

    bot.classList.remove("typing");
    const mt = metaText(meta.provider, meta.model);
    if (mt) {
      const m = document.createElement("span");
      m.className = "meta";
      m.innerText = mt;
      bot.appendChild(m);
    }

    const empId = detectEmpId(question + " " + answerText);
    if (empId) attachExport(bot, empId);

    history.push({ role: "assistant", content: answerText });
    while (history.length > MAX_HISTORY) history.shift();

    refreshUsage();
    sendBtn.disabled = false;
    textarea.focus();
  }

  // --- IRM brief export (F-38) ---
  function detectEmpId(text) {
    const m = (text || "").match(EMP_ID_RE);
    return m ? m[0].toUpperCase() : null;
  }

  function attachExport(el, empId) {
    const bar = document.createElement("div");
    bar.className = "msg-actions";
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "export-btn";
    btn.innerText = "Export " + empId + " to IRM brief";
    btn.addEventListener("click", () => exportIrm(empId, btn));
    bar.appendChild(btn);
    el.appendChild(bar);
  }

  async function exportIrm(empId, btn) {
    const label = btn ? btn.innerText : "";
    if (btn) {
      btn.disabled = true;
      btn.innerText = "Preparing…";
    }
    try {
      const res = await http("/api/export/irm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ employee_id: empId }),
      });
      if (!res.ok) {
        let msg = "Export failed.";
        try {
          msg = (await res.json()).error || msg;
        } catch (_) {
          /* non-JSON error */
        }
        addMessage("bot", msg);
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "IRM_Brief_" + empId + ".md";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (_) {
      addMessage("bot", "Could not reach the server to export the brief.");
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerText = label;
      }
    }
  }

  // --- Wiring ---
  fab.addEventListener("click", openPanel);
  closeBtn.addEventListener("click", closePanel);

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    send(textarea.value);
  });

  textarea.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send(textarea.value);
    }
  });

  textarea.addEventListener("input", () => {
    textarea.style.height = "auto";
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + "px";
  });

  suggestions.addEventListener("click", (e) => {
    const chip = e.target.closest(".chip");
    if (chip) send(chip.innerText);
  });

  // Deep-link hook so the dashboard (F-37) can open/prefill the assistant.
  window.AttendanceAssistant = {
    open: openPanel,
    ask: function (q) {
      openPanel();
      send(q);
    },
    prefill: function (q) {
      openPanel();
      textarea.value = q;
      textarea.dispatchEvent(new Event("input"));
      textarea.focus();
    },
  };

  // --- Single-source-of-truth: hydrate dashboard from the API when served. ---
  (async function hydrateEmployees() {
    try {
      const res = await http("/api/employees");
      if (!res.ok) return;
      const data = await res.json();
      if (data && typeof data === "object") {
        Object.assign(employeeData, data);
        if (typeof renderDashboard === "function") {
          renderDashboard(currentEmployeeId);
        }
        const analyticsPanel = document.getElementById("analytics-panel");
        if (
          typeof renderAnalytics === "function" &&
          analyticsPanel &&
          analyticsPanel.classList.contains("active")
        ) {
          renderAnalytics();
        }
      }
    } catch (_) {
      // Opened as a file:// — keep the bundled data.js copy.
    }
  })();

  refreshStatus();
})();
