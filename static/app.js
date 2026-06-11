const fileListEl = document.getElementById("file-list");
const searchInput = document.getElementById("search-input");
const searchResultsEl = document.getElementById("search-results");
const yamlDisplay = document.getElementById("yaml-display");
const jsonDisplay = document.getElementById("json-display");
const yamlFilenameEl = document.getElementById("yaml-filename");
const operationCountEl = document.getElementById("operation-count");
const serviceDescriptionEl = document.getElementById("service-description");
const specStoryLinkEl = document.getElementById("spec-story-link");
const healthStatusEl = document.getElementById("health-status");
const rebuildBtn = document.getElementById("rebuild-btn");
const expandAllBtn = document.getElementById("expand-all-btn");
const collapseAllBtn = document.getElementById("collapse-all-btn");
const toastEl = document.getElementById("toast");

let mapData = { nfs: [] };
let activeFilename = null;
let searchTimeout = null;

function sourceFile(entry) {
  return entry.sourceFile || entry.source_file || "";
}

function showToast(message, isError = false) {
  toastEl.textContent = message;
  toastEl.classList.toggle("error", isError);
  toastEl.classList.remove("hidden");
  setTimeout(() => toastEl.classList.add("hidden"), 3000);
}

async function loadHealth() {
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    const parts = [
      `${data.yamlCount} YAMLs`,
      `${data.bankCount} banks`,
    ];
    if (data.buildStatus?.lastRebuild) {
      const when = new Date(data.buildStatus.lastRebuild).toLocaleString();
      parts.push(`built ${when}`);
    }
    healthStatusEl.textContent = parts.join(" · ");
  } catch {
    healthStatusEl.textContent = "Health check failed";
  }
}

function renderIndex(filter = "") {
  const q = filter.trim().toLowerCase();
  fileListEl.innerHTML = "";

  const nfs = mapData.nfs || [];
  if (!nfs.length) {
    fileListEl.innerHTML = '<p class="placeholder">No map loaded. Add YAMLs and click Rebuild.</p>';
    return;
  }

  let visibleNfs = 0;

  for (const nfBlock of nfs) {
    const nfName = nfBlock.nf;
    const filteredSpecs = [];

    for (const spec of nfBlock.specs || []) {
      const filteredYamls = (spec.yamls || []).filter((entry) => {
        if (!q) return true;
        return (
          nfName.toLowerCase().includes(q) ||
          spec.tsNumber.toLowerCase().includes(q) ||
          (spec.title || "").toLowerCase().includes(q) ||
          entry.service.toLowerCase().includes(q) ||
          entry.sourceFile.toLowerCase().includes(q)
        );
      });
      if (filteredYamls.length) {
        filteredSpecs.push({ ...spec, yamls: filteredYamls });
      }
    }

    if (!filteredSpecs.length) continue;
    visibleNfs++;

    const yamlTotal = filteredSpecs.reduce((n, s) => n + s.yamls.length, 0);
    const block = document.createElement("div");
    block.className = "nf-block";

    const nfHeader = document.createElement("div");
    nfHeader.className = "nf-header" + (q ? " expanded" : "");
    nfHeader.textContent = `${nfName} (${filteredSpecs.length} spec, ${yamlTotal} yaml)`;

    const specContainer = document.createElement("div");
    specContainer.className = "spec-container" + (q ? " visible" : "");

    nfHeader.addEventListener("click", () => {
      nfHeader.classList.toggle("expanded");
      specContainer.classList.toggle("visible");
    });

    filteredSpecs.forEach((spec) => {
      const specBlock = document.createElement("div");
      specBlock.className = "spec-block";

      const specHeader = document.createElement("div");
      specHeader.className = "spec-header" + (q ? " expanded" : "");
      const titlePart = spec.title ? ` — ${spec.title}` : "";
      specHeader.innerHTML = `<a class="spec-platform-link" href="/specs?ts=${encodeURIComponent(spec.tsNumber)}" title="Open in Specs platform">TS ${spec.tsNumber}</a>${escapeHtml(titlePart)} (${spec.yamls.length}) <a class="spec-story-mini" href="/specs?ts=${encodeURIComponent(spec.tsNumber)}&view=story" title="Story">story</a>`;

      const yamlList = document.createElement("div");
      yamlList.className = "service-list" + (q ? " visible" : "");

      specHeader.addEventListener("click", (e) => {
        if (e.target.closest("a")) return;
        e.stopPropagation();
        specHeader.classList.toggle("expanded");
        yamlList.classList.toggle("visible");
      });

      spec.yamls.forEach((entry) => {
        const sf = entry.sourceFile;
        const wrapper = document.createElement("div");
        wrapper.className = "service-item";

        const link = document.createElement("span");
        link.className = "service-link" + (sf === activeFilename ? " active" : "");
        link.textContent = entry.service;
        link.title = sf;
        link.onclick = () => loadService(sf);

        const yamlLink = document.createElement("a");
        yamlLink.className = "yaml-link";
        yamlLink.href = `/api/yaml/${sf}`;
        yamlLink.textContent = "[YAML]";
        yamlLink.target = "_blank";

        wrapper.appendChild(link);
        wrapper.appendChild(yamlLink);
        yamlList.appendChild(wrapper);
      });

      specBlock.appendChild(specHeader);
      specBlock.appendChild(yamlList);
      specContainer.appendChild(specBlock);
    });

    block.appendChild(nfHeader);
    block.appendChild(specContainer);
    fileListEl.appendChild(block);
  }

  if (visibleNfs === 0) {
    fileListEl.innerHTML = '<p class="placeholder">No matching NF / spec / YAML</p>';
  }
}

