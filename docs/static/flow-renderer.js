/** Shared E2E flow timeline renderer with deep links to spec stories and NF lenses. */
(function () {
  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text ?? "";
    return div.innerHTML;
  }

  function badge(type, label) {
    return `<span class="badge ${type}">${escapeHtml(label)}</span>`;
  }

  function flowStepClass(step, ts) {
    if (step.in512 || (ts === "29.512" && step.inSpec)) return "in512";
    if (step.in502 || (ts === "29.502" && step.inSpec)) return "in502";
    if (step.inSpec) return "in-spec-step";
    return "";
  }

  function flowStepBadge(step, ts) {
    if (step.in512 || (ts === "29.512" && step.inSpec)) return badge("in-spec", "in this spec");
    if (step.in502 || (ts === "29.502" && step.inSpec)) return badge("in-spec", "in this spec");
    if (step.inSpec) return badge("in-spec", "in this spec");
    return "";
  }

  function renderJourneyLegend(options) {
    const opts = options || {};
    const hub = opts.hub;
    return `<div class="journey-legend" role="note">
      <span class="journey-legend-item"><span class="journey-dot journey-dot-owned"></span> ${hub ? "Step owned by anchor spec (29.512)" : "Defined in this spec"}</span>
      <span class="journey-legend-item"><span class="journey-dot journey-dot-flow"></span> ${hub ? "NF appears in flow below" : "In call flow"}</span>
      ${hub ? `<span class="journey-legend-item"><span class="badge neighbor">TS</span> Opens in new tab</span>` : `<span class="journey-legend-item"><span class="badge neighbor">TS</span> Related spec</span>`}
    </div>`;
  }

  function renderStitchRefs(refs, options) {
    const opts = options || {};
    const target = opts.newTab ? ' target="_blank" rel="noopener"' : "";
    if (!refs?.length) return "";
    return `<div class="stitch-refs">${refs
      .map(
        (r) =>
          `<a class="stitch-ref" href="${escapeHtml(r.storyUrl)}#sec-clauses"${target}>TS ${escapeHtml(r.ts)} §${escapeHtml(r.clause)}${r.title ? ` — ${escapeHtml(r.title.slice(0, 48))}${r.title.length > 48 ? "…" : ""}` : ""}</a>`
      )
      .join("")}</div>`;
  }

  function renderActors(actors, nfMap, options) {
    const opts = options || {};
    if (!actors?.length) return "";
    return actors
      .map((actor) => {
        const info = nfMap?.[actor];
        if (opts.expandActors && info?.primarySpec) {
          return `<button type="button" class="actor-expand" data-preview-ts="${escapeHtml(info.primarySpec)}" data-preview-label="${escapeHtml(actor)}">${escapeHtml(actor)}</button>`;
        }
        if (info?.storyUrl) {
          const target = opts.newTab ? ' target="_blank" rel="noopener"' : "";
          return `<a href="${escapeHtml(info.storyUrl)}" class="actor-link"${target}>${escapeHtml(actor)}</a>`;
        }
        return escapeHtml(actor);
      })
      .join(" → ");
  }

  function renderRefSpecLink(refSpec, options) {
    const opts = options || {};
    if (!refSpec) return "";
    const target = opts.newTab ? ' target="_blank" rel="noopener"' : "";
    const expand = opts.expandActors
      ? ` class="meta-chip meta-chip-link ref-spec-expand" data-preview-ts="${escapeHtml(refSpec)}" href="#"`
      : ` class="meta-chip meta-chip-link" href="/specs/${encodeURIComponent(refSpec)}"${target}`;
    return `<a${expand}>TS ${escapeHtml(refSpec)}</a>`;
  }

  function renderStepLayerChain(step, options) {
    const opts = options || {};
    const hint = step.layerHint;
    if (!hint) return "";
    const parts = [];
    const target = opts.newTab ? ' target="_blank" rel="noopener"' : "";
    if (hint.procedureTs) {
      parts.push(
        `<span class="flow-layer-part"><span class="flow-layer-label">Procedure</span> <a href="/specs/${encodeURIComponent(hint.procedureTs)}"${target}>TS ${escapeHtml(hint.procedureTs)}</a></span>`
      );
    }
    if (hint.nfs?.length) {
      parts.push(
        `<span class="flow-layer-part"><span class="flow-layer-label">NF</span> ${escapeHtml(hint.nfs.join(" → "))}</span>`
      );
    }
    if (hint.serviceTs) {
      parts.push(
        `<span class="flow-layer-part"><span class="flow-layer-label">Service</span> <a href="/specs/${encodeURIComponent(hint.serviceTs)}"${target}>TS ${escapeHtml(hint.serviceTs)}</a></span>`
      );
    }
    if (hint.operationId) {
      const opUrl = `/?q=${encodeURIComponent(hint.operationId)}`;
      parts.push(
        `<span class="flow-layer-part"><span class="flow-layer-label">Message</span> <a href="${escapeHtml(opUrl)}"${target}><code>${escapeHtml(hint.operationId)}</code></a></span>`
      );
    }
    if (!parts.length) return "";
    const titleParts = [];
    if (hint.procedureTs) titleParts.push(`Procedure TS ${hint.procedureTs}`);
    if (hint.nfs?.length) titleParts.push(`NF ${hint.nfs.join(" → ")}`);
    if (hint.serviceTs) titleParts.push(`Service TS ${hint.serviceTs}`);
    if (hint.operationId) titleParts.push(`Message ${hint.operationId}`);
    return `<div class="flow-step-layers" title="${escapeHtml(titleParts.join(" · "))}">${parts.join('<span class="flow-layer-sep">→</span>')}</div>`;
  }

  function renderOperationLink(operationId, anchorTs, options) {
    const opts = options || {};
    if (!operationId) return "";
    const target = opts.newTab ? ' target="_blank" rel="noopener"' : "";
    if (anchorTs === "29.512" || opts.linkOperations) {
      return ` <a class="op-link" href="/?q=${encodeURIComponent(operationId)}"${target}><code>${escapeHtml(operationId)}</code></a>`;
    }
    return ` <code>${escapeHtml(operationId)}</code>`;
  }

  function renderFlow(flow, ts, options) {
    const opts = options || {};
    const nfMap = opts.nfMap || {};
    const mode = opts.mode || "spec";
    const master = mode === "master";
    if (!flow?.steps?.length) return "<p>No end-to-end flow defined.</p>";

    const linkOpts = { newTab: master, expandActors: master };
    const refSpecs = flow.refSpecs || [];
    const refs = refSpecs
      .map((r) => {
        const rts = typeof r === "string" ? r : r.ts;
        const role = typeof r === "string" ? "" : ` (${escapeHtml(r.role)})`;
        const target = master ? ' target="_blank" rel="noopener"' : "";
        return `<a href="/specs/${encodeURIComponent(rts)}"${target}>TS ${escapeHtml(rts)}</a>${role}`;
      })
      .join(" · ");

    const hint = master
      ? "Green steps = owned by TS 29.512 · blue NF chips match the grid below · click an actor to preview"
      : "Green marker = step defined in this spec · blue chips = related specs";

    const layerOpts = { newTab: master };
    const steps = flow.steps
      .map(
        (s) => `<li class="flow-step ${flowStepClass(s, ts)}">
      <span class="step-num">Step ${s.order}</span>
      <div class="actors">${renderActors(s.actors, nfMap, linkOpts)}</div>
      <h4>${escapeHtml(s.action)}</h4>
      ${renderStepLayerChain(s, layerOpts)}
      ${flowStepBadge(s, ts)}
      ${renderOperationLink(s.operationId, ts, { linkOperations: true, newTab: master })}
      ${renderRefSpecLink(s.refSpec, linkOpts)}
      ${renderStitchRefs(s.stitchRefs, linkOpts)}
    </li>`
      )
      .join("");

    const legend =
      opts.showLegend === false ? "" : renderJourneyLegend({ hub: master });
    return `${legend}<p><strong>${escapeHtml(flow.name)}</strong>${refs ? `<br><span class="flow-refs">${refs}</span>` : ""}</p><p class="flow-hint">${escapeHtml(hint)}</p><ol class="flow-timeline">${steps}</ol>`;
  }

  function renderPreviewContent(preview) {
    if (!preview) return "<p class=\"loading\">Loading preview…</p>";
    const hints = preview.layerHints || {};
    const layerChain = [];
    if (hints.architectureTs) {
      layerChain.push(`<span>Procedure <a href="/specs/${encodeURIComponent(hints.architectureTs)}" target="_blank" rel="noopener">TS ${escapeHtml(hints.architectureTs)}</a></span>`);
    }
    layerChain.push(`<span>Service <strong>TS ${escapeHtml(preview.tsNumber)}</strong></span>`);
    const ops = (hints.operations || [])
      .map(
        (op) =>
          `<a href="${escapeHtml(op.explorerUrl)}" target="_blank" rel="noopener"><code>${escapeHtml(op.operationId)}</code></a>`
      )
      .join(" · ");
    if (ops) layerChain.push(`<span>Message ${ops}</span>`);

    const entryRows = (preview.entryPoints || [])
      .map((ep) => {
        const label = ep.operationId || ep.name || ep.type;
        return `<li>${escapeHtml(label)} — ${escapeHtml(ep.description || "")}</li>`;
      })
      .join("");

    const stepRows = (preview.e2eFlowSteps || [])
      .map(
        (s) =>
          `<li><span class="step-num">Step ${s.order}</span> ${escapeHtml((s.actors || []).join(" → "))}: ${escapeHtml(s.action)}</li>`
      )
      .join("");

    const messageLinks = (hints.operations || [])
      .map(
        (op) =>
          `<a class="master-btn secondary" href="${escapeHtml(op.explorerUrl)}" target="_blank" rel="noopener">See ${escapeHtml(op.operationId)} JSON ↗</a>`
      )
      .join("");

    return `<div class="preview-head">
      <h3>${escapeHtml(preview.primaryNf || preview.tsNumber)} · TS ${escapeHtml(preview.tsNumber)}</h3>
      <p class="preview-tagline">${escapeHtml(preview.tagline || preview.summary || "")}</p>
    </div>
    <div class="preview-layer-chain">${layerChain.join('<span class="preview-layer-sep">→</span>')}</div>
    ${entryRows ? `<h4 class="preview-sub">Entry points</h4><ul class="preview-list">${entryRows}</ul>` : ""}
    ${stepRows ? `<h4 class="preview-sub">In this journey</h4><ol class="preview-steps">${stepRows}</ol>` : ""}
    <div class="preview-actions">
      <a class="master-btn secondary" href="${escapeHtml(preview.storyUrl)}" target="_blank" rel="noopener">Full story ↗</a>
      <a class="master-btn secondary" href="${escapeHtml(preview.platformUrl)}" target="_blank" rel="noopener">Specs platform ↗</a>
      ${messageLinks}
    </div>`;
  }

  function renderBlockerChips(blockers) {
    if (!blockers?.length) {
      return `<span class="badge in-spec">ready</span>`;
    }
    return blockers
      .map((b) => `<span class="ready-chip off blocker-chip">${escapeHtml(b)}</span>`)
      .join(" ");
  }

  function storyKindBadge(kind) {
    if (kind === "full") return badge("in-spec", "full story");
    if (kind === "pdf-clauses") return badge("sbi", "PDF clauses");
    return badge("neighbor", "gap");
  }

  function renderNfGapsTable(nfGaps, options) {
    const opts = options || {};
    const compact = Boolean(opts.compact);
    if (!nfGaps?.items?.length) return "";

    const meta = nfGaps.meta || {};
    const rows = nfGaps.items.filter((item) => !item.hasFullNarrative || !item.ready);
    if (!rows.length) {
      return `<p class="nf-gaps-headline nf-gaps-complete">All ${meta.total || nfGaps.items.length} NFs have dedicated narrative pages and all sources are ready.</p>`;
    }

    const headlineParts = [];
    if (meta.fullNarrative != null && meta.total != null) {
      headlineParts.push(`${meta.fullNarrative}/${meta.total} NFs have dedicated narrative pages.`);
    }
    if (meta.ready != null && meta.total != null) {
      headlineParts.push(`${meta.ready}/${meta.total} have all sources ready (PDF + YAML + story).`);
    }
    const headline =
      headlineParts.join(" ") ||
      `${rows.length} NF stor${rows.length !== 1 ? "ies" : "y"} still need work.`;

    const tableRows = rows
      .map((item) => {
        const importCell = item.needsPdf
          ? `<code class="import-hint">${escapeHtml(item.importHint || "")}</code>`
          : "—";
        const actionCell = `<a href="${escapeHtml(item.storyUrl)}">Open story →</a>`;
        const roleCell = compact
          ? escapeHtml((item.role || "").slice(0, 60) + ((item.role || "").length > 60 ? "…" : ""))
          : escapeHtml(item.role || "");
        return `<tr>
        <td><strong>${escapeHtml(item.nf)}</strong></td>
        <td><a href="${escapeHtml(item.storyUrl)}">TS ${escapeHtml(item.primarySpec)}</a></td>
        ${compact ? "" : `<td>${roleCell}</td>`}
        <td>${storyKindBadge(item.storyKind || (item.hasFullNarrative ? "full" : "gap"))}</td>
        <td class="blocker-cell">${renderBlockerChips(item.blockers)}</td>
        <td>${importCell}</td>
        <td>${actionCell}</td>
      </tr>`;
      })
      .join("");

    const headers = compact
      ? `<tr><th>NF</th><th>Primary TS</th><th>Story</th><th>Missing</th><th>Import PDF</th><th>Action</th></tr>`
      : `<tr><th>NF</th><th>Primary TS</th><th>Role</th><th>Story</th><th>Missing</th><th>Import PDF</th><th>Action</th></tr>`;

    return `<p class="nf-gaps-headline">${escapeHtml(headline)}</p>
    <div class="table-scroll nf-gaps-scroll">
      <table class="story-table nf-gaps-table">
        <thead>${headers}</thead>
        <tbody>${tableRows}</tbody>
      </table>
    </div>`;
  }

  window.FlowRenderer = {
    escapeHtml,
    badge,
    flowStepClass,
    flowStepBadge,
    renderJourneyLegend,
    renderStitchRefs,
    renderActors,
    renderRefSpecLink,
    renderStepLayerChain,
    renderFlow,
    renderPreviewContent,
    renderNfGapsTable,
  };
})();
