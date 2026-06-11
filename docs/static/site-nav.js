/** Highlight the active item in .page-nav based on current URL. */
(function initSiteNav() {
  const path = window.location.pathname.replace(/\/+$/, "") || "/";

  document.querySelectorAll(".page-nav .nav-link").forEach((link) => {
    link.classList.remove("active");
    const nav = link.dataset.nav;
    if (!nav) return;

    let active = false;
    if (nav === "explorer" && path === "/") active = true;
    else if (nav === "topology" && path === "/topology") active = true;
    else if (nav === "specs" && (path === "/specs" || path.startsWith("/specs/"))) active = true;
    else if (nav === "stories" && path === "/stories") active = true;
    else if (nav === "ladder" && path === "/ladder") active = true;
    // legacy data-nav values
    else if (nav === "tsmap" && path === "/specs") active = true;
    else if (nav === "story" && path.startsWith("/specs/") && path !== "/specs") active = true;

    if (active) link.classList.add("active");
  });
})();
