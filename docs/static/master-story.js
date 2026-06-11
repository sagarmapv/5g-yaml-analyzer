const { escapeHtml, renderFlow, renderPreviewContent, renderJourneyLegend } = window.FlowRenderer;

const previewCache = new Map();
const HUB_CACHE_KEY = "master-story-hub-v4";

function storyIdFromUrl() {
  return new URLSearchParams(window.location.search).get("id") || "pdu-session-sm-policy";
}

function nfMapFromLens(nfLens) {
  const map = {};
  for (const lens of nfLens || []) {
    map[lens.nf] = { storyUrl: lens.storyUrl, primarySpec: lens.primarySpec };
  }
  return map;
}

function partitionNfLens(data) {
  if (data.nfInFlow?.length || data.nfEcosystem?.length) {
    return { inFlow: data.nfInFlow || [], ecosystem: data.nfEcosystem || [] };
  }
  const order = data.flowNfOrder || [];
  const rank = Object.fromEntries(order.map((nf, i) => [nf, i]));
  const inFlow = [];
  const ecosystem = [];
  for (const lens of data.nfLens || []) {
    const item = {
      ...lens,
      inFlow: lens.nf in rank,
      flowOrder: rank[lens.nf] ?? -1,
    };
    if (item.inFlow) inFlow.push(item);
    else ecosystem.push(item);
  }
  inFlow.sort((a, b) => a.flowOrder - b.flowOrder);
  ecosystem.sort((a, b) => a.nf.localeCompare(b.nf));
  return { inFlow, ecosystem };
}

function hubCardClass(item, kind) {
  if (kind === "nf") {
    if (item.inSpec) return "hub-card journey-focus";
    if (item.inFlow) return "hub-card hub-card--in-flow";
    return "hub-card hub-card--ecosystem";
  }
  return "hub-card hub-card--stitch";
}

function renderHubCard(item, kind) {
  const cls = hubCardClass(item, kind);
  if (kind === "stitch") {
    return `<div class="${cls}">
      <h3><span class="gap-priority">${escapeHtml(item.priority || "")}</span> TS ${escapeHtml(item.ts)}</h3>
      <span class="hub-card-meta">Supporting spec</span>
      <p>${escapeHtml(item.title)}</p>
      <p class="hub-card-role">${escapeHtml(item.role || "")}</p>
      <div class="hub-card-actions">
        <button type="button" class="nf-preview-btn" data-preview-ts="${escapeHtml(item.ts)}">Preview</button>
        <a href="${escapeHtml(item.storyUrl)}" target="_blank" rel="noopener">Full story ↗</a>
      </div>
    </div>`;
  }

  const ts = escapeHtml(item.primarySpec);
  const nf = escapeHtml(item.nf);
  const flowBadge = item.inFlow
    ? `<span class="hub-card-badge hub-card-badge--flow">In flow</span>`
    : `<span class="hub-card-badge">Related</span>`;
  const ownedBadge = item.inSpec ? `<span class="hub-card-badge hub-card-badge--owned">In 29.512</span>` : "";

  return `<div class="${cls}" data-preview-ts="${ts}" data-preview-label="${nf}" tabindex="0" role="button">
    <div class="hub-card-head">
      <h3>${nf}</h3>
      ${ownedBadge}${flowBadge}
    </div>
    <span class="hub-card-meta">TS ${ts}</span>
    <p class="hub-card-role">${escapeHtml(item.role)}</p>
    <div class="hub-card-actions">
      <button type="button" class="nf-preview-btn" data-preview-ts="${ts}" data-preview-label="${nf}">Preview</button>
      <a href="${escapeHtml(item.storyUrl)}" target="_blank" rel="noopener">Full story ↗</a>
    </div>
  </div>`;
}

function renderFlowNfStrip(order, nfLens) {
  const map = Object.fromEntries((nfLens || []).map((l) => [l.nf, l]));
  const chips = (order || [])
    .map((nf) => {
      const lens = map[nf];
      if (!lens) return "";
      const cls = lens.inSpec ? "flow-nf-chip flow-nf-chip--owned" : "flow-nf-chip";
      const ts = escapeHtml(lens.primarySpec);
      const label = escapeHtml(nf);
      return `<button type="button" class="${cls}" data-preview-ts="${ts}" data-preview-label="${label}">${label}</button>`;
    })
    .join("");
  if (!chips) return "";
  return `<div class="flow-nf-strip-wrap">
    <p class="flow-nf-strip-label">NFs in this flow (in order)</p>
    <div class="flow-nf-strip" role="toolbar" aria-label="Network functions in call flow order">${chips}</div>
  </div>`;
}

