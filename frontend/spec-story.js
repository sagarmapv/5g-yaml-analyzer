function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text ?? "";
  return div.innerHTML;
}

function tsFromPath() {
  const parts = window.location.pathname.split("/").filter(Boolean);
  const idx = parts.indexOf("specs");
  if (idx >= 0 && parts[idx + 1]) return decodeURIComponent(parts[idx + 1]);
  return null;
}

function isEmbedMode() {
  return new URLSearchParams(window.location.search).get("embed") === "1";
}

function isDebugMode() {
  return new URLSearchParams(window.location.search).get("debug") === "1";
}

function wrapTable(html) {
  return `<div class="table-scroll">${html}</div>`;
}

function badge(type, label) {
  return `<span class="badge ${type}">${escapeHtml(label)}</span>`;
}

function renderEntryPoints(entries) {
  if (!entries?.length) return "<p>No entry points defined.</p>";
  const rows = entries
    .map((e) => {
      const typeBadge =
        e.type === "sbi" ? badge("sbi", "SBI") : e.type === "procedure" ? badge("proc", "Procedure") : badge("neighbor", e.type);
      const detail =
        e.type === "sbi"
          ? `<code>${escapeHtml(e.method || "")} ${escapeHtml(e.path || "")}</code><br>${escapeHtml(e.operationId || e.name || "")}`
          : `${escapeHtml(e.name || "")}${e.clause ? ` <em>(§${escapeHtml(e.clause)})</em>` : ""}`;
      return `<tr>
        <td>${typeBadge}</td>
        <td>${detail}</td>
        <td>${escapeHtml(e.consumer || e.direction || "")}</td>
        <td>${escapeHtml(e.description || e.trigger || "")}${e.refSpec ? ` <em>(TS ${escapeHtml(e.refSpec)})</em>` : ""}</td>
      </tr>`;
    })
    .join("");
  return wrapTable(
    `<table class="story-table"><thead><tr><th>Type</th><th>Endpoint / name</th><th>Actor</th><th>Description</th></tr></thead><tbody>${rows}</tbody></table>`
  );
}

function renderRelatedStory(related) {
  if (!related?.length) return "";
  const links = related
    .map(
      (r) =>
        `<li><a href="/specs/${encodeURIComponent(r.ts)}">TS ${escapeHtml(r.ts)}</a> — ${escapeHtml(r.role || "")}</li>`
    )
    .join("");
  return `<div class="related-story"><h3 class="related-story-title">Related in the 512 story</h3><ul class="related-story-list">${links}</ul></div>`;
}

function readinessChip(label, on) {
  return `<span class="ready-chip ${on ? "on" : "off"}">${escapeHtml(label)}</span>`;
}

function renderElementReadinessItem(item) {
  if (!item) return "";
  const chips = [
    readinessChip("spec", item.hasSpec),
    readinessChip("yaml", item.hasYaml),
    readinessChip("story", item.hasStory),
  ].join("");
  const badgeLabel = item.ready ? "ready" : item.state === "partial" ? "partial" : "gap";
  const badgeType = item.ready ? "in-spec" : item.state === "partial" ? "sbi" : "neighbor";
  const specLink = item.primarySpec
    ? ` <a class="element-spec-link" href="${escapeHtml(item.platformUrl || `/specs?ts=${item.primarySpec}`)}" target="_blank" rel="noopener">TS ${escapeHtml(item.primarySpec)}</a>`
    : "";
  return `${badge(badgeType, badgeLabel)}${specLink}<div class="ready-chips">${chips}</div>`;
}

