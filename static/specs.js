const graphEl = document.getElementById("spec-graph");
const statusEl = document.getElementById("graph-status");
const searchEl = document.getElementById("search");
const depthEl = document.getElementById("depth");
const metaEl = document.getElementById("meta");
const refreshBtn = document.getElementById("refresh-btn");
const fitBtn = document.getElementById("fit-btn");
const detailPanel = document.getElementById("detail-panel");
const detailContent = document.getElementById("detail-content");
const detailToggle = document.getElementById("detail-toggle");
const focusChip = document.getElementById("focus-chip");
const focusLabel = document.getElementById("focus-label");
const clearFocusBtn = document.getElementById("clear-focus-btn");

const catalogSearchEl = document.getElementById("catalog-search");
const catalogFilterEl = document.getElementById("catalog-filter");
const catalogListEl = document.getElementById("catalog-list");
const catalogMetaEl = document.getElementById("catalog-meta");
const contextBar = document.getElementById("context-bar");
const contextTsEl = document.getElementById("context-ts");
const contextTitleEl = document.getElementById("context-title");
const ctxMap = document.getElementById("ctx-map");
const ctxStory = document.getElementById("ctx-story");
const ctxExplorer = document.getElementById("ctx-explorer");
const ctxTopology = document.getElementById("ctx-topology");
const ctxArchive = document.getElementById("ctx-archive");
const storyFrame = document.getElementById("story-frame");
const storyFrameWrap = document.getElementById("story-frame-wrap");
const viewMapEl = document.getElementById("view-map");
const viewStoryEl = document.getElementById("view-story");
const platformTabs = document.querySelectorAll(".platform-tab");

let network = null;
let platformData = { specs: [], map: { specs: [] } };
let mapData = { specs: [] };
let catalogItems = [];
let selectedTs = null;
let activeView = "map";
let focusedSpecTs = null;
let nfFilter = null;
const nodeMeta = new Map();

const COLORS = {
  root: { bg: "#444", border: "#666" },
  spec: { bg: "#f0c040", border: "#c9a020", font: "#1a1d23" },
  nf: { bg: "#4a9eff", border: "#2a7fd4", font: "#fff" },
  yaml: { bg: "#7ee787", border: "#5cb85c", font: "#1a1d23" },
};

const MAX_NODES_FULL = 120;
const MAX_SPECS_DEFAULT = 12;
const ANCHOR_TS = "29.512";

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function normalizeTs(ts) {
  if (!ts) return null;
  const t = ts.replace(/^TS\s*/i, "").trim();
  return /^\d{5}$/.test(t) ? `${t.slice(0, 2)}.${t.slice(2)}` : t;
}

function catalogEntry(ts) {
  return catalogItems.find((s) => s.tsNumber === ts);
}

function mapSpec(ts) {
  return (mapData.specs || []).find((s) => s.tsNumber === ts);
}

function updateUrl() {
  const params = new URLSearchParams();
  if (selectedTs) params.set("ts", selectedTs);
  if (activeView === "story") params.set("view", "story");
  const qs = params.toString();
  const next = qs ? `/specs?${qs}` : "/specs";
  if (`${window.location.pathname}${window.location.search}` !== next) {
    history.replaceState(null, "", next);
  }
}

function ensureVis() {
  if (typeof vis === "undefined" || !vis.Network) {
    throw new Error("Graph library not loaded. Hard-refresh (Ctrl+F5).");
  }
}

function badgeHtml(kind, label) {
  return `<span class="cat-badge cat-${kind}">${escapeHtml(label)}</span>`;
}