async function loadIndex() {
  try {
    const res = await fetch("/api/map");
    mapData = await res.json();
    renderIndex(searchInput.value);
  } catch (err) {
    fileListEl.innerHTML = `<p class="error">Failed to load map: ${err.message}</p>`;
  }
}

async function loadService(filename) {
  activeFilename = filename;
  renderIndex(searchInput.value);

  yamlFilenameEl.textContent = filename;
  operationCountEl.textContent = "";
  serviceDescriptionEl.textContent = "";
  serviceDescriptionEl.classList.add("hidden");
  yamlDisplay.innerHTML = '<p class="loading">Loading YAML...</p>';
  jsonDisplay.innerHTML = '<p class="loading">Loading operations...</p>';

  try {
    const [yamlRes, jsonRes, bankRes] = await Promise.all([
      fetch(`/api/yaml/${filename}`),
      fetch(`/api/parsed/${filename}`),
      fetch(`/api/bank/${filename}`),
    ]);

    if (!yamlRes.ok) throw new Error(`YAML: ${yamlRes.statusText}`);
    if (!jsonRes.ok) throw new Error(`Parsed: ${jsonRes.statusText}`);

    const yamlText = await yamlRes.text();
    const jsonData = await jsonRes.json();

    yamlDisplay.innerHTML = `<pre>${escapeHtml(yamlText)}</pre>`;
    operationCountEl.textContent = `${jsonData.length} operations`;

    if (specStoryLinkEl) {
      const tsMatch = filename.match(/^TS(\d{2})(\d{3})_/i);
      if (tsMatch) {
        const ts = `${tsMatch[1]}.${tsMatch[2]}`;
        specStoryLinkEl.href = `/specs?ts=${encodeURIComponent(ts)}&view=story`;
        specStoryLinkEl.textContent = `Specs platform: TS ${ts} →`;
        specStoryLinkEl.classList.remove("hidden");
      } else {
        specStoryLinkEl.classList.add("hidden");
      }
    }

    if (bankRes.ok) {
      const bank = await bankRes.json();
      const desc = (bank.serviceDescription || "").trim();
      if (desc) {
        const preview = desc.length > 280 ? `${desc.slice(0, 280)}…` : desc;
        serviceDescriptionEl.textContent = preview;
        serviceDescriptionEl.classList.remove("hidden");
      }
    }

    renderParsedSummary(jsonData, filename);
  } catch (err) {
    yamlDisplay.innerHTML = `<p class="error">${escapeHtml(err.message)}</p>`;
    jsonDisplay.innerHTML = `<p class="error">${escapeHtml(err.message)}</p>`;
  }
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function renderParsedSummary(parsedData, filename) {
  jsonDisplay.innerHTML = "";

  if (!parsedData.length) {
    jsonDisplay.innerHTML = '<p class="placeholder">No operations found</p>';
    return;
  }

  parsedData.forEach((msg) => {
    const block =
      window.MessageDetail?.appendParsedMessageBlock(jsonDisplay, msg, filename) ||
      (() => {
        const el = document.createElement("div");
        jsonDisplay.appendChild(el);
        return el;
      })();

    if (msg.operationId && block.parentNode) {
      block.appendChild(createCurlSection(filename, msg.operationId));
    }
  });
}

function createCollapsibleSection(title, items) {
  const section = document.createElement("div");

  const header = document.createElement("div");
  header.className = "section-header";
  header.textContent = "▶ " + title;

  const content = document.createElement("div");
  content.className = "section-content";

  items.forEach((item) => {
    const row = document.createElement("div");
    row.textContent = item;
    content.appendChild(row);
  });

  header.onclick = () => {
    const open = content.classList.toggle("visible");
    header.textContent = (open ? "▼ " : "▶ ") + title;
  };

  section.appendChild(header);
  section.appendChild(content);
  return section;
}

function createCurlSection(filename, operationId) {
  const row = document.createElement("div");
  row.className = "curl-row";

  const pre = document.createElement("pre");
  pre.textContent = "Loading curl...";

  const btn = document.createElement("button");
  btn.className = "copy-btn";
  btn.textContent = "Copy curl";
  btn.disabled = true;

  row.appendChild(pre);
  row.appendChild(btn);

  fetch(`/api/curl/${filename}/${encodeURIComponent(operationId)}`)
    .then((res) => res.json())
    .then((data) => {
      if (data.curl) {
        pre.textContent = data.curl;
        btn.disabled = false;
        btn.onclick = () => {
          navigator.clipboard.writeText(data.curl);
          showToast("curl copied to clipboard");
        };
      } else {
        pre.textContent = data.error || "curl unavailable";
      }
    })
    .catch(() => {
      pre.textContent = "Failed to load curl";
    });

  return row;
}

async function runSearch(query) {
  if (!query.trim()) {
    searchResultsEl.classList.add("hidden");
    searchResultsEl.innerHTML = "";
    renderIndex("");
    return;
  }

  renderIndex(query);

  try {
    const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
    const results = await res.json();

    if (results.length === 0) {
      searchResultsEl.innerHTML = '<p class="placeholder">No deep search matches</p>';
    } else {
      searchResultsEl.innerHTML = "";
      results.slice(0, 20).forEach((hit) => {
        const item = document.createElement("div");
        item.className = "search-result-item";
        item.innerHTML = `<strong>${escapeHtml(hit.nf)}</strong> · ${escapeHtml(hit.method)} ${escapeHtml(hit.path)}<br><small>${escapeHtml(hit.operationId)}</small>`;
        item.onclick = () => {
          loadService(hit.sourceFile);
          searchResultsEl.classList.add("hidden");
        };
        searchResultsEl.appendChild(item);
      });
      if (results.length > 20) {
        const more = document.createElement("p");
        more.className = "placeholder";
        more.textContent = `+ ${results.length - 20} more results`;
        searchResultsEl.appendChild(more);
      }
    }
    searchResultsEl.classList.remove("hidden");
  } catch {
    searchResultsEl.classList.add("hidden");
  }
}

searchInput.addEventListener("input", () => {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => runSearch(searchInput.value), 250);
});