function renderElements(elements, readiness, nfGaps) {
  if (!elements?.length) return "<p>No elements defined.</p>";
  const debug = isDebugMode();
  const legend = window.FlowRenderer?.renderJourneyLegend
    ? window.FlowRenderer.renderJourneyLegend()
    : "";
  const gapsTable =
    debug && nfGaps?.items?.length && window.FlowRenderer?.renderNfGapsTable
      ? window.FlowRenderer.renderNfGapsTable(nfGaps, { compact: true })
      : "";

  return `${legend}${gapsTable}<div class="element-grid">${elements
    .map((el) => {
      const journeyClass = el.inSpec ? "journey-focus" : "journey-related";
      const primary = el.primarySpec || "";
      const specLink = primary
        ? `<a class="element-spec-link" href="/specs/${encodeURIComponent(primary)}" target="_blank" rel="noopener">TS ${escapeHtml(primary)}</a>`
        : "";
      const readinessItem = readiness?.items?.find((r) => r.nf === el.nf);
      const readinessHtml = debug && readinessItem ? renderElementReadinessItem(readinessItem) : "";
      return `<div class="element-card ${journeyClass}">
      <h3>${escapeHtml(el.nf)}</h3>
      ${specLink}
      ${readinessHtml}
      <p>${escapeHtml(el.role)}</p>
    </div>`;
    })
    .join("")}</div>`;
}

function renderInteractions(interactions, operations) {
  if (!interactions?.length && !operations?.length) return "<p>No interactions defined.</p>";
  const rows = (interactions || [])
    .map(
      (ix) => `<tr>
      <td>${escapeHtml(ix.from)} → ${escapeHtml(ix.to)}</td>
      <td><code>${escapeHtml(ix.via || "")}</code></td>
      <td>${escapeHtml(ix.payload || ix.response || ix.description || "")}${ix.refSpec ? ` <em>(TS ${escapeHtml(ix.refSpec)})</em>` : ""}</td>
    </tr>`
    )
    .join("");
  const opRows = (operations || [])
    .map(
      (op) => `<tr>
      <td>${escapeHtml(op.nf)} → PCF</td>
      <td><code>${escapeHtml(op.method)} ${escapeHtml(op.path)}</code></td>
      <td><a href="/?yaml=${encodeURIComponent(op.sourceFile)}">${escapeHtml(op.operationId)}</a> — ${escapeHtml(op.summary)}</td>
    </tr>`
    )
    .join("");
  return wrapTable(
    `<table class="story-table"><thead><tr><th>Link</th><th>Via</th><th>Detail</th></tr></thead><tbody>${rows}${opRows}</tbody></table>`
  );
}

function nfMapFromReadiness(readiness) {
  const map = {};
  for (const item of readiness?.items || []) {
    map[item.nf] = { storyUrl: item.storyUrl };
  }
  return map;
}

function renderStoryGaps(gaps) {
  if (!gaps?.items?.length) return "";
  const meta = gaps.meta || {};
  const rows = gaps.items
    .map((item) => {
      const pdf = item.hasPdf ? badge("in-spec", item.pdfVersion || "PDF") : badge("neighbor", "no PDF");
      const yaml = item.hasYaml ? badge("sbi", "YAML") : badge("neighbor", "ref only");
      const clauses = item.hasClauses ? `${item.clauseCount} clauses` : "—";
      return `<tr>
        <td><span class="gap-priority">${escapeHtml(item.priority || "")}</span> <a href="${escapeHtml(item.storyUrl)}"><strong>TS ${escapeHtml(item.tsNumber)}</strong></a></td>
        <td>${escapeHtml(item.role || "")}</td>
        <td>${pdf} ${yaml}</td>
        <td>${escapeHtml(clauses)}</td>
        <td>${item.ready ? badge("in-spec", "stitched") : badge("neighbor", "gap")}</td>
      </tr>`;
    })
    .join("");
  const headline = meta.complete
    ? "All supporting specs are available — the 512 story is fully stitched."
    : `${meta.ready} of ${meta.total} supporting specs ready — import remaining PDFs to close knowledge gaps.`;
  return `<p class="gaps-headline">${escapeHtml(headline)}</p>${wrapTable(
    `<table class="story-table gaps-table"><thead><tr><th>Spec</th><th>Role in 512 story</th><th>Sources</th><th>PDF index</th><th>Status</th></tr></thead><tbody>${rows}</tbody></table>`
  )}`;
}