function renderCatalog() {
  const q = catalogSearchEl.value.trim().toLowerCase();
  const filter = catalogFilterEl.value;

  let items = [...catalogItems];
  if (filter === "yaml") items = items.filter((i) => i.hasYaml);
  else if (filter === "story") items = items.filter((i) => i.hasNarrative);
  else if (filter === "pdf") items = items.filter((i) => i.hasPdf);
  else if (filter === "stitch") items = items.filter((i) => i.isStitchSpec);
  else if (filter === "ref") items = items.filter((i) => i.referenceOnly);

  if (nfFilter) {
    const nf = nfFilter.toUpperCase();
    items = items.filter((i) => (i.nfServices || []).some((n) => n.toUpperCase() === nf));
  }

  if (q) {
    items = items.filter((i) =>
      [i.tsNumber, i.title, ...(i.nfServices || [])].join(" ").toLowerCase().includes(q)
    );
  }

  const meta = platformData.meta || {};
  catalogMetaEl.textContent = `${items.length} shown · ${meta.totalSpecs || catalogItems.length} total · ${meta.withStory || 0} stories · ${meta.withPdf || 0} PDFs`;

  if (!items.length) {
    catalogListEl.innerHTML = '<li class="catalog-placeholder">No specs match.</li>';
    return;
  }

  catalogListEl.innerHTML = items
    .map((item) => {
      const badges = [];
      if (item.isAnchorStory) badges.push(badgeHtml("anchor", "anchor"));
      if (item.hasYaml) badges.push(badgeHtml("yaml", "YAML"));
      if (item.hasNarrative) badges.push(badgeHtml("story", "story"));
      if (item.hasPdf) badges.push(badgeHtml("pdf", "PDF"));
      if (item.isStitchSpec) badges.push(badgeHtml("stitch", "512"));
      if (item.referenceOnly) badges.push(badgeHtml("ref", "ref"));

      const title = item.title?.startsWith("(referenced") ? "" : item.title;
      const sub = [
        item.yamlCount ? `${item.yamlCount} YAML` : null,
        item.nfCount ? `${item.nfCount} NF` : null,
        item.referenceCount && !item.hasYaml ? `${item.referenceCount} cites` : null,
      ]
        .filter(Boolean)
        .join(" · ");

      return `<li class="catalog-item${selectedTs === item.tsNumber ? " selected" : ""}" data-ts="${escapeHtml(item.tsNumber)}">
        <div class="catalog-item-head">
          <span class="catalog-ts">TS ${escapeHtml(item.tsNumber)}</span>
          <span class="catalog-badges">${badges.join("")}</span>
        </div>
        ${title ? `<div class="catalog-title">${escapeHtml(title.slice(0, 72))}${title.length > 72 ? "…" : ""}</div>` : ""}
        ${sub ? `<div class="catalog-sub">${escapeHtml(sub)}</div>` : ""}
      </li>`;
    })
    .join("");

  catalogListEl.querySelectorAll(".catalog-item").forEach((el) => {
    el.addEventListener("click", () => selectSpec(el.dataset.ts, { focusMap: activeView === "map" }));
  });
}

function updateContextBar() {
  if (!selectedTs) {
    contextBar.classList.add("hidden");
    return;
  }
  const item = catalogEntry(selectedTs);
  contextBar.classList.remove("hidden");
  contextTsEl.textContent = `TS ${selectedTs}`;
  contextTitleEl.textContent = item?.title?.startsWith("(referenced") ? "" : item?.title || "";

  const mapUrl = `/specs?ts=${encodeURIComponent(selectedTs)}&view=map`;
  const storyUrl = `/specs?ts=${encodeURIComponent(selectedTs)}&view=story`;
  ctxMap.href = mapUrl;
  ctxStory.href = storyUrl;

  const spec = mapSpec(selectedTs);
  const firstYaml = spec?.nfs?.[0]?.yamls?.[0]?.sourceFile;
  ctxExplorer.href = firstYaml ? `/?yaml=${encodeURIComponent(firstYaml)}` : `/specs?ts=${encodeURIComponent(selectedTs)}`;
  const nf = spec?.nfs?.[0]?.nf || item?.nfServices?.[0];
  ctxTopology.href = nf ? `/topology?nf=${encodeURIComponent(nf)}` : "/topology";

  if (item?.url) {
    ctxArchive.href = item.url;
    ctxArchive.classList.remove("hidden");
  } else {
    ctxArchive.classList.add("hidden");
  }
}

function loadStoryFrame(ts) {
  const hint = storyFrameWrap.querySelector(".story-pick-hint");
  if (!ts) {
    storyFrame.classList.add("hidden");
    if (hint) hint.classList.remove("hidden");
    storyFrame.removeAttribute("src");
    return;
  }
  if (hint) hint.classList.add("hidden");
  storyFrame.classList.remove("hidden");
  const src = `/specs/${encodeURIComponent(ts)}?embed=1`;
  if (storyFrame.getAttribute("src") !== src) {
    storyFrame.src = src;
  }
}

