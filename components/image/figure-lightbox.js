// Accessible full-size figure viewer for the report.
(() => {
  const dialog = document.createElement("dialog");
  dialog.className = "figure-lightbox";
  dialog.setAttribute("aria-label", "Expanded report figure");
  dialog.innerHTML = '<div class="lightbox-panel"><button type="button" class="lightbox-close" aria-label="Close enlarged figure">&times;</button><img alt=""><p class="lightbox-caption"></p></div>';
  document.body.appendChild(dialog);
  const enlarged = dialog.querySelector("img");
  const caption = dialog.querySelector(".lightbox-caption");
  let trigger = null;
  function open(img) {
    trigger = img;
    enlarged.src = img.currentSrc || img.src;
    enlarged.alt = img.alt;
    caption.textContent = img.closest("figure")?.querySelector("figcaption")?.textContent?.trim() || img.alt;
    dialog.showModal();
    document.body.classList.add("lightbox-open");
    dialog.querySelector(".lightbox-close").focus();
  }
  function close() { dialog.close(); }
  document.querySelectorAll(".report-figure img").forEach(img => {
    img.tabIndex = 0;
    img.setAttribute("role", "button");
    img.setAttribute("aria-label", "Enlarge: " + (img.alt || "figure"));
    img.addEventListener("click", () => open(img));
    img.addEventListener("keydown", e => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(img); }
    });
  });
  dialog.querySelector(".lightbox-close").addEventListener("click", close);
  dialog.addEventListener("click", e => { if (e.target === dialog) close(); });
  dialog.addEventListener("close", () => {
    document.body.classList.remove("lightbox-open");
    enlarged.removeAttribute("src");
    trigger?.focus();
  });
})();