function renderSpecReadiness(r) {
  if (!r) return "";
  const chips = [
    readinessChip("spec", r.hasSpec),
    readinessChip("yaml", r.hasYaml),
    readinessChip("story", r.hasStory),
  ].join("");
  const label = r.ready ? "ready" : r.state === "partial" ? "partial" : "gap";
  const badgeType = r.ready ? "in-spec" : r.state === "partial" ? "sbi" : "neighbor";
  return `<div class="spec-readiness spec-readiness-${r.state}">${badge(badgeType, label)} <span class="spec-readiness-label">TS ${escapeHtml(r.tsNumber)} readiness</span><div class="ready-chips">${chips}</div></div>`;
}

function renderOperations(operations) {
  if (!operations?.length) return "<p>No operations in corpus.</p>";
  const rows = operations
    .map(
      (op) => `<tr>
      <td><code>${escapeHtml(op.method)}</code></td>
      <td><code>${escapeHtml(op.path)}</code></td>
      <td><a href="/?yaml=${encodeURIComponent(op.sourceFile)}">${escapeHtml(op.operationId)}</a></td>
      <td>${escapeHtml(op.summary)}</td>
    </tr>`
    )
    .join("");
  return wrapTable(
    `<table class="story-table"><thead><tr><th>Method</th><th>Path</th><th>Operation</th><th>Summary</th></tr></thead><tbody>${rows}</tbody></table>`
  );
}

function renderReferencedBy(files) {
  if (!files?.length) return "<p>No cross-references in corpus.</p>";
  return `<ul class="ref-list">${files
    .map((f) => `<li><a href="/?yaml=${encodeURIComponent(f)}">${escapeHtml(f)}</a></li>`)
    .join("")}</ul>`;
}

function renderClauses(clauses, highlightNums, ts) {
  if (!clauses?.clauses?.length) {
    const cmd = ts ? `python scripts/extract_spec_pdf.py ${ts}` : "python scripts/extract_spec_pdf.py <ts>";
    return `<p>PDF clauses not extracted yet. Run <code>${escapeHtml(cmd)}</code>.</p>`;
  }
  const all = clauses.clauses;
  const highlights =
    highlightNums?.length > 0
      ? all.filter((c) => highlightNums.some((h) => c.number === h || c.number.startsWith(`${h}.`)))
      : [];
  const highlightBlock = highlights.length
    ? `<div class="clause-highlights"><h3 class="clause-highlights-title">Key clauses for this story</h3><ul class="clause-list">${highlights
        .map((c) => `<li><strong>${escapeHtml(c.number)}</strong> ${escapeHtml(c.title)}</li>`)
        .join("")}</ul></div>`
    : "";
  const items = all.map((c) => `<li><strong>${escapeHtml(c.number)}</strong> ${escapeHtml(c.title)}</li>`).join("");
  return `${highlightBlock}<p class="meta-chip">${escapeHtml(clauses.clauseCount || all.length)} clauses from ${escapeHtml(clauses.sourceFile || "PDF")} ${escapeHtml(clauses.version || "")}</p><div class="clause-scroll"><ul class="clause-list">${items}</ul></div>`;
}

function updatePlatformLinks(ts) {
  const platform = document.getElementById("bc-platform");
  if (platform) platform.href = `/specs?ts=${encodeURIComponent(ts)}&view=story`;
}

