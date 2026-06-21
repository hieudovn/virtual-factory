/* Virtual Factory — Asset Builder (v3)
   Drag-drop + port connections + connection lines + YAML export.
 */
const BUILDER = (() => {
  let enabled = false, connecting = false, connectStart = null, placedAssets = [], connections = [], idCounter = 100;

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

  const PORT_MAP = {
    tank_v1: { inlet: { x: 0, y: 0.5 }, outlet: { x: 1, y: 0.5 } },
    centrifugal_pump_v1: { inlet: { x: 0, y: 0.5 }, outlet: { x: 1, y: 0.5 } },
    control_valve_v1: { inlet: { x: 0, y: 0.5 }, outlet: { x: 1, y: 0.5 } },
    pipe_v1: { inlet: { x: 0, y: 0.5 }, outlet: { x: 1, y: 0.5 } },
    heat_exchanger_v1: { hot_inlet: { x: 0, y: 0.25 }, hot_outlet: { x: 1, y: 0.25 }, cold_inlet: { x: 0, y: 0.75 }, cold_outlet: { x: 1, y: 0.75 } },
    fan_v1: { inlet: { x: 0, y: 0.5 }, outlet: { x: 1, y: 0.5 } },
    compressor_v1: { inlet: { x: 0, y: 0.5 }, outlet: { x: 1, y: 0.5 } },
    separator_v1: { inlet: { x: 0, y: 0.5 }, gas_outlet: { x: 1, y: 0.25 }, liquid_outlet: { x: 1, y: 0.75 } },
    level_transmitter_v1: { input: { x: 0, y: 0.5 }, output: { x: 1, y: 0.5 } },
    flow_transmitter_v1: { input: { x: 0, y: 0.5 }, output: { x: 1, y: 0.5 } },
    pressure_transmitter_v1: { input: { x: 0, y: 0.5 }, output: { x: 1, y: 0.5 } },
    pid_controller_v1: { pv_input: { x: 0, y: 0.5 }, output: { x: 1, y: 0.5 } },
    valve_actuator_v1: { cmd_input: { x: 0, y: 0.5 }, feedback: { x: 1, y: 0.5 } },
  };

  function init() { buildPalette(); }

  function buildPalette() {
    const container = document.getElementById("palette-items");
    if (!container || typeof ICONS === "undefined") { setTimeout(buildPalette, 200); return; }
    container.innerHTML = "";
    for (const asset of ASSET_TYPES) {
      const item = document.createElement("div"); item.className = "palette-item"; item.draggable = true;
      item.dataset.assetType = asset.id;
      const iconFn = ICONS[asset.icon];
      if (iconFn) {
        const svg = ICONS.el("svg", { width: "28", height: "28", viewBox: "0 0 64 64" });
        svg.appendChild(iconFn({ fill: "transparent", stroke: "#64748b" })); item.appendChild(svg);
      }
      const label = document.createElement("span"); label.textContent = asset.name; item.appendChild(label);
      item.addEventListener("dragstart", (e) => { e.dataTransfer.setData("application/vf-asset-type", asset.id); e.dataTransfer.setData("application/vf-asset-name", asset.name); e.dataTransfer.effectAllowed = "copy"; item.style.opacity = "0.5"; });
      item.addEventListener("dragend", () => { item.style.opacity = "1"; });
      container.appendChild(item);
    }
    const canvas = document.querySelector(".process-canvas-wrap");
    if (canvas) {
      canvas.addEventListener("dragover", (e) => { if (!enabled) return; e.preventDefault(); e.dataTransfer.dropEffect = "copy"; });
      canvas.addEventListener("drop", (e) => { if (!enabled) return; e.preventDefault(); const t = e.dataTransfer.getData("application/vf-asset-type"); const n = e.dataTransfer.getData("application/vf-asset-name") || t; if (!t) return; const svg = document.getElementById("process-svg"); if (!svg) return; const r = svg.getBoundingClientRect(); const vbx = svg.getAttribute("viewBox") || "0 0 900 520"; const p = vbx.split(/[ ,]/).map(Number); const px = (p[2]||900)*((e.clientX - r.left)/r.width) + (p[0]||0); const py = (p[3]||520)*((e.clientY - r.top)/r.height) + (p[1]||0); placeAsset(t, n, Math.max(20, Math.min((p[2]||900)-20, px)), Math.max(20, Math.min((p[3]||520)-20, py))); });
    }
  }

  function placeAsset(type, name, x, y) {
    const id = "U" + (idCounter++); placedAssets.push({ id, type, name, x, y }); addNodeToSVG(id, type, name, x, y); showToast("+ " + name + " (" + id + ")");
  }

  function addNodeToSVG(id, type, name, x, y) {
    const svg = document.getElementById("process-svg"); if (!svg || typeof ICONS === "undefined") return;
    const NS = "http://www.w3.org/2000/svg"; const g = document.createElementNS(NS, "g");
    g.setAttribute("data-id", id); g.setAttribute("class", "eq-node"); g.style.cursor = enabled ? "pointer" : "";
    const c = { fill: "#e8f4f8", stroke: "#16726a" }; const NW = 120, NH = 72;
    const r = document.createElementNS(NS, "rect");
    r.setAttribute("x", x); r.setAttribute("y", y); r.setAttribute("width", NW); r.setAttribute("height", NH);
    r.setAttribute("rx", "10"); r.setAttribute("fill", c.fill); r.setAttribute("stroke", c.stroke); r.setAttribute("stroke-width", "2"); g.appendChild(r);
    const iconEl = ICONS.forModelType(type);
    if (iconEl) { const is = document.createElementNS(NS, "svg"); is.setAttribute("x", x + NW/2 - 18); is.setAttribute("y", y + 4); is.setAttribute("width", "36"); is.setAttribute("height", "36"); is.setAttribute("viewBox", "0 0 64 64"); is.appendChild(iconEl); g.appendChild(is); }
    const b = document.createElementNS(NS, "rect"); b.setAttribute("x", x); b.setAttribute("y", y + NH - 20); b.setAttribute("width", NW); b.setAttribute("height", "20"); b.setAttribute("fill", c.stroke); g.appendChild(b);
    const l = document.createElementNS(NS, "text"); l.setAttribute("x", x + NW/2); l.setAttribute("y", y + NH - 6); l.setAttribute("text-anchor", "middle"); l.setAttribute("fill", "#fff"); l.setAttribute("font-size", "11"); l.setAttribute("font-weight", "700"); l.setAttribute("font-family", "Inter, system-ui, sans-serif"); l.textContent = id; g.appendChild(l);
    g.addEventListener("click", (e) => { if (!enabled) return; e.stopPropagation(); showPorts(id); });
    svg.appendChild(g);
  }

  // ---- Port Connection System ----
  function showPorts(nodeId) {
    hidePorts(); const svg = document.getElementById("process-svg"); if (!svg) return;
    const asset = placedAssets.find(a => a.id === nodeId); if (!asset) return;
    const ports = PORT_MAP[asset.type]; if (!ports) return;
    const NW = 120, NH = 72; const NS = "http://www.w3.org/2000/svg";
    for (const [pname, pos] of Object.entries(ports)) {
      const px = asset.x + pos.x * NW, py = asset.y + pos.y * NH;
      const dot = document.createElementNS(NS, "circle");
      dot.setAttribute("cx", px); dot.setAttribute("cy", py); dot.setAttribute("r", "6");
      dot.setAttribute("fill", "#3b82f6"); dot.setAttribute("stroke", "#fff"); dot.setAttribute("stroke-width", "2");
      dot.setAttribute("class", "port-dot"); dot.dataset.nodeId = nodeId; dot.dataset.portName = pname;
      dot.style.cursor = "crosshair";
      dot.addEventListener("click", (e) => { e.stopPropagation(); onPortClick(nodeId, pname, px, py); });
      svg.appendChild(dot);
    }
  }

  function hidePorts() { document.querySelectorAll(".port-dot").forEach(d => d.remove()); }
  function hideTempLine() { document.querySelectorAll(".temp-conn").forEach(e => e.remove()); }

  function onPortClick(nodeId, portName, px, py) {
    if (!connecting) {
      connecting = true; connectStart = { nodeId, portName, x: px, y: py };
      const svg = document.getElementById("process-svg"); if (!svg) return;
      const NS = "http://www.w3.org/2000/svg"; const line = document.createElementNS(NS, "line");
      line.setAttribute("x1", px); line.setAttribute("y1", py); line.setAttribute("x2", px); line.setAttribute("y2", py);
      line.setAttribute("stroke", "#3b82f6"); line.setAttribute("stroke-width", "2"); line.setAttribute("stroke-dasharray", "5 3");
      line.setAttribute("class", "temp-conn"); svg.appendChild(line);
      svg.addEventListener("mousemove", onConnMouseMove);
      showToast("Click another port to connect");
    } else {
      const svg = document.getElementById("process-svg"); if (!svg) return;
      const NS = "http://www.w3.org/2000/svg"; const line = document.createElementNS(NS, "line");
      line.setAttribute("x1", connectStart.x); line.setAttribute("y1", connectStart.y); line.setAttribute("x2", px); line.setAttribute("y2", py);
      line.setAttribute("stroke", "#16726a"); line.setAttribute("stroke-width", "2.5"); line.setAttribute("stroke-dasharray", "6 3"); svg.appendChild(line);
      const conn = { id: idCounter++, from: connectStart.nodeId, fromPort: connectStart.portName, to: nodeId, toPort: portName };
      connections.push(conn); showToast("Connected " + connectStart.nodeId + " → " + nodeId);
      hidePorts(); hideTempLine(); connecting = false; connectStart = null;
      svg.removeEventListener("mousemove", onConnMouseMove);
    }
  }

  function onConnMouseMove(e) {
    const svg = document.getElementById("process-svg"); if (!svg) return;
    const r = svg.getBoundingClientRect(); const vbx = svg.getAttribute("viewBox") || "0 0 900 520";
    const p = vbx.split(/[ ,]/).map(Number); const mx = (p[2]||900)*((e.clientX - r.left)/r.width) + (p[0]||0); const my = (p[3]||520)*((e.clientY - r.top)/r.height) + (p[1]||0);
    const line = document.querySelector(".temp-conn"); if (line) { line.setAttribute("x2", mx); line.setAttribute("y2", my); }
  }

  // ---- Export ----
  function exportYAML() {
    let y = "plant:\n  id: custom_plant\n  name: Custom Plant\n  type: continuous_process\n\nmedium:\n  id: water\n  density_kg_m3: 997.0\n  viscosity_pa_s: 0.00089\n  specific_heat_j_kg_k: 4182.0\n\nequipment:\n";
    for (const a of placedAssets) { y += "  - id: " + a.id + "\n    model_type: " + a.type + "\n    display_name: " + a.name + "\n    parameters: {}\n"; }
    y += "\nconnections:\n";
    for (let i = 0; i < connections.length; i++) { const c = connections[i]; y += "  - id: C" + String(i+1).padStart(3,"0") + "\n    type: physical\n    from: " + c.from + "." + c.fromPort + "\n    to: " + c.to + "." + c.toPort + "\n    medium: water\n"; }
    const blob = new Blob([y], {type:"text/yaml"}); const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = "plant_config.yaml"; a.click();
    URL.revokeObjectURL(url); showToast("Exported " + placedAssets.length + " assets, " + connections.length + " connections");
  }

  function showToast(msg) {
    const t = document.createElement("div"); t.style.cssText = "position:fixed;bottom:80px;right:20px;background:#16726a;color:#fff;padding:10px 18px;border-radius:8px;font-size:13px;font-weight:600;z-index:100;box-shadow:0 10px 15px -3px rgba(0,0,0,.08);transition:opacity .4s";
    t.textContent = msg; document.body.appendChild(t); setTimeout(() => { t.style.opacity = "0"; setTimeout(() => t.remove(), 400); }, 2000);
  }

  function getPlacedAssets() { return [...placedAssets]; }
  function getConnections() { return [...connections]; }

  function enable() {
    enabled = true;
    document.querySelectorAll(".palette-item").forEach(i => i.draggable = true);
    document.querySelectorAll(".eq-node").forEach(n => n.style.cursor = "pointer");
    const c = document.querySelector(".process-canvas-wrap"); if (c) c.style.cursor = "copy";
    // Export button
    if (!document.getElementById("builder-export-btn")) {
      const btn = document.createElement("button"); btn.id = "builder-export-btn"; btn.className = "toolbar-btn";
      btn.textContent = "⬇ Export YAML"; btn.addEventListener("click", exportYAML);
      document.querySelector(".process-toolbar")?.appendChild(btn);
    }
  }

  function disable() {
    enabled = false; connecting = false; connectStart = null;
    hidePorts(); hideTempLine();
    document.querySelectorAll(".palette-item").forEach(i => i.draggable = false);
    document.querySelectorAll(".eq-node").forEach(n => n.style.cursor = "");
    const c = document.querySelector(".process-canvas-wrap"); if (c) c.style.cursor = "";
    const btn = document.getElementById("builder-export-btn"); if (btn) btn.remove();
    const svg = document.getElementById("process-svg"); if (svg) svg.removeEventListener("mousemove", onConnMouseMove);
  }

  setTimeout(init, 500);
  return { init, enable, disable, placeAsset, getPlacedAssets, getConnections, addNodeToSVG, exportYAML };
})();