function setView(view) {
  activeView = view === "story" ? "story" : "map";
  platformTabs.forEach((tab) => {
    const on = tab.dataset.view === activeView;
    tab.classList.toggle("active", on);
    tab.setAttribute("aria-selected", on ? "true" : "false");
  });
  viewMapEl.classList.toggle("active", activeView === "map");
  viewMapEl.hidden = activeView !== "map";
  viewStoryEl.classList.toggle("active", activeView === "story");
  viewStoryEl.hidden = activeView !== "story";

  if (activeView === "story") {
    loadStoryFrame(selectedTs || ANCHOR_TS);
    if (!selectedTs) selectSpec(ANCHOR_TS, { focusMap: false, skipView: true });
  } else if (network) {
    setTimeout(() => network.fit({ animation: true }), 80);
  }
  updateUrl();
}

function selectSpec(ts, opts = {}) {
  ts = normalizeTs(ts);
  if (!ts) return;
  selectedTs = ts;
  if (opts.focusMap !== false) {
    focusedSpecTs = ts;
    updateFocusUI();
    renderGraph();
    const item = catalogEntry(ts);
    if (item) showSpecSummaryFromCatalog(item);
  }
  renderCatalog();
  updateContextBar();
  if (!opts.skipView && activeView === "story") loadStoryFrame(ts);
  updateUrl();
}

function updateFocusUI() {
  if (focusedSpecTs) {
    focusChip.classList.remove("hidden");
    focusLabel.textContent = focusedSpecTs;
  } else {
    focusChip.classList.add("hidden");
  }
}

function setFocus(tsNumber) {
  selectSpec(tsNumber, { focusMap: true });
}

function clearFocus() {
  focusedSpecTs = null;
  selectedTs = null;
  updateFocusUI();
  updateContextBar();
  renderCatalog();
  renderGraph();
  updateUrl();
}

function filterSpecs(specs, query) {
  const q = query.trim().toLowerCase();
  if (!q) return specs;
  return specs.filter((spec) => {
    const haystack = [
      spec.tsNumber,
      spec.title,
      ...(spec.nfs || []).flatMap((n) => [
        n.nf,
        ...(n.yamls || []).map((y) => `${y.service} ${y.sourceFile}`),
      ]),
    ]
      .join(" ")
      .toLowerCase();
    return haystack.includes(q);
  });
}

function prepareSpecsForTree(allSpecs) {
  const q = searchEl.value.trim();
  let specs = filterSpecs(allSpecs, q);
  let capped = false;

  if (focusedSpecTs) {
    specs = specs.filter((spec) => spec.tsNumber === focusedSpecTs);
    if (!specs.length) {
      specs = allSpecs.filter((spec) => spec.tsNumber === focusedSpecTs);
    }
  } else if (!q && specs.length > MAX_SPECS_DEFAULT) {
    specs = specs.slice(0, MAX_SPECS_DEFAULT);
    capped = true;
  }

  return { specs, capped };
}

function buildGraphData(specs, maxDepth) {
  nodeMeta.clear();
  const nodes = [];
  const edges = [];
  let nodeCount = 0;

  const rootId = "root:sbi";
  nodes.push({
    id: rootId,
    label: "3GPP SBI",
    title: focusedSpecTs ? "Click to show all specs again" : "Root — all 3GPP service specs",
    level: 0,
    color: { background: COLORS.root.bg, border: COLORS.root.border },
    font: { color: "#ccc", size: 14 },
    shape: "box",
    margin: 10,
  });
  nodeMeta.set(rootId, { type: "root" });

  for (const spec of specs) {
    const specId = `spec:${spec.tsNumber}`;
    nodes.push({
      id: specId,
      label: `TS ${spec.tsNumber}`,
      title: `${spec.title || specId}\nClick to focus this spec`,
      level: 1,
      color: { background: COLORS.spec.bg, border: COLORS.spec.border },
      font: { color: COLORS.spec.font, size: 13 },
      shape: "box",
      margin: 8,
    });
    nodeMeta.set(specId, { type: "spec", data: spec });
    edges.push({ from: rootId, to: specId });
    nodeCount++;

    for (const nfBlock of spec.nfs || []) {
      const nfId = `nf:${spec.tsNumber}:${nfBlock.nf}`;
      nodes.push({
        id: nfId,
        label: nfBlock.nf,
        title: `${nfBlock.nf} under TS ${spec.tsNumber}`,
        level: 2,
        color: { background: COLORS.nf.bg, border: COLORS.nf.border },
        font: { color: COLORS.nf.font, size: 12 },
        shape: "ellipse",
      });
      nodeMeta.set(nfId, { type: "nf", spec, nf: nfBlock.nf });
      edges.push({ from: specId, to: nfId });
      nodeCount++;

      if (maxDepth >= 3) {
        for (const entry of nfBlock.yamls || []) {
          if (nodeCount >= MAX_NODES_FULL) {
            return { nodes, edges, truncated: true, nodeCount };
          }
          const yamlId = `yaml:${entry.sourceFile}`;
          const shortName =
            entry.service.length > 28 ? `${entry.service.slice(0, 26)}…` : entry.service;
          nodes.push({
            id: yamlId,
            label: shortName,
            title: entry.sourceFile,
            level: 3,
            color: { background: COLORS.yaml.bg, border: COLORS.yaml.border },
            font: { color: COLORS.yaml.font, size: 10 },
            shape: "dot",
            size: 14,
          });
          nodeMeta.set(yamlId, { type: "yaml", spec, nf: nfBlock.nf, entry });
          edges.push({ from: nfId, to: yamlId });
          nodeCount++;
        }
      }
    }
  }

  return { nodes, edges, truncated: false, nodeCount };
}