function initTocSpy() {
  const tocLinks = document.querySelectorAll(".toc-link");
  const scrollRoot = document.querySelector(".story-scroll");
  if (!tocLinks.length || !scrollRoot) return;

  const sectionTop = (el) => {
    const rootRect = scrollRoot.getBoundingClientRect();
    const elRect = el.getBoundingClientRect();
    return elRect.top - rootRect.top + scrollRoot.scrollTop;
  };

  tocLinks.forEach((link) => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      const id = link.getAttribute("href")?.slice(1);
      const target = id ? document.getElementById(id) : null;
      if (target) {
        scrollRoot.scrollTo({ top: sectionTop(target) - 8, behavior: "smooth" });
      }
    });
  });

  const sections = [...tocLinks]
    .map((link) => {
      const id = link.getAttribute("href")?.slice(1);
      const el = id ? document.getElementById(id) : null;
      return el ? { link, el } : null;
    })
    .filter(Boolean);

  const observer = new IntersectionObserver(
    (entries) => {
      const visible = entries.filter((e) => e.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio);
      if (!visible.length) return;
      const id = visible[0].target.id;
      tocLinks.forEach((l) => l.classList.toggle("active", l.getAttribute("href") === `#${id}`));
    },
    { root: scrollRoot, rootMargin: "-10% 0px -55% 0px", threshold: [0, 0.25, 0.5] }
  );

  sections.forEach((s) => observer.observe(s.el));
}

function initTopologyGraph(topology) {
  const el = document.getElementById("interaction-graph");
  if (!el || typeof vis === "undefined" || !topology?.nodes?.length) return;

  const focusNf = topology.focusNf || "PCF";
  const nodes = topology.nodes.map((n) => ({
    id: n.id,
    label: n.label,
    color:
      n.id === focusNf
        ? { background: "#f0c040", border: "#c9a020" }
        : { background: "#4a9eff", border: "#2a7fd4" },
    font: { color: n.id === focusNf ? "#1a1d23" : "#fff", size: 14 },
    shape: "box",
  }));
  const edges = (topology.edges || []).map((e) => ({
    from: e.from,
    to: e.to,
    arrows: "to",
    title: (e.examples || []).join(", "),
  }));

  const network = new vis.Network(el, { nodes: new vis.DataSet(nodes), edges: new vis.DataSet(edges) }, {
    physics: { enabled: true, stabilization: { iterations: 120 } },
    interaction: { hover: true },
  });
  network.once("stabilizationIterationsDone", () => network.fit({ animation: true }));
}

