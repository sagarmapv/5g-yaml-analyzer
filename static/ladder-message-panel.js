/** Ladder message detail panel — operation API or procedural hop. */
(function () {
  const opCache = new Map();

  function escapeHtml(text) {
    return window.MessageDetail?.escapeHtml(text) || String(text ?? "");
  }

  function renderProceduralDetail(msg) {
    const kindNote =
      msg.messageKind === "n4"
        ? "<p>This hop uses <strong>N4 / PFCP</strong> between SMF and UPF — not modeled as OpenAPI in the corpus.</p>"
        : "";
    return `<div class="message-detail message-detail--procedural">
      <h3>Step ${escapeHtml(msg.stepOrder)} — ${escapeHtml(msg.from)} → ${escapeHtml(msg.to)}</h3>
      <p>${escapeHtml(msg.action || msg.label)}</p>
      ${kindNote}
      ${msg.procedureTs ? `<p class="message-detail-meta">Procedure: TS ${escapeHtml(msg.procedureTs)}</p>` : ""}
      ${msg.serviceTs ? `<p class="message-detail-meta">Service context: TS ${escapeHtml(msg.serviceTs)}</p>` : ""}
      ${msg.payload ? `<p>Payload reference: <code>${escapeHtml(msg.payload)}</code></p>` : ""}
      ${msg.response ? `<p>Response reference: <code>${escapeHtml(msg.response)}</code></p>` : ""}
    </div>`;
  }

  async function fetchOperationDetail(operationId) {
    if (opCache.has(operationId)) {
      return opCache.get(operationId);
    }
    const res = await fetch(`/api/operations/${encodeURIComponent(operationId)}`);
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }
    const data = await res.json();
    opCache.set(operationId, data);
    return data;
  }

  async function openLadderMessage(msg, panelBodyEl) {
    if (!panelBodyEl) return;
    panelBodyEl.innerHTML = "<p class=\"loading\">Loading message detail…</p>";

    if (!msg.operationId || !msg.hasMessageDetail) {
      panelBodyEl.innerHTML = renderProceduralDetail(msg);
      return;
    }

    try {
      const detail = await fetchOperationDetail(msg.operationId);
      const html = window.MessageDetail?.renderOperationDetailHtml(detail);
      panelBodyEl.innerHTML = html || "<p class=\"loading\">No detail available.</p>";
    } catch (err) {
      panelBodyEl.innerHTML = `<p class="loading">Failed to load operation: ${escapeHtml(err.message)}</p>`;
    }
  }

  function showLadderPanel(title) {
    const panel = document.getElementById("ladder-message-panel");
    const titleEl = document.getElementById("ladder-message-title");
    if (panel) panel.classList.remove("hidden");
    if (titleEl) titleEl.textContent = title || "Message detail";
    panel?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function hideLadderPanel() {
    document.getElementById("ladder-message-panel")?.classList.add("hidden");
  }

  window.LadderMessagePanel = {
    openLadderMessage,
    showLadderPanel,
    hideLadderPanel,
    renderProceduralDetail,
  };
})();
