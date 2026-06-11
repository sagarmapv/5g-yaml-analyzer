const graphEl = document.getElementById("nf-graph");
const statusEl = document.getElementById("graph-status");
const coreOnlyEl = document.getElementById("core-only");
const minWeightEl = document.getElementById("min-weight");
const minWeightValueEl = document.getElementById("min-weight-value");
const refreshBtn = document.getElementById("refresh-graph");
const edgeDetailsEl = document.getElementById("edge-details");
const edgeSummaryEl = document.getElementById("edge-summary");
const edgeExamplesEl = document.getElementById("edge-examples");
const nodeDetailsEl = document.getElementById("node-details");
const nodeSummaryEl = document.getElementById("node-summary");
const nodeSpecsLinkEl = document.getElementById("node-specs-link");

let network = null;
const edgeMeta = new Map();

const CORE_COLOR = "#4a9eff";
const EXTENDED_COLOR = "#f0c040";
const PROXY_COLOR = "#c678dd";
const PROXY_NFS = new Set(["SCP", "SEPP"]);
const EDGE_COLOR = "rgba(160, 180, 200, 0.55)";
const HIGHLIGHT_COLOR = "#7ee787";

function nfColor(node) {
  if (PROXY_NFS.has(node.id)) return PROXY_COLOR;
  return node.isCore ? CORE_COLOR : EXTENDED_COLOR;
}

function nfShape(node) {
  return PROXY_NFS.has(node.id) ? "diamond" : "dot";
}

function ensureVisLoaded() {
  if (typeof vis === "undefined" || !vis.Network || !vis.DataSet) {
    throw new Error("Graph library failed to load. Hard-refresh the page (Ctrl+F5).");
  }
}

function toVisData(topology) {
  ensureVisLoaded();
  edgeMeta.clear();

  if (!topology.nodes.length) {
    return {
      nodes: new vis.DataSet([]),
      edges: new vis.DataSet([]),
    };
  }

  const weights = topology.edges.map((e) => e.weight);
  const maxWeight = Math.max(1, ...weights);

  const nodes = new vis.DataSet(
    topology.nodes.map((node) => ({
      id: node.id,
      label: `${node.label}\n(${node.serviceCount} svc)`,
      title: `${node.label}: ${node.serviceCount} services`,
      color: {
        background: nfColor(node),
        border: "#2a3440",
        highlight: { background: HIGHLIGHT_COLOR, border: "#ffffff" },
      },
      font: { color: "#ffffff", size: 14 },
      shape: nfShape(node),
      size: 18 + Math.min(node.serviceCount, 20),
    }))
  );

  const edges = new vis.DataSet(
    topology.edges.map((edge, index) => {
      const edgeId = `e${index}`;
      edgeMeta.set(edgeId, edge);
      return {
        id: edgeId,
        from: edge.from,
        to: edge.to,
        arrows: "to",
        width: 1 + (edge.weight / maxWeight) * 5,
        label: String(edge.weight),
        font: { align: "middle", size: 10, color: "#aab4be", strokeWidth: 0 },
        color: { color: EDGE_COLOR, highlight: HIGHLIGHT_COLOR },
        smooth: { type: "continuous" },
      };
    })
  );

  return { nodes, edges };
}

function showEmptyState(message) {
  graphEl.innerHTML = `<div class="graph-empty">${message}</div>`;
}