function renderGraph() {
  try {
    ensureVis();
    graphEl.innerHTML = "";

    const maxDepth = parseInt(depthEl.value, 10);
    const { specs, capped } = prepareSpecsForTree(mapData.specs || []);

    if (!specs.length) {
      graphEl.innerHTML = `<div class="graph-hint">No specs match your search.<br>Pick one from the catalog or search "29.518".</div>`;
      statusEl.textContent = "0 nodes";
      return;
    }

    const { nodes, edges, truncated, nodeCount } = buildGraphData(specs, maxDepth);

    if (network) {
      network.destroy();
      network = null;
    }

    network = new vis.Network(
      graphEl,
      { nodes: new vis.DataSet(nodes), edges: new vis.DataSet(edges) },
      {
        layout: {
          hierarchical: {
            enabled: true,
            direction: "UD",
            sortMethod: "directed",
            levelSeparation: 140,
            nodeSpacing: 160,
            treeSpacing: 140,
            blockShifting: true,
            edgeMinimization: true,
          },
        },
        physics: { enabled: false },
        interaction: {
          hover: true,
          tooltipDelay: 100,
          navigationButtons: true,
          keyboard: true,
          zoomView: true,
        },
        edges: {
          arrows: { to: { enabled: true, scaleFactor: 0.6 } },
          color: { color: "rgba(140,160,180,0.45)", highlight: "#7ee787" },
          smooth: { type: "cubicBezier", forceDirection: "vertical", roundness: 0.5 },
        },
      }
    );

    network.on("click", (params) => {
      if (!params.nodes.length) return;
      const meta = nodeMeta.get(params.nodes[0]);
      if (meta?.type === "root") {
        clearFocus();
        return;
      }
      if (meta?.type === "yaml") {
        showDetail(meta.spec, meta.nf, meta.entry);
        detailPanel.classList.remove("collapsed");
        detailToggle.textContent = "Detail ▼";
      } else if (meta?.type === "spec") {
        selectSpec(meta.data.tsNumber, { focusMap: true });
      } else if (meta?.type === "nf") {
        showNfSummary(meta.spec, meta.nf);
      }
    });

    network.once("afterDrawing", () => network.fit({ animation: { duration: 400 } }));

    let status = `${nodeCount} nodes · ${specs.length} spec${specs.length === 1 ? "" : "s"}`;
    if (focusedSpecTs) status += ` · focused TS ${focusedSpecTs}`;
    if (capped) status += ` · showing first ${MAX_SPECS_DEFAULT} (pick from catalog)`;
    if (truncated) status += " · truncated";
    statusEl.textContent = status;
  } catch (err) {
    graphEl.innerHTML = `<div class="graph-hint">${escapeHtml(err.message)}</div>`;
    statusEl.textContent = "Error";
    console.error(err);
  }
}

