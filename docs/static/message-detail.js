/** Shared operation / message detail rendering for Explorer and ladder. */
(function () {
  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text ?? "";
    return div.innerHTML;
  }

  function createCollapsibleSection(title, items) {
    const section = document.createElement("div");
    const header = document.createElement("div");
    header.className = "section-header";
    header.textContent = "▶ " + title;
    const content = document.createElement("div");
    content.className = "section-content";
    (items || []).forEach((item) => {
      const row = document.createElement("div");
      row.textContent = item;
      content.appendChild(row);
    });
    header.onclick = () => {
      const open = content.classList.toggle("visible");
      header.textContent = (open ? "▼ " : "▶ ") + title;
    };
    section.appendChild(header);
    section.appendChild(content);
    return section;
  }

  function renderOperationDetailHtml(detail) {
    if (!detail) return "<p class=\"loading\">No operation detail.</p>";

    const paramRows = (detail.parameters || [])
      .map(
        (p) =>
          `<li><code>${escapeHtml(p.in)}</code> <strong>${escapeHtml(p.name)}</strong>${p.required ? " (required)" : ""}${p.schemaRef ? ` → ${escapeHtml(p.schemaRef)}` : ""}</li>`
      )
      .join("");

    let requestHtml = "";
    if (detail.request) {
      const r = detail.request;
      requestHtml = `<h4 class="preview-sub">Request body</h4>
        <ul class="preview-list">
          <li>Content-Type: <code>${escapeHtml(r.contentType || "")}</code></li>
          ${r.schemaRef ? `<li>Schema: <code>${escapeHtml(r.schemaRef)}</code></li>` : ""}
          ${(r.requiredProperties || []).length ? `<li>Required: ${r.requiredProperties.map((f) => `<code>${escapeHtml(f)}</code>`).join(", ")}</li>` : ""}
        </ul>`;
    }

    const responseRows = (detail.responses || [])
      .map((r) => {
        const headers = (r.headers || [])
          .map((h) => `<code>${escapeHtml(h.name)}</code>${h.required ? " (required)" : ""}`)
          .join(", ");
        return `<li><strong>${escapeHtml(r.statusCode)}</strong> — ${escapeHtml(r.description || "")}
          ${r.schemaRef ? `<br>Body: <code>${escapeHtml(r.schemaRef)}</code>` : ""}
          ${headers ? `<br>Headers: ${headers}` : ""}
        </li>`;
      })
      .join("");

    return `<div class="message-detail">
      <div class="message-header">
        <span class="method-badge ${escapeHtml((detail.method || "default").toLowerCase())}">${escapeHtml(detail.method || "?")}</span>
        <span class="op-path">${escapeHtml(detail.path || "")}</span>
      </div>
      <p class="op-id"><code>${escapeHtml(detail.operationId || "")}</code>${detail.summary ? ` — ${escapeHtml(detail.summary)}` : ""}</p>
      ${detail.nf ? `<p class="message-detail-meta">${escapeHtml(detail.nf)} · ${escapeHtml(detail.service || "")}</p>` : ""}
      ${paramRows ? `<h4 class="preview-sub">Parameters</h4><ul class="preview-list">${paramRows}</ul>` : ""}
      ${requestHtml}
      ${responseRows ? `<h4 class="preview-sub">Responses</h4><ul class="preview-list">${responseRows}</ul>` : ""}
      <div class="preview-actions">
        <a class="master-btn secondary" href="${escapeHtml(detail.explorerUrl || "/")}" target="_blank" rel="noopener">Open in Explorer ↗</a>
        ${detail.storyUrl ? `<a class="master-btn secondary" href="${escapeHtml(detail.storyUrl)}" target="_blank" rel="noopener">Full spec story ↗</a>` : ""}
      </div>
    </div>`;
  }

  function appendParsedMessageBlock(container, msg, filename) {
    const block = document.createElement("div");
    block.className = "message-block";

    const header = document.createElement("div");
    header.className = "message-header";
    const badge = document.createElement("span");
    badge.className = `method-badge ${msg.method || "default"}`;
    badge.textContent = msg.method || "?";
    const pathEl = document.createElement("span");
    pathEl.className = "op-path";
    pathEl.textContent = msg.path;
    header.appendChild(badge);
    header.appendChild(pathEl);
    block.appendChild(header);

    if (msg.operationId) {
      const opId = document.createElement("div");
      opId.className = "op-id";
      opId.textContent = `operationId: ${msg.operationId}`;
      block.appendChild(opId);
    }

    if (msg.summary) {
      const summary = document.createElement("div");
      summary.className = "op-summary";
      summary.textContent = msg.summary;
      block.appendChild(summary);
    }

    if (msg.parameters?.length) {
      block.appendChild(
        createCollapsibleSection(
          "Parameters",
          msg.parameters.map((p) => `${p.in}: ${p.name} (required: ${p.required})`)
        )
      );
    }

    const reqFields = msg.requestBodyRequiredFields || msg.request_body_required_fields;
    if (reqFields?.length) {
      block.appendChild(createCollapsibleSection("Request Body Fields", reqFields));
    }

    if (msg.responses?.length) {
      block.appendChild(
        createCollapsibleSection(
          "Responses",
          msg.responses.map((r) => {
            const code = r.statusCode || r.status_code;
            return `${code}: ${r.description}`;
          })
        )
      );
    }

    container.appendChild(block);
    return block;
  }

  window.MessageDetail = {
    escapeHtml,
    createCollapsibleSection,
    renderOperationDetailHtml,
    appendParsedMessageBlock,
  };
})();