function renderMaster(data) {
  document.title = `${data.title} — Master Story`;
  document.getElementById("master-title").textContent = data.title;
  document.getElementById("master-tagline").textContent = data.tagline || "";

  const storyId = data.id || storyIdFromUrl();
  const ladderUrl = data.ladderUrl || `/ladder?id=${encodeURIComponent(storyId)}&nfs=SMF,PCF`;

  const { inFlow, ecosystem } = partitionNfLens(data);
  const flowOrder = data.flowNfOrder || inFlow.map((l) => l.nf);

  const flowHtml = renderFlow(data.enrichedE2eFlow, data.anchorSpec, {
    mode: "master",
    nfMap: nfMapFromLens(data.nfLens),
    showLegend: false,
  });

  const nfStrip = renderFlowNfStrip(flowOrder, data.nfLens);
  const nfFlowGrid = inFlow.map((l) => renderHubCard(l, "nf")).join("");
  const nfEcoGrid = ecosystem.map((l) => renderHubCard(l, "nf")).join("");
  const stitchCards = (data.supportingSpecs || []).map((s) => renderHubCard(s, "stitch")).join("");
  const pageLegend = renderJourneyLegend({ hub: true });

  document.getElementById("master-main").innerHTML = `
    <section class="master-hero">
      <h2>PDU session journey</h2>
      <p>${escapeHtml(data.summary || "")}</p>
      ${data.whyItMatters ? `<p>${escapeHtml(data.whyItMatters)}</p>` : ""}
      <div class="master-actions">
        <a class="master-btn" href="${escapeHtml(data.anchorStoryUrl)}" target="_blank" rel="noopener">Anchor spec story ↗</a>
        <a class="master-btn secondary" href="${escapeHtml(data.anchorPlatformUrl)}" target="_blank" rel="noopener">Specs platform ↗</a>
        <a class="master-btn secondary" href="${escapeHtml(ladderUrl)}">Open signaling ladder →</a>
      </div>
    </section>

    ${pageLegend}

    <section class="master-section master-flow-section" id="sec-flow">
      <h2>End-to-end call flow</h2>
      <p class="section-desc">Follow the establishment sequence — green steps are owned by TS 29.512. Click an NF chip or actor to preview inline. For message-level detail, use the <a href="${escapeHtml(ladderUrl)}">signaling ladder</a>.</p>
      ${nfStrip}
      ${flowHtml}
      <aside class="master-preview-panel hidden" id="master-preview-panel" aria-live="polite">
        <div class="master-preview-toolbar">
          <span id="master-preview-title">Preview</span>
          <button type="button" id="master-preview-close" class="master-preview-close" aria-label="Close preview">×</button>
        </div>
        <div id="master-preview-body" class="master-preview-body"></div>
      </aside>
    </section>

    <section class="master-section" id="sec-nf-flow">
      <h2>NFs in this flow</h2>
      <p class="section-desc">These network functions appear as actors in the call flow above — same set, same order.</p>
      <div class="hub-card-grid">${nfFlowGrid}</div>
    </section>

    ${
      ecosystem.length
        ? `<section class="master-section master-ecosystem-section" id="sec-nf-ecosystem">
      <h2>Related NFs</h2>
      <p class="section-desc">Part of the 29.512 service model but not direct actors in this establishment sequence (e.g. policy data stores, exposure, charging).</p>
      <div class="hub-card-grid hub-card-grid--ecosystem">${nfEcoGrid}</div>
    </section>`
        : ""
    }

    <section class="master-section" id="sec-stitch">
      <h2>Supporting spec stories</h2>
      <p class="section-desc">Stage-2 procedures, architecture, SBI principles, and signalling flows in this journey.</p>
      <div class="hub-card-grid">${stitchCards}</div>
    </section>
  `;

  bindPreviewHandlers();
}

function showPreviewPanel(label) {
  const panel = document.getElementById("master-preview-panel");
  const title = document.getElementById("master-preview-title");
  if (panel) panel.classList.remove("hidden");
  if (title) title.textContent = label ? `${label} preview` : "Preview";
  panel?.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function hidePreviewPanel() {
  document.getElementById("master-preview-panel")?.classList.add("hidden");
}

async function openPreview(ts, label) {
  const body = document.getElementById("master-preview-body");
  if (!body) return;
  showPreviewPanel(label || `TS ${ts}`);
  body.innerHTML = "<p class=\"loading\">Loading preview…</p>";

  let preview = previewCache.get(ts);
  if (!preview) {
    try {
      const res = await fetch(`/api/specs/${encodeURIComponent(ts)}/preview`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      preview = await res.json();
      previewCache.set(ts, preview);
    } catch (err) {
      body.innerHTML = `<p class="loading">Failed to load preview: ${escapeHtml(err.message)}</p>`;
      return;
    }
  }
  body.innerHTML = renderPreviewContent(preview);
}

function bindPreviewHandlers() {
  const onPreviewClick = (e) => {
    const btn = e.target.closest("[data-preview-ts]");
    if (!btn) return;
    if (btn.classList.contains("ref-spec-expand")) e.preventDefault();
    const ts = btn.getAttribute("data-preview-ts");
    const label = btn.getAttribute("data-preview-label") || btn.textContent?.trim();
    if (ts) openPreview(ts, label);
  };

  document.getElementById("master-main")?.addEventListener("click", onPreviewClick);
  document.getElementById("master-preview-close")?.addEventListener("click", hidePreviewPanel);
}

function cacheHubData(id, data) {
  try {
    sessionStorage.setItem(`${HUB_CACHE_KEY}:${id}`, JSON.stringify(data));
  } catch {
    /* quota */
  }
}

function loadCachedHub(id) {
  try {
    const raw = sessionStorage.getItem(`${HUB_CACHE_KEY}:${id}`);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

async function init() {
  const id = storyIdFromUrl();
  const cached = loadCachedHub(id);
  if (cached) renderMaster(cached);

  try {
    const res = await fetch(`/api/stories/${encodeURIComponent(id)}?view=hub`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    cacheHubData(id, data);
    renderMaster(data);
  } catch (err) {
    if (!cached) {
      document.getElementById("master-main").innerHTML = `<p class="loading">Failed to load story: ${escapeHtml(err.message)}</p>`;
    }
  }
}

init();