function showSpecSummaryFromCatalog(item) {
  detailPanel.classList.remove("collapsed");
  detailToggle.textContent = "Detail ▼";
  const spec = mapSpec(item.tsNumber);
  detailContent.innerHTML = `
    <h2>TS ${escapeHtml(item.tsNumber)}</h2>
    <div class="path-line">${escapeHtml(item.title?.startsWith("(referenced") ? "" : item.title || "")}</div>
    <p style="font-size:0.85rem;color:#aaa">
      ${item.yamlCount} YAML · ${item.nfCount} NF · ${item.referenceCount} reference cite(s)
    </p>
    <div class="detail-actions">
      <a href="/specs?ts=${encodeURIComponent(item.tsNumber)}&view=story">Story in platform →</a>
      <a href="/specs/${encodeURIComponent(item.tsNumber)}">Full story page →</a>
      ${item.url ? `<a href="${escapeHtml(item.url)}" target="_blank" rel="noopener">3GPP archive</a>` : ""}
      ${spec?.nfs?.[0]?.yamls?.[0] ? `<a href="/?yaml=${encodeURIComponent(spec.nfs[0].yamls[0].sourceFile)}">Open in Explorer</a>` : ""}
    </div>
  `;
}

function showSpecSummary(spec) {
  showSpecSummaryFromCatalog(
    catalogEntry(spec.tsNumber) || {
      tsNumber: spec.tsNumber,
      title: spec.title,
      yamlCount: spec.yamlCount,
      nfCount: spec.nfCount,
      referenceCount: 0,
      url: spec.url,
    }
  );
}

function showNfSummary(spec, nf) {
  const block = (spec.nfs || []).find((n) => n.nf === nf);
  detailPanel.classList.remove("collapsed");
  detailToggle.textContent = "Detail ▼";
  detailContent.innerHTML = `
    <h2>${escapeHtml(nf)}</h2>
    <div class="path-line">TS ${escapeHtml(spec.tsNumber)} → ${escapeHtml(nf)}</div>
    <p style="font-size:0.85rem;color:#aaa">${block?.yamlCount || 0} YAML API file(s).</p>
    <div class="detail-actions">
      <a href="/topology?nf=${encodeURIComponent(nf)}">Show in Topology</a>
    </div>
  `;
}

async function showDetail(spec, nf, entry) {
  detailContent.innerHTML = '<p class="placeholder">Loading…</p>';
  try {
    const res = await fetch(`/api/yaml/${entry.sourceFile}`);
    const text = await res.text();
    detailContent.innerHTML = `
      <h2>${escapeHtml(entry.service)}</h2>
      <div class="path-line">TS ${escapeHtml(spec.tsNumber)} → ${escapeHtml(nf)} → ${escapeHtml(entry.sourceFile)}</div>
      <pre>${escapeHtml(text.slice(0, 8000))}${text.length > 8000 ? "\n… truncated …" : ""}</pre>
      <div class="detail-actions">
        <a href="/?yaml=${encodeURIComponent(entry.sourceFile)}">Open in Explorer</a>
        <a href="/specs?ts=${encodeURIComponent(spec.tsNumber)}&view=map">Platform map</a>
        <a href="/api/yaml/${encodeURIComponent(entry.sourceFile)}" target="_blank">Raw YAML</a>
      </div>
    `;
    network?.selectNodes([`yaml:${entry.sourceFile}`]);
  } catch (err) {
    detailContent.innerHTML = `<p class="error">${escapeHtml(err.message)}</p>`;
  }
}

const STITCH_TS = new Set([
  "23.502", "29.513", "23.501", "23.503", "29.501", "29.502", "29.510", "29.514",
]);

function mergePlatformFallback(map, catalog) {
  const mapByTs = Object.fromEntries((map.specs || []).map((s) => [s.tsNumber, s]));
  const catalogSpecs = catalog.specs || [];
  const source = catalogSpecs.length ? catalogSpecs : map.specs || [];

  const items = source.map((entry) => {
    const ts = entry.tsNumber;
    const mapped = mapByTs[ts] || {};
    const nfs = mapped.nfs || [];
    const nfServices = nfs.length
      ? nfs.map((n) => n.nf).filter(Boolean)
      : entry.nfServices || [];

    return {
      tsNumber: ts,
      title: entry.title || mapped.title || "",
      yamlCount: entry.yamlCount ?? mapped.yamlCount ?? 0,
      nfCount: mapped.nfCount ?? nfServices.length,
      nfServices,
      referenceOnly: Boolean(entry.referenceOnly),
      referenceCount: entry.referenceCount || 0,
      url: (entry.urls || [mapped.url || ""])[0],
      hasYaml: Boolean(entry.yamlFiles?.length || mapped.yamlCount),
      hasNarrative: ts === ANCHOR_TS,
      hasPdf: false,
      isStitchSpec: STITCH_TS.has(ts),
      isAnchorStory: ts === ANCHOR_TS,
      platformUrl: `/specs?ts=${ts}`,
      storyUrl: `/specs/${ts}`,
      mapUrl: `/specs?ts=${ts}&view=map`,
    };
  });

  items.sort((a, b) => {
    if (a.isAnchorStory !== b.isAnchorStory) return a.isAnchorStory ? -1 : 1;
    if (a.hasYaml !== b.hasYaml) return a.hasYaml ? -1 : 1;
    return a.tsNumber.localeCompare(b.tsNumber);
  });

  return {
    specs: items,
    map,
    meta: {
      ...catalog.meta,
      ...map.meta,
      totalSpecs: items.length,
      withStory: items.filter((i) => i.hasNarrative).length,
      withPdf: 0,
      stitchCount: items.filter((i) => i.isStitchSpec).length,
      anchor: ANCHOR_TS,
    },
  };
}

