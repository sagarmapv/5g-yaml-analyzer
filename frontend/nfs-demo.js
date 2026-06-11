/** Static demo — NF catalog browser (GitHub Pages). */

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

const TIER_LABELS = {
  access: "Access",
  core_control: "Core control",
  user_plane: "User plane",
  data: "Data",
  charging: "Charging",
  exposure: "Exposure",
  analytics: "Analytics",
  security_roaming: "Security & roaming",
  extended: "Extended",
};

function renderNfCard(nf) {
  const ifaces = (nf.interfaces || []).slice(0, 4).join(", ");
  const corpus = nf.inCorpus
    ? `<span style="color:#9fd4b0">In YAML corpus (${nf.serviceCount || 0} services)</span>`
    : `<span style="color:var(--text-muted)">Catalog only</span>`;

  return `
    <article class="nf-card">
      <h4>${escapeHtml(nf.id)}</h4>
      <div class="tier">${escapeHtml(TIER_LABELS[nf.tier] || nf.tier || "")}</div>
      <p>${escapeHtml(nf.role || nf.description || "")}</p>
      ${ifaces ? `<p style="font-size:0.8rem;margin-top:6px;color:#889099">Interfaces: ${escapeHtml(ifaces)}</p>` : ""}
      <p style="font-size:0.75rem;margin-top:8px">${corpus}</p>
    </article>
  `;
}

function groupByTier(nfs) {
  const groups = new Map();
  for (const nf of nfs) {
    const tier = nf.tier || "other";
    if (!groups.has(tier)) groups.set(tier, []);
    groups.get(tier).push(nf);
  }
  return [...groups.entries()].sort((a, b) => a[0].localeCompare(b[0]));
}

async function initNfsDemo() {
  const host = document.getElementById("nfs-host");
  if (!host) return;

  host.innerHTML = '<p class="loading-inline">Loading NF catalog…</p>';

  try {
    const res = await fetch("/api/nfs?summary=true");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const nfs = (data.networkFunctions || []).filter((nf) => nf.e2eDefault !== false);
    const groups = groupByTier(nfs);

    host.innerHTML = groups
      .map(
        ([tier, items]) => `
        <section style="margin-bottom:28px">
          <h2 style="font-size:0.95rem;color:var(--text-muted);margin:0 0 12px">${escapeHtml(TIER_LABELS[tier] || tier)} (${items.length})</h2>
          <div class="nf-grid">${items.map(renderNfCard).join("")}</div>
        </section>
      `,
      )
      .join("");
  } catch (err) {
    host.innerHTML = `<p class="loading-inline">Failed to load: ${escapeHtml(err.message)}</p>`;
    console.error(err);
  }
}

window.addEventListener("load", initNfsDemo);
