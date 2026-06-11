const { escapeHtml } = window.FlowRenderer;
const { renderLadderPage, renderInlineRequestDetail, renderProceduralInline } = window.LadderRenderer;

let ladderData = null;
let selectedNfs = new Set();
let expandedStep = null;
const opCache = new Map();

function storyIdFromUrl() {
  return new URLSearchParams(window.location.search).get("id") || "pdu-session-sm-policy";
}

function knowledgeUrlForStory(id) {
  if (document.querySelector('meta[name="demo-mode"]')) {
    return `./master-story.html?id=${encodeURIComponent(id)}`;
  }
  return `/stories?id=${id}`;
}

function nfsFromUrl() {
  const raw = new URLSearchParams(window.location.search).get("nfs") || "";
  return raw
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

function syncUrl() {
  const url = new URL(window.location.href);
  if (selectedNfs.size) {
    url.searchParams.set("nfs", [...selectedNfs].join(","));
  } else {
    url.searchParams.delete("nfs");
  }
  window.history.replaceState({}, "", url);
}

function render() {
  const host = document.getElementById("ladder-host");
  if (!host || !ladderData) return;
  host.innerHTML = renderLadderPage(ladderData, {
    selectedNfs: [...selectedNfs],
    expandedStep,
  });
  if (expandedStep != null) {
    fillExpandedDetail(expandedStep);
  }
}

async function fillExpandedDetail(stepOrder) {
  const slot = document.querySelector(`[data-detail-slot="${stepOrder}"]`);
  if (!slot || !ladderData) return;
  const msg = ladderData.ladderMessages.find((m) => m.stepOrder === stepOrder);
  if (!msg) return;

  if (!msg.operationId || !msg.hasMessageDetail) {
    slot.innerHTML = renderProceduralInline(msg);
    return;
  }

  slot.innerHTML = "<p class=\"loading\">Loading request detail…</p>";
  try {
    let detail = opCache.get(msg.operationId);
    if (!detail) {
      const res = await fetch(
        `/api/operations/${encodeURIComponent(msg.operationId)}?view=request`
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      detail = await res.json();
      opCache.set(msg.operationId, detail);
    }
    slot.innerHTML = renderInlineRequestDetail(detail);
  } catch (err) {
    slot.innerHTML = `<p class="loading">Failed to load: ${escapeHtml(err.message)}</p>`;
  }
}

function bindHandlers() {
  const host = document.getElementById("ladder-host");
  if (!host) return;

  host.addEventListener("click", (e) => {
    const clearBtn = e.target.closest("[data-ladder-clear]");
    if (clearBtn) {
      selectedNfs.clear();
      expandedStep = null;
      syncUrl();
      render();
      return;
    }

    const actorBtn = e.target.closest("[data-ladder-actor]");
    if (actorBtn) {
      const actor = actorBtn.getAttribute("data-ladder-actor");
      if (selectedNfs.has(actor)) selectedNfs.delete(actor);
      else selectedNfs.add(actor);
      syncUrl();
      render();
      return;
    }

    const msgBtn = e.target.closest("[data-ladder-msg]");
    if (!msgBtn) return;

    const stepOrder = Number(msgBtn.getAttribute("data-step-order"));
    expandedStep = expandedStep === stepOrder ? null : stepOrder;
    render();
  });
}

async function init() {
  const id = storyIdFromUrl();
  selectedNfs = new Set(nfsFromUrl());

  try {
    const res = await fetch(`/api/stories/${encodeURIComponent(id)}/ladder`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    ladderData = await res.json();
    document.title = `${ladderData.title} — Signaling Ladder`;
    document.getElementById("ladder-title").textContent = ladderData.title;
    document.getElementById("ladder-knowledge-link").href = knowledgeUrlForStory(id);
    render();
    bindHandlers();
  } catch (err) {
    document.getElementById("ladder-host").innerHTML = `<p class="loading">Failed to load ladder: ${escapeHtml(err.message)}</p>`;
  }
}

init();
