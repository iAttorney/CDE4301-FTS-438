// The sidebar belongs to the top-level shell, not to individual chapters.
// Chapter links navigate the named iframe, leaving Shoelace tree state and
// sidebar scroll position untouched.
(() => {
  const frame = document.getElementById("report-frame");
  const sidebar = document.querySelector(".sidebar");
  if (!frame || !sidebar) return;
  const tree = sidebar.querySelector(".table-of-content");
  const allowed = /^(?:index|references|section-[0-9]+(?:-[0-9]+)?)\.html$/;
  const normalize = href => {
    const u = new URL(href, location.href);
    return u.origin === location.origin && allowed.test(u.pathname.split("/").pop())
      ? u : null;
  };
  const links = [...tree.querySelectorAll('a[href]')];
  links.forEach(link => {
    const url = normalize(link.href);
    if (!url) return;
    link.target = "report-frame";
    link.removeAttribute("aria-current");
  });
  const brand = sidebar.querySelector(".sidebar-brand");
  if (brand) brand.href = "index.html";
  const toggle = sidebar.querySelector(".mobile-nav-toggle");
  if (toggle) toggle.addEventListener("click", () => {
    const expanded = sidebar.classList.toggle("open");
    toggle.setAttribute("aria-expanded", String(expanded));
  });
  // Prevent old inline mobile handlers from toggling the menu a second time.
  if (toggle) toggle.removeAttribute("onclick");

  const select = () => {
    try {
      const u = new URL(frame.contentWindow.location.href);
      const file = u.pathname.split("/").pop();
      const hash = u.hash;
      links.forEach(link => {
        const target = normalize(link.href);
        if (!target) return;
        const selected = target.pathname.split("/").pop() === file && (!target.hash || target.hash === hash);
        if (selected && (hash ? !!target.hash : !target.hash)) link.setAttribute("aria-current", "page");
        else link.removeAttribute("aria-current");
      });
      const query = new URL(location.href);
      if (file && allowed.test(file)) {
        query.searchParams.set("page", file);
        if (hash) query.searchParams.set("anchor", hash.slice(1));
        else query.searchParams.delete("anchor");
        history.replaceState(null, "", query);
      }
    } catch (_) { /* Browser cross-origin protection: do not alter the sidebar. */ }
  };
  frame.addEventListener("load", select);
  const params = new URLSearchParams(location.search);
  const requested = params.get("page");
  const anchor = params.get("anchor");
  if (requested && allowed.test(requested) && requested !== "index.html") {
    frame.src = requested + (anchor ? "#" + encodeURIComponent(anchor) : "");
  }
  // When an anchor is selected within the same iframe document, load may not fire.
  tree.addEventListener("click", event => {
    const link = event.target.closest("a[href]");
    if (!link) return;
    const url = normalize(link.href);
    if (!url) return;
    setTimeout(select, 0);
  });
})();
