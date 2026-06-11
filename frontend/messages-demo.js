/** Static demo — journey operation envelopes (GitHub Pages). */

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function methodClass(method) {
  return (method || "GET").toLowerCase();
}

async function loadManifest() {
  const base = document.querySelector('meta[name="demo-base"]')?.content || "./demo/data";
  const res = await fetch(`${base}/messages-manifest.json`);
  if (!res.ok) throw new Error(`manifest ${res.status}`);
  return res.json();
}

async function loadOperation(id) {
  const res = await fetch(`/api/operations/${encodeURIComponent(id)}?view=request`);
  if (!res.ok) throw new Error(`${id}: HTTP ${res.status}`);
  return res.json();
}

function renderOperationCard(detail) {
  const env = detail.envelope || {};
  const headers = env.headers || detail.requestHeaders || [];
  const body = env.body ?? detail.request?.example ?? detail.request;
  const payload = {
    headers: headers,
    body: body,
  };
  const method = detail.method || env.method || "—";
  const path = detail.path || env.path || detail.operationId || "";

  return `
    <details class="msg-card" open>
      <summary>
        <span class="msg-method ${methodClass(method)}">${escapeHtml(method)}</span>
        <span class="msg-path">${escapeHtml(path)}</span>
        <span style="color:var(--text-muted);font-size:0.85rem">${escapeHtml(detail.summary || detail.operationId || "")}</span>
      </summary>
      <div class="msg-body">
        <pre>${escapeHtml(JSON.stringify(payload, null, 2))}</pre>
      </div>
    </details>
  `;
}

async function initMessagesDemo() {
  const host = document.getElementById("messages-host");
  if (!host) return;

  try {
    const manifest = await loadManifest();
    const ops = manifest.operations || [];
    host.innerHTML = '<p class="loading-inline">Loading message envelopes…</p>';

    const details = await Promise.all(ops.map((op) => loadOperation(op.id)));
    host.innerHTML = `<div class="msg-list">${details.map(renderOperationCard).join("")}</div>`;
  } catch (err) {
    host.innerHTML = `<p class="loading-inline">Failed to load: ${escapeHtml(err.message)}</p>`;
    console.error(err);
  }
}

window.addEventListener("load", initMessagesDemo);
