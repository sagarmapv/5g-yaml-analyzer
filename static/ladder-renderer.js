/** Static UE→NFs→UE sequence ladder with multi-NF highlight and inline expand. */
(function () {
  const { escapeHtml } = window.FlowRenderer;

  function isMessageHighlighted(msg, selectedSet) {
    const selected = selectedSet || new Set();
    if (!selected.size) return true;
    if (selected.size === 1) {
      const nf = [...selected][0];
      return msg.from === nf || msg.to === nf;
    }
    return selected.has(msg.from) && selected.has(msg.to);
  }

  function actorLabel(actor, index, total) {
    if (actor === "UE" && index === total - 1) return "UE";
    return actor;
  }

  function messageRowClass(msg, anchorSpec, highlighted) {
    const base = ["ladder-msg"];
    if (!highlighted) base.push("ladder-msg--dimmed");
    if (msg.messageKind === "n4" || msg.messageKind === "procedural") {
      base.push("ladder-msg--procedural");
      return base.join(" ");
    }
    if (msg.serviceTs === anchorSpec && msg.inAnchor) {
      base.push("ladder-msg--anchor");
    } else {
      base.push("ladder-msg--sbi");
    }
    return base.join(" ");
  }

  function renderMessageLabel(msg) {
    if (msg.operationId) {
      const dir =
        msg.direction === "response" ? " ←" : msg.direction === "notify" ? " ⇢" : " →";
      return `${escapeHtml(msg.operationId)}${dir}`;
    }
    return escapeHtml(msg.label || msg.action || "procedural");
  }

  function formatJsonBlock(obj) {
    if (obj == null) return "";
    const esc = window.MessageDetail?.escapeHtml || escapeHtml;
    return `<pre class="ladder-json-block">${esc(JSON.stringify(obj, null, 2))}</pre>`;
  }

  function renderInlineRequestDetail(detail) {
    if (!detail) return "<p class=\"loading\">No request detail.</p>";
    const esc = window.MessageDetail?.escapeHtml || escapeHtml;

    const env = detail.envelope;
    let envelopeHtml = "";
    if (env) {
      envelopeHtml = `<h4 class="preview-sub">Headers (JSON)</h4>
        ${formatJsonBlock(env.headers)}
        <h4 class="preview-sub">Body (JSON)</h4>
        ${env.body && env.body.json ? formatJsonBlock(env.body.json) : "<p class=\"loading\">No example body fixture.</p>"}`;
    }

    const headerRows = (detail.requestHeaders || [])
      .map(
        (h) =>
          `<li><code>${esc(h.name)}</code>${h.required ? " (required)" : ""}${h.schemaRef ? ` → ${esc(h.schemaRef)}` : ""}</li>`
      )
      .join("");
    const pathRows = (detail.pathParams || [])
      .map((p) => `<li><code>${esc(p.name)}</code> path${p.required ? " (required)" : ""}</li>`)
      .join("");
    const queryRows = (detail.queryParams || [])
      .map((q) => `<li><code>${esc(q.name)}</code> query${q.required ? " (required)" : ""}</li>`)
      .join("");

    let bodyHtml = "";
    if (detail.request) {
      const r = detail.request;
      const propRows = (r.properties || [])
        .map(
          (p) =>
            `<li><code>${esc(p.name)}</code> <span class="ladder-prop-type">${esc(p.type || "")}</span>${p.required ? " *" : ""}</li>`
        )
        .join("");
      bodyHtml = `<h4 class="preview-sub">Request body</h4>
        <ul class="preview-list">
          <li>Content-Type: <code>${esc(r.contentType || "")}</code></li>
          ${r.schemaRef ? `<li>Schema: <code>${esc(r.schemaRef)}</code></li>` : ""}
          ${(r.requiredProperties || []).length ? `<li>Required: ${r.requiredProperties.map((f) => `<code>${esc(f)}</code>`).join(", ")}</li>` : ""}
        </ul>
        ${propRows ? `<ul class="preview-list ladder-prop-list">${propRows}</ul>` : ""}`;
    }

    return `<div class="ladder-inline-detail">
      <div class="message-header">
        <span class="method-badge ${esc((detail.method || "default").toLowerCase())}">${esc(detail.method || "?")}</span>
        <span class="op-path">${esc(detail.path || "")}</span>
      </div>
      <p class="op-id"><code>${esc(detail.operationId || "")}</code></p>
      ${pathRows ? `<h4 class="preview-sub">Path parameters</h4><ul class="preview-list">${pathRows}</ul>` : ""}
      ${queryRows ? `<h4 class="preview-sub">Query parameters</h4><ul class="preview-list">${queryRows}</ul>` : ""}
      ${envelopeHtml || ""}
      ${!envelopeHtml && headerRows ? `<h4 class="preview-sub">Request headers</h4><ul class="preview-list">${headerRows}</ul>` : ""}
      ${!envelopeHtml ? bodyHtml : ""}
      <div class="preview-actions">
        <a class="master-btn secondary" href="${esc(detail.explorerUrl || "/")}" target="_blank" rel="noopener">Open in Explorer ↗</a>
      </div>
    </div>`;
  }

  function renderProceduralInline(msg) {
    const kindNote =
      msg.messageKind === "n4"
        ? "<p>N4 / PFCP — not OpenAPI in this corpus.</p>"
        : "";
    return `<div class="ladder-inline-detail ladder-inline-detail--procedural">
      <p>${escapeHtml(msg.action || msg.label)}</p>
      ${kindNote}
      ${msg.procedureTs ? `<p class="message-detail-meta">Procedure: TS ${escapeHtml(msg.procedureTs)}</p>` : ""}
      ${msg.payload ? `<p>Reference: <code>${escapeHtml(msg.payload)}</code></p>` : ""}
    </div>`;
  }

  function renderStaticLadder(actors, messages, selectedNfs, anchorSpec, expandedStep) {
    const selectedSet = new Set(selectedNfs || []);
    const colCount = actors.length;

    const headerCells = actors
      .map((actor, i) => {
        const active = selectedSet.has(actor) ? " ladder-lifeline-head--selected" : "";
        const label = actorLabel(actor, i, actors.length);
        const sub = i === 0 ? " (origin)" : i === actors.length - 1 ? " (term)" : "";
        return `<div class="ladder-lifeline-head${active}" data-col="${i}">${escapeHtml(label)}<span class="ladder-lifeline-sub">${sub}</span></div>`;
      })
      .join("");

    const lifelines = actors
      .map(
        (_, i) =>
          `<div class="ladder-lifeline-col" style="grid-column: ${i + 1}"><div class="ladder-lifeline-line"></div></div>`
      )
      .join("");

    const rows = (messages || [])
      .map((msg) => {
        const fromIdx = msg.fromIndex ?? actors.indexOf(msg.from);
        const toIdx = msg.toIndex ?? actors.indexOf(msg.to);
        const highlighted = isMessageHighlighted(msg, selectedSet);
        const cls = messageRowClass(msg, anchorSpec, highlighted);
        const start = Math.min(fromIdx, toIdx);
        const end = Math.max(fromIdx, toIdx);
        const expanded = expandedStep === msg.stepOrder;

        const attrs = `data-ladder-msg="1" data-step-order="${msg.stepOrder}"${
          msg.operationId && msg.hasMessageDetail
            ? ` data-operation-id="${escapeHtml(msg.operationId)}"`
            : ` data-procedural="1"`
        }`;

        const detailSlot =
          expanded
            ? `<div class="ladder-inline-expand" id="ladder-expand-${msg.stepOrder}">
            <div class="ladder-inline-expand-inner" data-detail-slot="${msg.stepOrder}"></div>
          </div>`
            : "";

        return `<div class="ladder-message-block ${highlighted ? "ladder-message-block--on" : "ladder-message-block--dim"}">
          <div class="ladder-message-row">
            <span class="ladder-step-num">S${msg.stepOrder}</span>
            <div class="ladder-track" style="--peer-count: ${colCount}">
              ${lifelines}
              <button type="button" class="${cls}" style="--col-start: ${start + 1}; --col-end: ${end + 2}" ${attrs} aria-expanded="${expanded}">
                <span class="ladder-arrow-label">${renderMessageLabel(msg)}</span>
                <span class="ladder-hop-endpoints">${escapeHtml(msg.from)} → ${escapeHtml(msg.to)}${msg.interface ? ` <span class="ladder-if-badge">${escapeHtml(msg.interface)}</span>` : ""}</span>
              </button>
            </div>
          </div>
          ${detailSlot}
        </div>`;
      })
      .join("");

    return `<div class="ladder-static" style="--peer-count: ${colCount}">
      <div class="ladder-header-row">
        <span class="ladder-step-num ladder-step-num--head"></span>
        <div class="ladder-track ladder-track--head">${headerCells}</div>
      </div>
      <div class="ladder-messages">${rows}</div>
    </div>`;
  }

  function renderActorSelector(actors, selectedNfs) {
    const selectedSet = new Set(selectedNfs || []);
    const unique = [];
    for (const actor of actors || []) {
      if (actor === "UE" && unique.includes("UE")) continue;
      unique.push(actor);
    }
    const chips = unique
      .map((actor) => {
        const active = selectedSet.has(actor) ? " ladder-actor-chip--active" : "";
        return `<button type="button" class="ladder-actor-chip${active}" data-ladder-actor="${escapeHtml(actor)}">${escapeHtml(actor)}</button>`;
      })
      .join("");
    return `<div class="ladder-actor-selector" role="toolbar" aria-label="Select NFs to highlight">${chips}
      <button type="button" class="ladder-actor-chip ladder-actor-chip--clear" data-ladder-clear="1">Clear</button>
    </div>`;
  }

  function renderLadderPage(data, options) {
    const opts = options || {};
    const selected = opts.selectedNfs || [];
    const expandedStep = opts.expandedStep ?? null;
    const actors = data.ladderActors || [];
    const messages = data.ladderMessages || [];
    const anchorSpec = data.anchorSpec || "29.512";

    const selectionHint =
      selected.length >= 2
        ? `Highlighting hops between: ${selected.map(escapeHtml).join(", ")}`
        : selected.length === 1
          ? `Highlighting hops involving ${escapeHtml(selected[0])}`
          : "All hops visible — select NFs to focus";

    return `${renderActorSelector(actors, selected)}
      <p class="section-desc ladder-filter-desc">${selectionHint}</p>
      ${renderStaticLadder(actors, messages, selected, anchorSpec, expandedStep)}`;
  }

  window.LadderRenderer = {
    isMessageHighlighted,
    renderStaticLadder,
    renderActorSelector,
    renderLadderPage,
    renderInlineRequestDetail,
    renderProceduralInline,
  };
})();