function renderGraph(topology) {
  try {
    ensureVisLoaded();
    graphEl.innerHTML = "";

    if (!topology.nodes.length) {
      showEmptyState("No NF links match the current filters. Lower min link strength or disable core-only.");
      statusEl.textContent = "0 NFs · 0 links";
      return;
    }

    const { nodes, edges } = toVisData(topology);

    const options = {
      physics: {
        enabled: true,
        solver: "forceAtlas2Based",
        forceAtlas2Based: {
          gravitationalConstant: -50,
          centralGravity: 0.015,
          springLength: 160,
          springConstant: 0.09,
          avoidOverlap: 0.5,
        },
        stabilization: { iterations: 200, updateInterval: 25 },
      },
      interaction: {
        hover: true,
        tooltipDelay: 120,
        navigationButtons: true,
        keyboard: true,
      },
      layout: {
        improvedLayout: true,
      },
    };

    if (network) {
      network.destroy();
      network = null;
    }

    network = new vis.Network(graphEl, { nodes, edges }, options);

    network.once("stabilizationIterationsDone", () => {
      network.setOptions({ physics: { enabled: false } });
    });

    network.on("selectEdge", (params) => {
      if (!params.edges.length) return;
      const edge = edgeMeta.get(params.edges[0]);
      if (edge) showEdgeDetails(edge);
    });

    network.on("click", (params) => {
      if (params.nodes.length) {
        showNodeDetails(params.nodes[0], topology);
        return;
      }
      if (!params.edges.length) {
        hideEdgeDetails();
        hideNodeDetails();
      }
    });

    statusEl.textContent = `${topology.meta.nodeCount} NFs · ${topology.meta.edgeCount} links`;
  } catch (err) {
    showEmptyState(err.message);
    statusEl.textContent = `Error: ${err.message}`;
    console.error(err);
  }
}

function showEdgeDetails(edge) {
  hideNodeDetails();
  edgeDetailsEl.classList.remove("hidden");
  edgeSummaryEl.textContent = `${edge.from} → ${edge.to} (strength ${edge.weight}, ${edge.signals.join(", ")})`;
  edgeExamplesEl.innerHTML = "";
  (edge.examples || []).forEach((example) => {
    const li = document.createElement("li");
    const yamlMatch = example.match(/(TS\d+_[\w]+\.yaml)/i);
    if (yamlMatch) {
      const a = document.createElement("a");
      a.href = `/?yaml=${encodeURIComponent(yamlMatch[1])}`;
      a.textContent = example;
      li.appendChild(a);
    } else {
      li.textContent = example;
    }
    edgeExamplesEl.appendChild(li);
  });
}

function hideEdgeDetails() {
  edgeDetailsEl.classList.add("hidden");
}

function showNodeDetails(nfId, topology) {
  hideEdgeDetails();
  const node = topology.nodes.find((n) => n.id === nfId);
  if (!node || !nodeDetailsEl) return;
  nodeDetailsEl.classList.remove("hidden");
  nodeSummaryEl.textContent = `${node.label} — ${node.serviceCount} service(s) in corpus`;
  if (nodeSpecsLinkEl) {
    nodeSpecsLinkEl.href = `/specs?nf=${encodeURIComponent(nfId)}`;
    nodeSpecsLinkEl.textContent = `Specs for ${nfId} →`;
  }
  network?.selectNodes([nfId]);
  network?.focus(nfId, { scale: 1.2, animation: true });
}

function hideNodeDetails() {
  nodeDetailsEl?.classList.add("hidden");
}

async function loadTopology(refresh = false) {
  statusEl.textContent = "Loading topology...";
  hideEdgeDetails();
  hideNodeDetails();

  const params = new URLSearchParams({
    coreOnly: coreOnlyEl.checked ? "true" : "false",
    minWeight: minWeightEl.value,
    refresh: refresh ? "true" : "false",
  });

  try {
    const res = await fetch(`/api/topology?${params}`);
    if (!res.ok) {
      throw new Error(`API error ${res.status}`);
    }
    const data = await res.json();
    renderGraph(data);
    const nfParam = new URLSearchParams(window.location.search).get("nf");
    if (nfParam && network) {
      showNodeDetails(nfParam.toUpperCase(), data);
    }
  } catch (err) {
    showEmptyState(`Failed to load topology: ${err.message}`);
    statusEl.textContent = `Failed: ${err.message}`;
    console.error(err);
  }
}

minWeightEl.addEventListener("input", () => {
  minWeightValueEl.textContent = minWeightEl.value;
});

coreOnlyEl.addEventListener("change", () => loadTopology(false));
minWeightEl.addEventListener("change", () => loadTopology(false));
refreshBtn.addEventListener("click", () => loadTopology(true));

window.addEventListener("load", () => loadTopology(false));
