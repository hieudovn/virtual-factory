/* Virtual Factory — Panel Resizer
   Drag handles to resize sidebar, bottom panel, and property panel.
   Sizes persist in localStorage.
 */
const RESIZER = (() => {
  const LS_KEY = "vf-panel-sizes";
  let activeHandle = null, startX = 0, startY = 0, startSize = 0;

  function loadSizes() {
    try { return JSON.parse(localStorage.getItem(LS_KEY)) || {}; } catch(e) { return {}; }
  }
  function saveSizes(s) { localStorage.setItem(LS_KEY, JSON.stringify(s)); }

  function applySizes() {
    const s = loadSizes();
    const root = document.documentElement;
    if (s.sidebarW) root.style.setProperty("--sidebar-w", s.sidebarW + "px");
    if (s.bottomH) root.style.setProperty("--bottombar-h", s.bottomH + "px");
    if (s.propertyW) root.style.setProperty("--property-w", s.propertyW + "px");
  }

  function init() {
    applySizes();
    document.querySelectorAll(".resize-handle").forEach(h => {
      h.addEventListener("mousedown", onStart);
      h.addEventListener("touchstart", onStart, {passive:false});
    });
    document.addEventListener("mousemove", onMove);
    document.addEventListener("touchmove", onMove, {passive:false});
    document.addEventListener("mouseup", onEnd);
    document.addEventListener("touchend", onEnd);

    // Sidebar toggle
    const toggle = document.getElementById("sidebar-toggle");
    if (toggle) {
      toggle.addEventListener("click", () => {
        const root = document.documentElement;
        const sidebar = document.querySelector(".sidebar");
        const cur = root.style.getPropertyValue("--sidebar-w") || getComputedStyle(root).getPropertyValue("--sidebar-w");
        const curPx = parseInt(cur) || 0;
        if (curPx < 50) {
          const saved = loadSizes().sidebarW || 260;
          root.style.setProperty("--sidebar-w", saved + "px");
          if (sidebar) sidebar.classList.remove("collapsed");
          toggle.textContent = "☰";
        } else {
          root.style.setProperty("--sidebar-w", "0px");
          if (sidebar) sidebar.classList.add("collapsed");
          toggle.textContent = "▶";
        }
      });
    }
  }

  function onStart(e) {
    activeHandle = e.target.closest(".resize-handle");
    if (!activeHandle) return;
    e.preventDefault();
    const pt = e.touches ? e.touches[0] : e;
    startX = pt.clientX;
    startY = pt.clientY;
    const target = activeHandle.dataset.target;
    const root = document.documentElement;
    const style = getComputedStyle(root);

    if (target === "sidebar") {
      startSize = parseInt(style.getPropertyValue("--sidebar-w")) || 260;
    } else if (target === "bottom") {
      startSize = parseInt(style.getPropertyValue("--bottombar-h")) || 320;
    } else if (target === "property") {
      startSize = parseInt(style.getPropertyValue("--property-w")) || 280;
    }
    activeHandle.classList.add("active");
    document.body.style.cursor = activeHandle.classList.contains("resize-handle-h") ? "row-resize" : "col-resize";
    document.body.style.userSelect = "none";
  }

  function onMove(e) {
    if (!activeHandle) return;
    const pt = e.touches ? e.touches[0] : e;
    const dx = pt.clientX - startX;
    const dy = pt.clientY - startY;
    const target = activeHandle.dataset.target;
    const root = document.documentElement;
    const sizes = loadSizes();

    if (target === "sidebar") {
      const w = Math.max(0, Math.min(500, startSize + dx));
      root.style.setProperty("--sidebar-w", w + "px");
      sizes.sidebarW = w;
    } else if (target === "bottom") {
      const h = Math.max(120, Math.min(700, startSize - dy));
      root.style.setProperty("--bottombar-h", h + "px");
      sizes.bottomH = h;
    } else if (target === "property") {
      const w = Math.max(0, Math.min(500, startSize - dx));
      root.style.setProperty("--property-w", w + "px");
      sizes.propertyW = w;
    }
    saveSizes(sizes);
  }

  function onEnd() {
    if (activeHandle) activeHandle.classList.remove("active");
    activeHandle = null;
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
  }

  return { init, applySizes };
})();

document.addEventListener("DOMContentLoaded", () => RESIZER.init());
