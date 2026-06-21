/* Virtual Factory — Panel Resizer (v2)
   Drag handles to resize sidebar and right panel.
   Sizes persist in localStorage.
 */
const RESIZER = (() => {
  const LS_KEY = "vf-panel-sizes-v2";
  const DEFAULT_SIDEBAR = 230;
  const DEFAULT_RIGHT = 320;
  let activeHandle = null, startX = 0, startY = 0, startSize = 0;

  function loadSizes() {
    try { return JSON.parse(localStorage.getItem(LS_KEY)) || {}; } catch(e) { return {}; }
  }
  function saveSizes(s) { localStorage.setItem(LS_KEY, JSON.stringify(s)); }

  function applySizes() {
    const s = loadSizes();
    const root = document.documentElement;
    root.style.setProperty("--sidebar-w", (s.sidebarW || DEFAULT_SIDEBAR) + "px");
    root.style.setProperty("--property-w", (s.propertyW || DEFAULT_RIGHT) + "px");
  }

  function init() {
    applySizes();
    // All resize handles
    document.querySelectorAll(".resize-handle, #resize-sidebar").forEach(h => {
      h.addEventListener("mousedown", onStart);
      h.addEventListener("touchstart", onStart, {passive:false});
    });
    document.addEventListener("mousemove", onMove);
    document.addEventListener("touchmove", onMove, {passive:false});
    document.addEventListener("mouseup", onEnd);
    document.addEventListener("touchend", onEnd);
  }

  function onStart(e) {
    activeHandle = e.target.closest(".resize-handle, #resize-sidebar");
    if (!activeHandle) return;
    e.preventDefault();
    const pt = e.touches ? e.touches[0] : e;
    startX = pt.clientX;
    startY = pt.clientY;
    const target = activeHandle.dataset.target || activeHandle.id === "resize-sidebar" ? "sidebar" : null;
    // Determine actual target
    let actualTarget = target;
    if (activeHandle.id === "resize-sidebar") actualTarget = "sidebar";
    else if (activeHandle.dataset.target === "right") actualTarget = "right";
    else actualTarget = target;

    const root = document.documentElement;
    const style = getComputedStyle(root);

    if (actualTarget === "sidebar") {
      startSize = parseInt(style.getPropertyValue("--sidebar-w")) || DEFAULT_SIDEBAR;
    } else if (actualTarget === "right") {
      startSize = parseInt(style.getPropertyValue("--property-w")) || DEFAULT_RIGHT;
    }
    activeHandle.classList.add("active");
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }

  function onMove(e) {
    if (!activeHandle) return;
    const pt = e.touches ? e.touches[0] : e;
    const dx = pt.clientX - startX;
    const root = document.documentElement;
    const sizes = loadSizes();

    let actualTarget = activeHandle.dataset.target;
    if (activeHandle.id === "resize-sidebar") actualTarget = "sidebar";
    else if (activeHandle.dataset.target === "right") actualTarget = "right";

    if (actualTarget === "sidebar") {
      const w = Math.max(0, Math.min(500, startSize + dx));
      root.style.setProperty("--sidebar-w", w + "px");
      sizes.sidebarW = w;
    } else if (actualTarget === "right") {
      const w = Math.max(180, Math.min(600, startSize - dx));
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
