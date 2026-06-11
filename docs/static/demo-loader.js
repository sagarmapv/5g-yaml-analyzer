/** On GitHub Pages, resolve /api/* to baked demo/data/*.json */
(function () {
  const path = window.location.pathname || "";
  const isPages =
    path.includes("/5g-yaml-analyzer/") ||
    path.includes("/5g-visualizer/") ||
    path.match(/\/[^/]+\/ladder\.html/) ||
    document.querySelector('meta[name="demo-mode"]');

  if (!isPages && !window.DEMO_MODE) return;

  function demoDataUrl(filename) {
    const meta = document.querySelector('meta[name="demo-base"]');
    const base = (meta && meta.content) || "./demo/data";
    const root = base.endsWith("/") ? base : `${base}/`;
    return new URL(filename, new URL(root, window.location.href)).href;
  }

  const originalFetch = window.fetch.bind(window);

  window.fetch = async function demoFetch(input, init) {
    const url = typeof input === "string" ? input : input.url;
    if (!url.startsWith("/api/")) {
      return originalFetch(input, init);
    }

    let demoFile = null;
    const ladderMatch = url.match(/^\/api\/stories\/([^/?]+)\/ladder/);
    const hubMatch = url.match(/^\/api\/stories\/([^/?]+)/);
    const opMatch = url.match(/^\/api\/operations\/([^/?]+)/);
    const specPreviewMatch = url.match(/^\/api\/specs\/([^/?]+)\/preview/);
    const topologyMatch = url.match(/^\/api\/topology/);
    const nfsMatch = url.match(/^\/api\/nfs/);

    if (ladderMatch) {
      demoFile = `ladder-${ladderMatch[1]}.json`;
    } else if (hubMatch && url.includes("view=hub")) {
      demoFile = `stories-${hubMatch[1]}-hub.json`;
    } else if (opMatch) {
      demoFile = `operations/${decodeURIComponent(opMatch[1])}.json`;
    } else if (specPreviewMatch) {
      const ts = decodeURIComponent(specPreviewMatch[1]);
      demoFile = `specs/${ts}-preview.json`;
    } else if (topologyMatch) {
      demoFile = "topology-core.json";
    } else if (nfsMatch) {
      demoFile = "nf-catalog-summary.json";
    }

    if (demoFile) {
      const res = await originalFetch(demoDataUrl(demoFile), init);
      if (res.ok) return res;
    }
    return originalFetch(input, init);
  };
})();
