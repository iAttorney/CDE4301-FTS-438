// The sidebar belongs to the top-level shell, not to individual chapters.
// Chapter links navigate the named iframe, leaving Shoelace tree state and
// sidebar scroll position untouched.
(() => {
  const allowed = /^(?:references|appendix|section-[0-9]+(?:-[0-9]+)?)\.html$/;
  const frame = document.getElementById("report-frame");
  const sidebar = document.querySelector(".sidebar");

  if (frame && sidebar) {
    initShell(frame, sidebar);
  } else if (window.parent !== window) {
    initChapter();
  }

  function initShell(frameEl, sidebarEl) {
    const tree = sidebarEl.querySelector(".table-of-content");
    if (!tree) return;

    const normalize = href => {
      const u = new URL(href, location.href);
      return u.origin === location.origin && allowed.test(u.pathname.split("/").pop())
        ? u
        : null;
    };

    const links = [...tree.querySelectorAll("a[href]")];
    links.forEach(link => {
      const url = normalize(link.href);
      if (!url) return;
      link.target = "report-frame";
      link.removeAttribute("aria-current");
    });

    const brand = sidebarEl.querySelector(".sidebar-brand");
    if (brand) {
      brand.href = "index.html";
      brand.removeAttribute("aria-current");
    }

    const toggle = sidebarEl.querySelector(".mobile-nav-toggle");
    if (toggle) {
      toggle.addEventListener("click", () => {
        const expanded = sidebarEl.classList.toggle("open");
        toggle.setAttribute("aria-expanded", String(expanded));
      });
      // Prevent old inline mobile handlers from toggling the menu a second time.
      toggle.removeAttribute("onclick");
    }

    const findActiveLink = (file, hash) => {
      const fileLinks = links.filter(link => {
        const target = normalize(link.href);
        return target && target.pathname.split("/").pop() === file;
      });
      if (!fileLinks.length) return null;
      if (hash) {
        const exact = fileLinks.find(link => normalize(link.href).hash === hash);
        if (exact) return exact;
      }
      return fileLinks.find(link => !normalize(link.href).hash) || fileLinks[0];
    };

    const applySelection = (file, hash = "", { scrollSidebar = true, updateUrl = true } = {}) => {
      if (!file || !allowed.test(file)) return;
      const activeLink = findActiveLink(file, hash);
      let changed = false;

      links.forEach(link => {
        if (link === activeLink) {
          if (link.getAttribute("aria-current") !== "page") {
            link.setAttribute("aria-current", "page");
            changed = true;
          }
        } else if (link.hasAttribute("aria-current")) {
          link.removeAttribute("aria-current");
        }
      });

      const activeItem = activeLink ? activeLink.closest("sl-tree-item") : null;
      tree.querySelectorAll("sl-tree-item").forEach(item => {
        const isSelected = item === activeItem;
        item.selected = isSelected;
        item.toggleAttribute("selected", isSelected);
      });

      if (changed && activeItem) {
        let parent = activeItem.parentElement
          ? activeItem.parentElement.closest("sl-tree-item")
          : null;
        while (parent) {
          parent.expanded = true;
          parent.setAttribute("expanded", "");
          parent = parent.parentElement
            ? parent.parentElement.closest("sl-tree-item")
            : null;
        }
        if (scrollSidebar) {
          activeLink.scrollIntoView({ block: "nearest" });
        }
      }

      if (updateUrl) {
        try {
          const query = new URL(location.href);
          query.searchParams.set("page", file);
          if (hash) query.searchParams.set("anchor", hash.slice(1));
          else query.searchParams.delete("anchor");
          history.replaceState(null, "", query.search + location.hash);
        } catch (_) {
          /* Ignore history restrictions on restricted origins. */
        }
      }
    };

    const selectFromFrame = () => {
      try {
        const u = new URL(frameEl.contentWindow.location.href);
        const file = u.pathname.split("/").pop();
        if (!file || !allowed.test(file)) return;
        applySelection(file, u.hash);
      } catch (_) {
        /* Cross-origin protection (e.g. file://): chapter postMessage handles sync. */
      }
    };

    frameEl.addEventListener("load", selectFromFrame);

    window.addEventListener("message", event => {
      if (event.source !== frameEl.contentWindow) return;
      const data = event.data;
      if (!data || (data.type !== "report-nav" && data.type !== "report-scroll")) return;
      if (!allowed.test(data.page)) return;
      applySelection(data.page, data.hash || "");
    });

    const params = new URLSearchParams(location.search);
    const requested = params.get("page");
    const anchor = params.get("anchor");
    if (requested && allowed.test(requested)) {
      const targetSrc = requested + (anchor ? "#" + encodeURIComponent(anchor) : "");
      if (requested !== "section-1.html" || anchor) {
        frameEl.src = targetSrc;
      }
      applySelection(requested, anchor ? "#" + anchor : "", { updateUrl: false });
    } else {
      applySelection("section-1.html", "", { updateUrl: false });
      selectFromFrame();
    }

    tree.addEventListener("click", event => {
      const link = event.target.closest("a[href]");
      if (!link) return;
      const url = normalize(link.href);
      if (!url) return;
      applySelection(url.pathname.split("/").pop(), url.hash);
      if (sidebarEl.classList.contains("open") && toggle) {
        sidebarEl.classList.remove("open");
        toggle.setAttribute("aria-expanded", "false");
      }
    });
  }

  function initChapter() {
    const file = location.pathname.split("/").pop();
    if (!file || !allowed.test(file)) return;

    const post = (type, hash) => {
      window.parent.postMessage({ type, page: file, hash }, "*");
    };

    let lastReportedHash = location.hash;
    let lockUntil = location.hash ? Date.now() + 600 : 0;

    post("report-nav", location.hash);

    window.addEventListener("hashchange", () => {
      lockUntil = Date.now() + 600;
      lastReportedHash = location.hash;
      post("report-nav", location.hash);
    });

    const sections = [...document.querySelectorAll("main section[id] section[id]")];
    if (!sections.length) return;

    let ticking = false;
    const updateFromScroll = () => {
      ticking = false;
      if (Date.now() < lockUntil) return;

      const doc = document.documentElement;
      const scrollTop = window.scrollY;
      let activeHash = "";

      if (scrollTop > 16) {
        const atBottom =
          doc.scrollHeight - window.innerHeight > 40 &&
          scrollTop + window.innerHeight >= doc.scrollHeight - 4;
        const last = sections[sections.length - 1];
        if (atBottom && last.getBoundingClientRect().top < window.innerHeight * 0.75) {
          activeHash = "#" + last.id;
        } else {
          const threshold = Math.min(160, window.innerHeight * 0.25);
          for (const sec of sections) {
            if (sec.getBoundingClientRect().top <= threshold) {
              activeHash = "#" + sec.id;
            } else {
              break;
            }
          }
        }
      }

      if (activeHash !== lastReportedHash) {
        lastReportedHash = activeHash;
        post("report-scroll", activeHash);
      }
    };

    window.addEventListener(
      "scroll",
      () => {
        if (!ticking) {
          ticking = true;
          requestAnimationFrame(updateFromScroll);
        }
      },
      { passive: true },
    );
  }
})();