function renderStory(data) {
  const spec = data.spec || {};
  const narrative = data.narrative || {};
  const ts = spec.tsNumber || tsFromPath();

  updatePlatformLinks(ts);

  document.title = `TS ${ts} — Spec Story`;
  document.getElementById("bc-ts").textContent = `TS ${ts}`;
  const displayTitle = narrative.title || spec.title || "Spec Story";
  const cleanTitle = displayTitle.startsWith("(referenced") ? narrative.tagline || "Spec Story" : displayTitle;
  document.getElementById("story-title").textContent = `TS ${ts} — ${cleanTitle}`;
  document.getElementById("story-tagline").textContent = narrative.tagline || narrative.summary || "";

  const banner = document.getElementById("version-banner");
  if (data.versionBanner) {
    banner.textContent = data.versionBanner;
    banner.classList.remove("hidden");
  } else {
    banner.classList.add("hidden");
  }

  const isStitchPage = Boolean(narrative.stitchAnchor);
  const isAnchor = ts === "29.512";
  const e2eFlow = data.enrichedE2eFlow || narrative.e2eFlow;
  const relatedLinks = narrative.relatedStory?.length
    ? narrative.relatedStory
    : (narrative.relatedSpecs || []).map((r) => ({ ts: r.ts, role: r.role }));
  const main = document.getElementById("story-main");

  const section = (id, title, desc, html, show = true) =>
    show && html
      ? `<section class="story-section" id="${id}"><h2>${title}</h2>${desc ? `<p>${desc}</p>` : ""}${html}</section>`
      : "";

  main.innerHTML = `
    <div class="meta-row">
      <span class="meta-chip">YAML <strong>${escapeHtml(data.versions?.yaml || "—")}</strong></span>
      <span class="meta-chip">PDF <strong>${escapeHtml(data.versions?.pdf || "—")}</strong></span>
      ${isAnchor ? `<span class="meta-chip">Stitch <strong>${data.storyGaps?.meta?.ready || 0}/${data.storyGaps?.meta?.total || 0}</strong> specs</span>` : ""}
      ${!isStitchPage && !isAnchor ? `<span class="meta-chip">Referenced by <strong>${data.referencedBy?.length || 0}</strong> YAMLs</span>` : ""}
      ${isAnchor || isStitchPage ? `<a class="master-journey-link" href="/stories">Master journey →</a>` : ""}
    </div>

    ${data.specReadiness && !isAnchor && isDebugMode() ? renderSpecReadiness(data.specReadiness) : ""}

    ${section(
      "sec-overview",
      isStitchPage || isAnchor ? (isAnchor ? "Overview" : "Supporting spec") : "Overview",
      "",
      `<p>${escapeHtml(narrative.summary || narrative.tagline || "")}</p>${narrative.whyItMatters ? `<p>${escapeHtml(narrative.whyItMatters)}</p>` : ""}${narrative.defines?.length ? `<ul>${narrative.defines.map((d) => `<li>${escapeHtml(d)}</li>`).join("")}</ul>` : ""}${narrative.primaryNf ? `<p class="meta-chip">NF: <strong>${escapeHtml(narrative.primaryNf)}</strong></p>` : ""}${renderRelatedStory(relatedLinks)}${isStitchPage ? `<p><a href="/stories">← Master story</a> · <a href="/specs?ts=29.512&view=story">TS 29.512 in platform</a></p>` : ""}${isAnchor ? `<p><a class="master-journey-link prominent" href="/stories">Open master journey</a></p>` : ""}`
    )}

    ${section(
      "sec-entry",
      "1. Entry points",
      isAnchor
        ? "Where session management policy control starts — SBI APIs and procedure triggers."
        : "How this spec enters the 512 story — procedures and SBI entry points.",
      renderEntryPoints(narrative.entryPoints),
      narrative.entryPoints?.length
    )}

    ${section(
      "sec-elements",
      "2. Major elements",
      isAnchor ? "Network functions involved in the 29.512 story." : "Network functions in this spec's story.",
      renderElements(narrative.elements, data.elementReadiness, isAnchor ? data.nfGaps : null),
      narrative.elements?.length
    )}

    ${section(
      "sec-interactions",
      "3. How elements interact",
      "Service relationships and operations relevant to this story.",
      `${renderInteractions(narrative.interactions, isAnchor ? data.operations : [])}<div id="interaction-graph"></div>`,
      narrative.interactions?.length || (isAnchor && data.operations?.length)
    )}

    ${section(
      "sec-gaps",
      "Story stitch — no more gaps",
      "Supporting specs that connect 512 to the live network. PDF and YAML sources stitched into the call flow below.",
      renderStoryGaps(data.storyGaps),
      isAnchor && data.storyGaps?.items?.length
    )}

    ${section(
      "sec-flow",
      "4. End-to-end call flow",
      isAnchor
        ? "PDU session establishment — green marker = steps defined in TS 29.512."
        : "Call flow for this spec within the 512 story — green marker = steps owned by this spec.",
      window.FlowRenderer.renderFlow(e2eFlow, ts, { nfMap: nfMapFromReadiness(data.elementReadiness) }),
      e2eFlow?.steps?.length
    )}

    ${section(
      "sec-operations",
      "API operations (YAML corpus)",
      "",
      renderOperations(data.operations),
      data.operations?.length
    )}

    ${section(
      "sec-refs",
      "Who references 29.512",
      "",
      renderReferencedBy(data.referencedBy),
      isAnchor && data.referencedBy?.length
    )}

    ${section(
      "sec-clauses",
      "PDF clause index",
      "",
      renderClauses(data.pdfClauses, data.highlightClauses || narrative.highlightClauses, ts),
      data.pdfClauses?.clauses?.length
    )}

    <div class="story-links">
      ${spec.url ? `<a href="${escapeHtml(spec.url)}" target="_blank" rel="noopener">3GPP archive</a>` : ""}
      <a href="/specs?ts=${encodeURIComponent(ts)}&view=map">Specs platform (map)</a>
      <a href="/specs?ts=${encodeURIComponent(ts)}&view=story">Specs platform (story)</a>
      ${!isAnchor ? `<a href="/specs?ts=29.512&view=story">TS 29.512 anchor</a>` : ""}
      <a href="/topology">NF Topology</a>
      ${data.yamls?.[0] ? `<a href="/?yaml=${encodeURIComponent(data.yamls[0].sourceFile)}">Open in Explorer</a>` : ""}
    </div>
  `;

  document.querySelectorAll(".toc-link").forEach((link) => {
    const id = link.getAttribute("href")?.slice(1);
    link.style.display = id && document.getElementById(id) ? "" : "none";
  });

  if (data.topology?.nodes?.length && (isAnchor || narrative.interactions?.length)) {
    initTopologyGraph({ ...data.topology, focusNf: narrative.primaryNf || "PCF" });
  }
  initTocSpy();
}

