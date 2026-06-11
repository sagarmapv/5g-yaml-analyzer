/** On GitHub Pages, resolve /api/* to baked demo/data/*.json */
(function () {
  const path = window.location.pathname || "";
  const isPages =
    path.includes("/5g-yaml-analyzer/") ||
    path.includes("/5g-visualizer/") ||
    path.match(/\/[^/]+\/ladder\.html/) ||
    document.querySelector('meta[name="demo-mode"]');

  if (!isPages && !window.DEMO_MODE) return;

  function basePath() {
    const parts = path.split("/").filter(Boolean);
    if (parts.length && parts[parts.length - 1].endsWith(".html")) {
      parts.pop();
    }
    return parts.length ? "/" + parts.join("/") : "";
  }

  const DEMO_BASE = (window.DEMO_BASE || basePath()) + "/demo/data";

  const originalFetch = window.fetch.bind(window);

  window.fetch = async function demoFetch(input, init) {
    const url = typeof input === "string" ? input : input.url;
    if (!url.startsWith("/api/")) {
      return originalFetch(input, init);
    }

    let demoUrl = null;
    const ladderMatch = url.match(/^\/api\/stories\/([^/?]+)\/ladder/);
    const hubMatch = url.match(/^\/api\/stories\/([^/?]+)/);
    const opMatch = url.match(/^\/api\/operations\/([^/?]+)/);
    const specPreviewMatch = url.match(/^\/api\/specs\/([^/?]+)\/preview/);
    const topologyMatch = url.match(/^\/api\/topology/);
    const nfsMatch = url.match(/^\/api\/nfs/);

    if (ladderMatch) {
      demoUrl = `${DEMO_BASE}/ladder-${ladderMatch[1]}.json`;
    } else if (hubMatch && url.includes("view=hub")) {
      demoUrl = `${DEMO_BASE}/stories-${hubMatch[1]}-hub.json`;
    } else if (opMatch) {
      demoUrl = `${DEMO_BASE}/operations/${decodeURIComponent(opMatch[1])}.json`;
    } else if (specPreviewMatch) {
      const ts = decodeURIComponent(specPreviewMatch[1]);
      demoUrl = `${DEMO_BASE}/specs/${ts}-preview.json`;
    } else if (topologyMatch) {
      demoUrl = `${DEMO_BASE}/topology-core.json`;
    } else if (nfsMatch) {
      demoUrl = `${DEMO_BASE}/nf-catalog-summary.json`;
    }

    if (demoUrl) {
      const res = await originalFetch(demoUrl, init);
      if (res.ok) return res;
    }
    return originalFetch(input, init);
  };
})();