async function loadPlatform(refresh = false) {
  statusEl.textContent = "Loading…";
  catalogListEl.innerHTML = '<li class="catalog-placeholder">Loading catalog…</li>';
  try {
    const res = await fetch(`/api/specs/platform?refresh=${refresh}`);
    if (res.ok) {
      platformData = await res.json();
    } else {
      const [mapRes, catRes] = await Promise.all([
        fetch(`/api/specs?refresh=${refresh}`),
        fetch(`/api/specs/catalog?refresh=${refresh}`),
      ]);
      if (!mapRes.ok) throw new Error(`Specs API unavailable (${mapRes.status}). Restart the server.`);
      const map = await mapRes.json();
      const catalog = catRes.ok ? await catRes.json() : { specs: [], meta: {} };
      platformData = mergePlatformFallback(map, catalog);
      if (!res.ok && res.status === 404) {
        console.warn("Platform API missing — using fallback. Restart server: python -m backend.app");
      }
    }

    catalogItems = platformData.specs || [];
    mapData = platformData.map || { specs: [] };
    const m = platformData.meta || {};
    metaEl.textContent = `${m.specCount || m.totalSpecs} specs · ${m.nfCount} NFs · ${m.yamlCount} YAMLs`;
    renderCatalog();
    renderGraph();
  } catch (err) {
    statusEl.textContent = `Failed: ${err.message}`;
    catalogListEl.innerHTML = `<li class="catalog-placeholder">${escapeHtml(err.message)}</li>`;
  }
}

searchEl.addEventListener("input", () => renderGraph());
depthEl.addEventListener("change", () => renderGraph());
fitBtn.addEventListener("click", () => network?.fit({ animation: true }));
refreshBtn.addEventListener("click", () => loadPlatform(true));
clearFocusBtn.addEventListener("click", (event) => {
  event.stopPropagation();
  clearFocus();
});
catalogSearchEl.addEventListener("input", () => renderCatalog());
catalogFilterEl.addEventListener("change", () => renderCatalog());

platformTabs.forEach((tab) => {
  tab.addEventListener("click", () => setView(tab.dataset.view));
});

detailToggle.addEventListener("click", () => {
  detailPanel.classList.toggle("collapsed");
  detailToggle.textContent = detailPanel.classList.contains("collapsed") ? "Detail ▲" : "Detail ▼";
});

window.addEventListener("load", () => {
  const params = new URLSearchParams(window.location.search);
  const tsParam = normalizeTs(params.get("ts") || params.get("spec"));
  const viewParam = params.get("view");
  nfFilter = params.get("nf");
  if (nfFilter) catalogSearchEl.placeholder = `NF filter: ${nfFilter}…`;
  if (viewParam === "story") activeView = "story";

  loadPlatform(false).then(() => {
    if (tsParam) {
      focusedSpecTs = tsParam;
      selectedTs = tsParam;
      updateFocusUI();
      updateContextBar();
      renderCatalog();
      renderGraph();
      const item = catalogEntry(tsParam);
      if (item) showSpecSummaryFromCatalog(item);
    }
    setView(activeView);

    const yaml = params.get("yaml");
    if (!yaml) return;
    for (const spec of mapData.specs || []) {
      for (const nfBlock of spec.nfs || []) {
        const entry = (nfBlock.yamls || []).find((y) => y.sourceFile === yaml);
        if (entry) {
          selectSpec(spec.tsNumber, { focusMap: true, skipView: true });
          searchEl.value = yaml.replace(".yaml", "");
          depthEl.value = "3";
          renderGraph();
          showDetail(spec, nfBlock.nf, entry);
          detailPanel.classList.remove("collapsed");
          return;
        }
      }
    }
  });
});
