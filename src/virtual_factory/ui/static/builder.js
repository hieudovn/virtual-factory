/* Virtual Factory — Asset Builder (v2)
   Drag-and-drop equipment from palette onto the SVG canvas.
 */
const BUILDER = (() => {
  let enabled = false;
  let placedAssets = [];
  let idCounter = 100;

  const ASSET_TYPES = [
    { id: "tank_v1", name: "Tank", icon: "tank" },
    { id: "centrifugal_pump_v1", name: "Pump", icon: "pump" },
    { id: "control_valve_v1", name: "Valve", icon: "valve" },
    { id: "pipe_v1", name: "Pipe", icon: "pipe" },
    { id: "heat_exchanger_v1", name: "Heat Exchanger", icon: "heatExchanger" },
    { id: "fan_v1", name: "Fan", icon: "fan" },
    { id: "compressor_v1", name: "Compressor", icon: "pump" },
    { id: "separator_v1", name: "Separator", icon: "tank" },
    { id: "level_transmitter_v1", name: "Level Tx", icon: "levelTransmitter" },
    { id: "flow_transmitter_v1", name: "Flow Tx", icon: "flowTransmitter" },
    { id: "pressure_transmitter_v1", name: "Press Tx", icon: "pressureTransmitter" },
    { id: "pid_controller_v1", name: "Controller", icon: "controller" },
    { id: "valve_actuator_v1", name: "Actuator", icon: "actuator" },
  ];

  function init() { buildPalette(); }

  function buildPalette() {
    const container = document.getElementById("palette-items");
    if (!container || typeof ICONS === "undefined") { setTimeout(buildPalette, 200); return; }
    container.innerHTML = "";
    for (const asset of ASSET_TYPES) {
      const item = document.createElement("div");
      item.className = "palette-item"; item.draggable = true;
      item.dataset.assetType = asset.id;
      const iconFn = ICONS[asset.icon];
      if (iconFn) {
        const svg = ICONS.el("svg", { width: "28", height: "28", viewBox: "0 0 64 64" });
        svg.appendChild(iconFn({ fill: "transparent", stroke: "#64748b" }));
        item.appendChild(svg);
      }
      const label = document.createElement("span");
      label.textContent = asset.name; item.appendChild(label);
      item.addEventListener("dragstart", (e) => {
        e.dataTransfer.setData("application/vf-asset-type", asset.id);
        e.dataTransfer.setData("application/vf-asset-name", asset.name);
        e.dataTransfer.effectAllowed = "copy"; item.style.opacity = "0.5";
      });
      item.addEventListener("dragend", () => { item.style.opacity = "1"; });
      container.appendChild(item);
    }
    const canvas = document.querySelector(".process-canvas-wrap");
    if (canvas) {
      canvas.addEventListener("dragover", (e) => { if (!enabled) return; e.preventDefault(); e.dataTransfer.dropEffect = "copy"; });
      canvas.addEventListener("drop", (e) => {
        if (!enabled) return; e.preventDefault();
        const type = e.dataTransfer.getData("application/vf-asset-type");
        const name = e.dataTransfer.getData("application/vf-asset-name") || type;
        if (!type) return;
        const svg = document.getElementById("process-svg"); if (!svg) return;
        const r = svg.getBoundingClientRect();
        const sx = 900 / r.width, sy = 520 / r.height;
        const vbx = svg.getAttribute("viewBox") || "0 0 900 520";
        const parts = vbx.split(/[ ,]/).map(Number);
        const vx = parts[0]||0, vy = parts[1]||0, vw = parts[2]||900, vh = parts[3]||520;
        const px = vx + ((e.clientX - r.left) / r.width) * vw;
        const py = vy + ((e.clientY - r.top) / r.height) * vh;
        placeAsset(type, name, Math.max(20, Math.min(vw-20, px)), Math.max(20, Math.min(vh-20, py)));
      });
    }
  }

  function placeAsset(type, name, x, y) {
    const id = "U" + (idCounter++);
    placedAssets.push({ id, type, name, x, y });
    addNodeToSVG(id, type, name, x, y);
    showToast(`+ ${name} (${id})`);
  }

  function addNodeToSVG(id, type, name, x, y) {
    const svg = document.getElementById("process-svg"); if (!svg || typeof ICONS === "undefined") return;
    const NS = "http://www.w3.org/2000/svg";
    const g = document.createElementNS(NS, "g"); g.setAttribute("data-id", id);
    g.setAttribute("class", "eq-node"); g.style.cursor = "pointer";
    const c = { fill: "#e8f4f8", stroke: "#16726a" };
    const NW = 120, NH = 72;
    const r = document.createElementNS(NS, "rect");
    r.setAttribute("x", x); r.setAttribute("y", y); r.setAttribute("width", NW); r.setAttribute("height", NH);
    r.setAttribute("rx", "10"); r.setAttribute("fill", c.fill); r.setAttribute("stroke", c.stroke); r.setAttribute("stroke-width", "2");
    g.appendChild(r);
    const iconEl = ICONS.forModelType(type);
    if (iconEl) {
      const is = document.createElementNS(NS, "svg");
      is.setAttribute("x", x + NW/2 - 18); is.setAttribute("y", y + 4);
      is.setAttribute("width", "36"); is.setAttribute("height", "36"); is.setAttribute("viewBox", "0 0 64 64");
      is.appendChild(iconEl); g.appendChild(is);
    }
    const b = document.createElementNS(NS, "rect");
    b.setAttribute("x", x); b.setAttribute("y", y + NH - 20); b.setAttribute("width", NW); b.setAttribute("height", "20");
    b.setAttribute("fill", c.stroke); g.appendChild(b);
    const l = document.createElementNS(NS, "text");
    l.setAttribute("x", x + NW/2); l.setAttribute("y", y + NH - 6);
    l.setAttribute("text-anchor", "middle"); l.setAttribute("fill", "#fff");
    l.setAttribute("font-size", "11"); l.setAttribute("font-weight", "700");
    l.setAttribute("font-family", "Inter, system-ui, sans-serif");
    l.textContent = id; g.appendChild(l);
    svg.appendChild(g);
  }

  function showToast(msg) {
    const t = document.createElement("div");
    t.style.cssText = "position:fixed;bottom:80px;right:20px;background:#16726a;color:#fff;padding:10px 18px;border-radius:8px;font-size:13px;font-weight:600;z-index:100;box-shadow:0 10px 15px -3px rgba(0,0,0,.08);transition:opacity .4s";
    t.textContent = msg; document.body.appendChild(t);
    setTimeout(() => { t.style.opacity = "0"; setTimeout(() => t.remove(), 400); }, 2000);
  }

  function getPlacedAssets() { return [...placedAssets]; }
  function enable() { enabled = true; document.querySelectorAll(".palette-item").forEach(i => i.draggable = true); const c = document.querySelector(".process-canvas-wrap"); if (c) c.style.cursor = "copy"; }
  function disable() { enabled = false; document.querySelectorAll(".palette-item").forEach(i => i.draggable = false); const c = document.querySelector(".process-canvas-wrap"); if (c) c.style.cursor = ""; }
  setTimeout(init, 500);
  return { init, enable, disable, placeAsset, getPlacedAssets, addNodeToSVG };
})();