async function elementReadinessFromPlatform(elements) {
  const res = await fetch("/api/specs/platform");
  if (!res.ok) return null;
  const platform = await res.json();
  const byTs = Object.fromEntries((platform.specs || []).map((s) => [s.tsNumber, s]));
  const items = elements.map((el) => {
    const primarySpec = el.primarySpec || "29.512";
    const ps = byTs[primarySpec] || {};
    const nfListed = (ps.nfServices || []).includes(el.nf);
    const hasSpec = Boolean(ps.hasPdf);
    const hasYaml = nfListed ? Boolean(ps.hasYaml) : Boolean(ps.hasYaml);
    const hasStory = Boolean(ps.hasNarrative);
    const ready = hasSpec && hasYaml && hasStory;
    return {
      nf: el.nf,
      primarySpec,
      hasSpec,
      hasYaml,
      hasStory,
      ready,
      state: ready ? "ready" : hasSpec || hasYaml || hasStory ? "partial" : "gap",
      platformUrl: `/specs?ts=${encodeURIComponent(primarySpec)}`,
    };
  });
  const ready = items.filter((i) => i.ready).length;
  return { items, meta: { total: items.length, ready, complete: ready === items.length } };
}

async function ensureElementReadiness(data, ts) {
  if (data.elementReadiness?.items?.length) return data.elementReadiness;
  const elements = data.narrative?.elements;
  if (!elements?.length) return null;

  try {
    const res = await fetch(`/api/specs/${encodeURIComponent(ts)}/element-readiness`);
    if (res.ok) return res.json();
  } catch {
    /* try platform fallback */
  }

  return elementReadinessFromPlatform(elements);
}

async function loadStory() {
  if (isEmbedMode()) {
    document.body.classList.add("embed-mode");
  }

  const ts = tsFromPath();
  if (!ts) {
    document.getElementById("story-main").innerHTML = '<p class="error">No spec number in URL.</p>';
    return;
  }
  try {
    const res = await fetch(`/api/specs/${encodeURIComponent(ts)}/detail`);
    if (!res.ok) throw new Error(res.status === 404 ? "Spec not found" : res.statusText);
    const data = await res.json();
    data.elementReadiness = await ensureElementReadiness(data, ts);
    renderStory(data);
  } catch (err) {
    document.getElementById("story-main").innerHTML = `<p class="error">${escapeHtml(err.message)}</p>`;
  }
}

window.addEventListener("load", loadStory);