expandAllBtn.addEventListener("click", () => {
  document.querySelectorAll(".nf-header, .spec-header").forEach((el) => el.classList.add("expanded"));
  document.querySelectorAll(".spec-container, .service-list").forEach((el) => el.classList.add("visible"));
});

collapseAllBtn.addEventListener("click", () => {
  document.querySelectorAll(".nf-header, .spec-header").forEach((el) => el.classList.remove("expanded"));
  document.querySelectorAll(".spec-container, .service-list").forEach((el) => el.classList.remove("visible"));
});

rebuildBtn.addEventListener("click", async () => {
  rebuildBtn.disabled = true;
  rebuildBtn.textContent = "Rebuilding...";
  try {
    const res = await fetch("/api/rebuild", { method: "POST" });
    const data = await res.json();
    if (data.ok) {
      showToast(`Rebuild complete: ${data.status.parsedCount} files parsed`);
      await loadIndex();
      await loadHealth();
    } else {
      showToast(data.error || "Rebuild failed", true);
    }
  } catch (err) {
    showToast(err.message, true);
  } finally {
    rebuildBtn.disabled = false;
    rebuildBtn.textContent = "Rebuild";
  }
});

window.onload = async () => {
  await loadIndex();
  await loadHealth();
  const params = new URLSearchParams(window.location.search);
  const yaml = params.get("yaml");
  if (yaml) {
    await loadService(yaml);
  }
};
