/* Virtual Factory — SVG Process Flow Editor (v2)

   Renders the plant graph as an interactive SVG diagram with live
   telemetry values overlaid on equipment nodes.

   Interactions:
   - Scroll-wheel zoom centred on cursor
   - Drag empty space to pan
   - Drag nodes to reposition (only when simulation stopped)
   - Click nodes to inspect
 */

const EDITOR = (() => {
  const NS = "http://www.w3.org/2000/svg";

  // ---- Layout constants -------------------------------------------
  const NODE_W = 120, NODE_H = 72;
  const INSTR_W = 100, INSTR_H = 56;
  const SENSOR_R = 28;
  const FONT = "13px Inter, system-ui, sans-serif";

  // ---- Colour map for alarm states ---------------------------------
  const ALARM_COLOURS = { true: "#b42318", false: "#0f7a43", undefined: "#667474" };
  const CATEGORY_COLOURS = {
    equipment:    { fill: "#e8f4f8", stroke: "#16726a", text: "#13201f" },
    sensors:      { fill: "#fff8e1", stroke: "#b45309", text: "#13201f" },
    controllers:  { fill: "#f3e8ff", stroke: "#7c3aed", text: "#13201f" },
    actuators:    { fill: "#fce4ec", stroke: "#c2185b", text: "#13201f" },
  };

  // ---- Interaction state -------------------------------------------
  let svg = null;
  let graphData = null;
  let telemetry = new Map();
  let alarms = new Map();

  // Viewport
  let viewX = 0, viewY = 0, viewW = 900, viewH = 520;

  // Pan state
  let panning = false, panSX = 0, panSY = 0, panVX = 0, panVY = 0;

  // Node drag state (only when stopped)
  let draggingNode = null, dragDX = 0, dragDY = 0, dragHasMoved = false;
  const DRAG_THRESH = 3;

  // ---- Public API --------------------------------------------------

  function init(svgEl) {
    svg = svgEl;
    viewX = 0; viewY = 0; viewW = 900; viewH = 520;
    _applyView();

    // Scroll-wheel zoom
    svg.addEventListener("wheel", _onWheel, { passive: false });

    // Pan via mousedown on the wrapping container
    const wrap = svg.closest(".process-canvas-wrap");
    if (wrap) {
      wrap.addEventListener("mousedown", _onPanStart);
      window.addEventListener("mousemove", _onPanMove);
      window.addEventListener("mouseup", _onPanEnd);
    }

    // Node drag (delegated on SVG, only when stopped)
    svg.addEventListener("mousedown", _onNodeDragStart);
    window.addEventListener("mousemove", _onNodeDragMove);
    window.addEventListener("mouseup", _onNodeDragEnd);

    // Prevent browser drag behaviour on the SVG
    svg.addEventListener("dragstart", e => e.preventDefault());
  }

  function _applyView() {
    if (!svg) return;
    svg.setAttribute("viewBox", `${viewX} ${viewY} ${viewW} ${viewH}`);
  }

  function _isRunning() {
    const el = document.getElementById("runtime-state");
    return el && el.textContent.includes("▶");
  }

  // ---- Wheel zoom ---------------------------------------------------

  function _onWheel(e) {
    e.preventDefault();
    if (!svg) return;
    // Cursor position in SVG client coordinates
    const rect = svg.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    // Map to viewBox coordinates
    const svgX = viewX + (mx / rect.width) * viewW;
    const svgY = viewY + (my / rect.height) * viewH;
    // Zoom factor
    const factor = e.deltaY < 0 ? 0.9 : 1.1;
    const newW = viewW * factor;
    const newH = viewH * factor;
    // Clamp zoom
    const clampedW = Math.max(120, Math.min(4000, newW));
    const clampedH = Math.max(70, Math.min(2400, newH));
    const actualFactor = clampedW / viewW;
    // Zoom toward cursor
    viewX = svgX - (svgX - viewX) * actualFactor;
    viewY = svgY - (svgY - viewY) * actualFactor;
    viewW = clampedW;
    viewH = clampedH;
    _applyView();
  }

  // ---- Pan (drag empty space) ---------------------------------------

  function _onPanStart(e) {
    // Only pan on left button, not on nodes
    if (e.button !== 0) return;
    const target = e.target.closest("[data-id]");
    if (target) return; // let node drag/click handle it
    panning = true;
    panSX = e.clientX;
    panSY = e.clientY;
    panVX = viewX;
    panVY = viewY;
    svg.style.cursor = "grabbing";
    e.preventDefault();
  }

  function _onPanMove(e) {
    if (!panning) return;
    const dx = e.clientX - panSX;
    const dy = e.clientY - panSY;
    const rect = svg.getBoundingClientRect();
    const scaleX = viewW / rect.width;
    const scaleY = viewH / rect.height;
    viewX = panVX - dx * scaleX;
    viewY = panVY - dy * scaleY;
    _applyView();
  }

  function _onPanEnd(e) {
    if (!panning) return;
    panning = false;
    svg.style.cursor = "";
  }

  // ---- Node drag (only when stopped) --------------------------------

  function _onNodeDragStart(e) {
    if (e.button !== 0) return;
    const target = e.target.closest("[data-id]");
    if (!target) return;

    const nodeId = target.getAttribute("data-id");
    const node = graphData && graphData.nodes.find(n => n.id === nodeId);
    if (!node || !node.position) return;

    draggingNode = node;
    dragDX = 0;
    dragDY = 0;
    dragHasMoved = false;
    e.stopPropagation();
    e.preventDefault();
  }

  function _onNodeDragMove(e) {
    if (!draggingNode) return;
    if (_isRunning()) return; // no reposition while running
    const rect = svg.getBoundingClientRect();
    const scaleX = viewW / rect.width;
    const scaleY = viewH / rect.height;
    dragDX += e.movementX * scaleX;
    dragDY += e.movementY * scaleY;
    if (Math.abs(dragDX) > DRAG_THRESH || Math.abs(dragDY) > DRAG_THRESH) {
      dragHasMoved = true;
    }
    const g = svg.querySelector(`[data-id="${draggingNode.id}"]`);
    if (g) {
      g.setAttribute("transform", `translate(${dragDX},${dragDY})`);
    }
  }

  function _onNodeDragEnd(e) {
    if (!draggingNode) return;
    const node = draggingNode;
    // Commit position change to graphData
    if (dragHasMoved) {
      node.position.x += dragDX;
      node.position.y += dragDY;
      render(); // re-render with final position
    } else {
      // It was a click – show inspector
      // Reset any tiny transform
      const g = svg.querySelector(`[data-id="${node.id}"]`);
      if (g) g.removeAttribute("transform");
      showPropertyPanel(node);
    }
    draggingNode = null;
    dragDX = 0;
    dragDY = 0;
    dragHasMoved = false;
  }

  async function loadGraph() {
    const resp = await fetch("/api/plant-graph");
    graphData = await resp.json();
    if (graphData) render();
  }

  function updateTelemetry(frame) {
    if (!Array.isArray(frame)) return;
    for (const s of frame) {
      if (s && s.category !== "internal_truth") {
        telemetry.set(s.name, s);
        if (s.category === "industrial_event") alarms.set(s.name, s);
      }
    }
    if (graphData) render();
  }

  function render() {
    if (!svg || !graphData) return;
    svg.replaceChildren();

    // Background grid
    drawGrid();

    // Edge labels (sensor measuring path, etc.)
    for (const edge of graphData.edges) {
      if (edge.category === "measurement") drawMeasurementEdge(edge);
      if (edge.category === "control") drawControlEdge(edge);
      if (edge.category === "actuation") drawActuationEdge(edge);
    }

    // Physical connections (equipment → equipment)
    drawPhysicalEdges();

    // Nodes
    for (const node of graphData.nodes) {
      if (node.category === "equipment") drawEquipmentNode(node);
      if (node.category === "sensors") drawSensorNode(node);
      if (node.category === "controllers") drawControllerNode(node);
      if (node.category === "actuators") drawActuatorNode(node);
    }
  }

  // ---- Drawing helpers ---------------------------------------------

  function drawGrid() {
    const grid = el("g", { opacity: "0.06" });
    for (let x = 40; x < 900; x += 40) {
      grid.appendChild(el("line", { x1: x, y1: 0, x2: x, y2: 520, stroke: "#16726a", "stroke-width": "1" }));
    }
    for (let y = 40; y < 520; y += 40) {
      grid.appendChild(el("line", { x1: 0, y1: y, x2: 900, y2: y, stroke: "#16726a", "stroke-width": "1" }));
    }
    svg.appendChild(grid);
  }

  function drawPhysicalEdges() {
    const eqNodes = graphData.nodes.filter(n => n.category === "equipment");
    const physicalEdges = graphData.edges.filter(e => e.category === "physical");
    for (const edge of physicalEdges) {
      const from = eqNodes.find(n => n.id === extractId(edge.source));
      const to = eqNodes.find(n => n.id === extractId(edge.target));
      if (!from || !to) continue;

      const p = from.position, q = to.position;
      const x1 = p.x + NODE_W, y1 = p.y + NODE_H / 2;
      const x2 = q.x, y2 = q.y + NODE_H / 2;

      // Arrow line
      const g = el("g", {});
      const line = el("line", { x1, y1, x2, y2, stroke: "#16726a", "stroke-width": "2.5", "stroke-dasharray": "6 3" });
      g.appendChild(line);

      // Arrowhead
      const mx = (x1 + x2) / 2, my = (y1 + y2) / 2;
      const arrow = el("polygon", {
        points: `${mx},${my-5} ${mx+8},${my} ${mx},${my+5}`,
        fill: "#16726a",
      });
      g.appendChild(arrow);
      svg.appendChild(g);
    }
  }

  function drawMeasurementEdge(edge) {
    const sensNode = graphData.nodes.find(n => n.id === extractId(edge.source));
    if (!sensNode) return;
    const p = sensNode.position;

    const g = el("g", { opacity: "0.55" });
    const path = el("path", {
      d: `M${p.x + SENSOR_R} ${p.y} Q${p.x + 30} ${p.y - 35} ${p.x + SENSOR_R} ${p.y - 50}`,
      stroke: "#b45309", "stroke-width": "1.5", fill: "none", "stroke-dasharray": "3 3",
    });
    g.appendChild(path);
    g.appendChild(el("text", {
      x: p.x + SENSOR_R + 4, y: p.y - 42, fill: "#b45309", "font-size": "9", "font-family": FONT,
    }, "measure"));
    svg.appendChild(g);
  }

  function drawControlEdge(edge) {
    const ctrlNode = graphData.nodes.find(n => n.id === extractId(edge.source));
    if (!ctrlNode) return;
    const p = ctrlNode.position;

    const g = el("g", { opacity: "0.5" });
    const line = el("line", {
      x1: p.x + INSTR_W / 2, y1: p.y + INSTR_H,
      x2: p.x + INSTR_W / 2, y2: p.y + INSTR_H + 30,
      stroke: "#7c3aed", "stroke-width": "1.5", "stroke-dasharray": "4 3",
    });
    g.appendChild(line);
    g.appendChild(el("text", {
      x: p.x + INSTR_W / 2 + 4, y: p.y + INSTR_H + 24,
      fill: "#7c3aed", "font-size": "9",
    }, edge.target));  // show output signal name
    svg.appendChild(g);
  }

  function drawActuationEdge(edge) {
    const actNode = graphData.nodes.find(n => n.id === extractId(edge.source));
    if (!actNode) return;
    const p = actNode.position;

    const g = el("g", { opacity: "0.5" });
    const line = el("line", {
      x1: p.x + INSTR_W / 2, y1: p.y,
      x2: p.x + INSTR_W / 2, y2: p.y - 25,
      stroke: "#c2185b", "stroke-width": "1.5", "stroke-dasharray": "4 3",
    });
    g.appendChild(line);
    svg.appendChild(g);
  }

  function drawEquipmentNode(node) {
    const p = node.position;
    const colours = CATEGORY_COLOURS.equipment;
    const x = p.x, y = p.y;

    const g = el("g", { "data-id": node.id, class: "eq-node", style: "cursor:" + (_isRunning()?"default":"grab") });
    // Click handled by _onNodeDragEnd; no separate listener needed

    // Background rounded rect
    g.appendChild(el("rect", {
      x, y, width: NODE_W, height: NODE_H, rx: "10",
      fill: colours.fill, stroke: colours.stroke, "stroke-width": "2",
    }));

    // Equipment icon from ICONS library
    const iconSize = 36;
    const iconX = x + NODE_W/2 - iconSize/2;
    const iconY = y + 4;

    if (typeof ICONS !== "undefined" && node.model_type) {
      const iconSvg = el("svg", {
        x: iconX, y: iconY, width: iconSize, height: iconSize,
        viewBox: "0 0 64 64",
      });
      const iconEl = ICONS.forModelType(node.model_type);
      if (iconEl) iconSvg.appendChild(iconEl);
      g.appendChild(iconSvg);
    }

    // ID badge at bottom
    g.appendChild(el("rect", {
      x: x, y: y + NODE_H - 20, width: NODE_W, height: 20,
      fill: colours.stroke, rx: "0",
    }));
    g.appendChild(el("text", {
      x: x + NODE_W/2, y: y + NODE_H - 6, "text-anchor": "middle",
      fill: "#fff", "font-size": "12", "font-weight": "700", "font-family": FONT,
    }, node.id));

    // Live value badge
    const liveValue = findLiveValue(node.id);
    if (liveValue !== null) {
      g.appendChild(el("rect", {
        x: x + 4, y: y + 4, width: NODE_W - 8, height: 16, rx: "4",
        fill: "rgba(255,255,255,0.85)",
      }));
      g.appendChild(el("text", {
        x: x + NODE_W/2, y: y + 16, "text-anchor": "middle",
        fill: colours.stroke, "font-size": "10", "font-weight": "700", "font-family": "monospace",
      }, formatVal(liveValue.value) + (liveValue.unit ? " " + liveValue.unit : "")));
    }

    // Alarm indicator
    const hasAlarm = hasActiveAlarm(node.id);
    g.appendChild(el("circle", {
      cx: x + NODE_W - 12, cy: y + 12, r: "6",
      fill: ALARM_COLOURS[hasAlarm], stroke: "#fff", "stroke-width": "2",
    }));

    svg.appendChild(g);
  }

  function drawSensorNode(node) {
    const p = node.position;
    const colours = CATEGORY_COLOURS.sensors;
    const cx = p.x + SENSOR_R, cy = p.y;

    const g = el("g", { "data-id": node.id, class: "eq-node", style: "cursor:" + (_isRunning()?"default":"grab") });

    g.appendChild(el("circle", {
      cx, cy, r: SENSOR_R, fill: colours.fill, stroke: colours.stroke, "stroke-width": "2",
    }));

    g.appendChild(el("text", {
      x: cx, y: cy - 4, "text-anchor": "middle",
      fill: colours.text, "font-size": "11", "font-weight": "600", "font-family": FONT,
    }, node.id));

    g.appendChild(el("text", {
      x: cx, y: cy + 14, "text-anchor": "middle",
      fill: colours.stroke, "font-size": "9", "font-family": "monospace",
    }, _sensorValue(node)));

    svg.appendChild(g);
  }

  function drawControllerNode(node) {
    const p = node.position;
    const colours = CATEGORY_COLOURS.controllers;
    const x = p.x, y = p.y;

    const g = el("g", { "data-id": node.id, class: "eq-node", style: "cursor:" + (_isRunning()?"default":"grab") });

    g.appendChild(el("rect", {
      x, y, width: INSTR_W, height: INSTR_H, rx: "6",
      fill: colours.fill, stroke: colours.stroke, "stroke-width": "2",
    }));

    g.appendChild(el("text", {
      x: x + INSTR_W / 2, y: y + 18, "text-anchor": "middle",
      fill: colours.text, "font-size": "12", "font-weight": "600", "font-family": FONT,
    }, node.id));

    g.appendChild(el("text", {
      x: x + INSTR_W / 2, y: y + 36, "text-anchor": "middle",
      fill: "#667474", "font-size": "10", "font-family": FONT,
    }, node.display_name));

    // Controller/actuator output value (find telemetry signal whose source matches this node)
    const liveVal = _sensorNodeSignal(node);
    if (liveVal) {
      g.appendChild(el("text", {
        x: x + INSTR_W / 2, y: y + 52, "text-anchor": "middle",
        fill: "#7c3aed", "font-size": "11", "font-weight": "700", "font-family": "monospace",
      }, formatVal(liveVal.value) + (liveVal.unit ? " " + liveVal.unit : "")));
    }

    svg.appendChild(g);
  }

  function drawActuatorNode(node) {
    const p = node.position;
    const colours = CATEGORY_COLOURS.actuators;
    const x = p.x, y = p.y;

    const g = el("g", { "data-id": node.id, class: "eq-node", style: "cursor:" + (_isRunning()?"default":"grab") });

    g.appendChild(el("rect", {
      x, y, width: INSTR_W, height: INSTR_H, rx: "6",
      fill: colours.fill, stroke: colours.stroke, "stroke-width": "2",
    }));

    g.appendChild(el("text", {
      x: x + INSTR_W / 2, y: y + 18, "text-anchor": "middle",
      fill: colours.text, "font-size": "12", "font-weight": "600", "font-family": FONT,
    }, node.id));

    g.appendChild(el("text", {
      x: x + INSTR_W / 2, y: y + 36, "text-anchor": "middle",
      fill: "#667474", "font-size": "10", "font-family": FONT,
    }, node.display_name));

    // Feedback value
    const fbSignal = _sensorNodeSignal(node);
    if (fbSignal) {
      g.appendChild(el("text", {
        x: x + INSTR_W / 2, y: y + 52, "text-anchor": "middle",
        fill: "#c2185b", "font-size": "11", "font-weight": "700", "font-family": "monospace",
      }, formatVal(fbSignal.value) + "%"));
    }

    svg.appendChild(g);
  }

  // ---- Live data lookup ---------------------------------------------

  function findLiveValue(equipmentId) {
    // Generic: search all telemetry signals for a value to display on this equipment node.
    // Priority order:
    //   1. Signals named exactly like equipment (rare)
    //   2. Industrial signals whose name starts with the equipment ID
    //   3. Equipment truth signals (e.g. COMP01.power_consumed_kw)
    //   4. Any signal containing the equipment ID

    // Priority 2: industrial signals named after the equipment
    for (const [name, s] of telemetry) {
      if (s.category === "industrial_signal" && name.startsWith(equipmentId + "_")) {
        return { value: s.value, unit: s.unit };
      }
    }

    // Priority 3: equipment truth values (calculated category, prefixed with equipment ID)
    const preferredTruth = ["power_consumed_kw", "discharge_pressure_kpa",
      "pressure_kpa", "flow_m3_s", "level_true", "volume_true"];
    for (const key of preferredTruth) {
      const s = telemetry.get(`${equipmentId}.${key}`);
      if (s && s.value !== null && s.value !== undefined) {
        return { value: s.value, unit: s.unit };
      }
    }

    // Priority 4: any truth variable for this equipment
    for (const [name, s] of telemetry) {
      if (name.startsWith(equipmentId + ".")) {
        return { value: s.value, unit: s.unit };
      }
    }

    // Priority 5: any signal containing the equipment ID
    for (const [name, s] of telemetry) {
      if (name.includes(equipmentId)) {
        return { value: s.value, unit: s.unit };
      }
    }

    return null;
  }

  function findLiveSignal(name, defaultValue) {
    return telemetry.get(name) || defaultValue;
  }

  function _sensorNodeSignal(node) {
    // Find telemetry signal whose source field matches this sensor node ID
    for (const [name, s] of telemetry) {
      if (s.source === node.id) return s;
    }
    return null;
  }

  function _sensorValue(node) {
    const s = _sensorNodeSignal(node);
    if (s && s.value !== null && s.value !== undefined) {
      return formatVal(s.value) + (s.unit ? " " + s.unit : "");
    }
    return "Tx";
  }

  function hasActiveAlarm(equipmentId) {
    // Generic: check all alarms for any that mention this equipment
    for (const [name, a] of alarms) {
      if (name.includes(equipmentId) && a.value === true) {
        return true;
      }
    }
    return false;
  }

  // ---- SVG helpers --------------------------------------------------

  function el(tag, attrs, text) {
    const e = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      e.setAttribute(k, v);
    }
    if (text !== undefined) e.textContent = text;
    return e;
  }

  function extractId(endpoint) {
    return (endpoint || "").split(".")[0];
  }

  function truncate(s, max) {
    return (s || "").length > max ? s.slice(0, max - 1) + "…" : (s || "");
  }

  function formatVal(v) {
    if (typeof v === "number") return v.toFixed(1);
    if (typeof v === "boolean") return v ? "ACTIVE" : "CLEAR";
    return String(v);
  }

  // ---- Property Inspector --------------------------------------------

  function showPropertyPanel(node) {
    const body = document.getElementById("property-body");
    if (!body) return;

    // Highlight
    svg.querySelectorAll(".eq-node.selected").forEach(el => el.classList.remove("selected"));
    const sel = svg.querySelector(`[data-id="${node.id}"]`);
    if (sel) sel.classList.add("selected");

    const modelType = node.model_type || "unknown";
    const category = node.category || "equipment";
    const liveVal = findLiveValue(node.id);
    const hasAlarm = hasActiveAlarm(node.id);
    const relatedSignals = findRelatedSignals(node.id);

    let html = `<div style="margin-bottom:10px">
      <h3 style="font-size:15px;font-weight:700;margin-bottom:2px">${node.id}</h3>
      <p style="font-size:10px;color:var(--ink-muted)">${node.display_name||""} · ${modelType}</p>
      </div>
      <div style="display:grid;gap:4px;font-size:11px;margin-bottom:8px">
      <div style="display:flex;justify-content:space-between"><span style="color:var(--ink-muted)">Category</span><span style="font-weight:600">${category}</span></div>
      <div style="display:flex;justify-content:space-between"><span style="color:var(--ink-muted)">Status</span><span style="font-weight:600;color:${hasAlarm?'var(--danger)':'var(--success)'}">${hasAlarm?'⚠ Active Alarm':'✓ Normal'}</span></div>`;

    if (liveVal) {
      html += `<div style="display:flex;justify-content:space-between"><span style="color:var(--ink-muted)">Live Value</span><span style="font-weight:700;font-size:14px;color:var(--accent)">${formatVal(liveVal.value)} ${liveVal.unit||""}</span></div>`;
    }
    html += `</div>`;

    // --- PID Controller specific controls ---
    if (category === "controllers" || modelType.includes("pid")) {
      html += `<hr style="border:none;border-top:1px solid var(--border-panel);margin:8px 0">
        <h4 style="font-size:11px;font-weight:700;margin-bottom:8px;color:var(--accent)">🎛️ PID Tuning</h4>
        <div class="pid-inline-controls" id="pid-inline-${node.id}">
          <div style="display:flex;flex-direction:column;gap:6px">
            <div style="display:flex;align-items:center;gap:8px">
              <label style="font-size:10px;color:var(--ink-muted);width:20px">SP</label>
              <input type="range" min="0" max="5" step="0.1" value="2.5" style="flex:1;height:4px" oninput="document.getElementById('pid-sp-val-${node.id}').textContent=this.value">
              <span style="font-size:11px;font-weight:700;min-width:36px;text-align:right" id="pid-sp-val-${node.id}">2.5</span><span style="font-size:9px;color:var(--ink-muted)">m</span>
            </div>
            <div style="display:flex;align-items:center;gap:8px">
              <label style="font-size:10px;color:var(--ink-muted);width:20px">Kp</label>
              <input type="range" min="0" max="20" step="0.1" value="1.0" style="flex:1;height:4px" oninput="document.getElementById('pid-kp-val-${node.id}').textContent=this.value">
              <span style="font-size:11px;font-weight:700;min-width:36px;text-align:right" id="pid-kp-val-${node.id}">1.0</span>
            </div>
            <div style="display:flex;align-items:center;gap:8px">
              <label style="font-size:10px;color:var(--ink-muted);width:20px">Ki</label>
              <input type="range" min="0" max="5" step="0.01" value="0.1" style="flex:1;height:4px" oninput="document.getElementById('pid-ki-val-${node.id}').textContent=this.value">
              <span style="font-size:11px;font-weight:700;min-width:36px;text-align:right" id="pid-ki-val-${node.id}">0.10</span>
            </div>
            <div style="display:flex;align-items:center;gap:8px">
              <label style="font-size:10px;color:var(--ink-muted);width:20px">Kd</label>
              <input type="range" min="0" max="5" step="0.01" value="0.0" style="flex:1;height:4px" oninput="document.getElementById('pid-kd-val-${node.id}').textContent=this.value">
              <span style="font-size:11px;font-weight:700;min-width:36px;text-align:right" id="pid-kd-val-${node.id}">0.00</span>
            </div>
          </div>
          <button class="topbar-btn primary" style="margin-top:8px;width:100%;font-size:10px"
            onclick="EDITOR.applyPidSettings('${node.id}')">💾 Apply PID Changes</button>
        </div>`;
    }

    // --- Sensor specific info ---
    if (category === "sensors") {
      html += `<hr style="border:none;border-top:1px solid var(--border-panel);margin:8px 0">
        <h4 style="font-size:11px;font-weight:700;margin-bottom:6px;color:var(--accent)">📡 Sensor Info</h4>
        <div style="font-size:10px;color:var(--ink-muted)">
          <div style="display:flex;justify-content:space-between;padding:2px 0"><span>Measured Signal</span><span style="font-weight:600">${relatedSignals[0]?.name||"N/A"}</span></div>
          <div style="display:flex;justify-content:space-between;padding:2px 0"><span>Quality</span><span style="font-weight:600;color:${liveVal?.quality==='GOOD'?'var(--success)':'var(--warning)'}">${liveVal?.quality||"N/A"}</span></div>
        </div>`;
    }

    // Related signals
    if (relatedSignals.length) {
      html += `<hr style="border:none;border-top:1px solid var(--border-panel);margin:8px 0"><h4 style="font-size:11px;font-weight:600;margin-bottom:4px;color:var(--ink-muted)">Related Signals</h4>`;
      for (const s of relatedSignals) {
        html += `<div style="display:flex;justify-content:space-between;padding:2px 0;font-size:10px"><span>${s.name}</span><span style="font-weight:600">${typeof s.value==='number'?s.value.toFixed(3):s.value} ${s.unit||""}</span></div>`;
      }
    }

    body.innerHTML = html;
  }

  // Called by inline PID Apply button
  async function applyPidSettings(controllerId) {
    const spEl = document.getElementById(`pid-sp-val-${controllerId}`);
    const kpEl = document.getElementById(`pid-kp-val-${controllerId}`);
    const kiEl = document.getElementById(`pid-ki-val-${controllerId}`);
    const kdEl = document.getElementById(`pid-kd-val-${controllerId}`);
    const params = {};
    if (spEl) params.setpoint = parseFloat(spEl.textContent);
    if (kpEl) params.kp = parseFloat(kpEl.textContent);
    if (kiEl) params.ki = parseFloat(kiEl.textContent);
    if (kdEl) params.kd = parseFloat(kdEl.textContent);
    try {
      await fetch(`/api/pid/${controllerId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params),
      });
      // Flash feedback
      const btn = document.querySelector(`#pid-inline-${controllerId} button`);
      if (btn) { btn.textContent = "✅ Applied!"; btn.style.background = "var(--success)"; setTimeout(()=>{btn.textContent="💾 Apply PID Changes";btn.style.background=""},1500); }
    } catch (e) { console.warn("PID apply failed:", e); }
  }

  function findRelatedSignals(equipmentId) {
    // Map equipment to related signal names
    const map = {
      "T102": ["LT102_LEVEL"],
      "V101": ["FT101_FLOW", "V101_OPENING_FEEDBACK"],
      "P101": ["PT101_PRESSURE"],
      "LIC102": ["LIC102_OUT"],
    };
    const names = map[equipmentId] || [];
    const signals = [];
    for (const name of names) {
      // Try APP.telemetry first, then EDITOR's local telemetry
      const s = (typeof APP!=="undefined"&&APP.telemetry.get(name)) || telemetry.get(name);
      if (s) signals.push(s);
    }
    return signals;
  }

  return { init, loadGraph, updateTelemetry, render, showPropertyPanel, applyPidSettings,
    zoomIn: () => _zoomAtCenter(1/1.2),
    zoomOut: () => _zoomAtCenter(1.2),
    fit: () => { viewX=0; viewY=0; viewW=900; viewH=520; _applyView(); },
    resetView: () => { viewX=0; viewY=0; viewW=900; viewH=520; _applyView(); },
  };

  function _zoomAtCenter(factor) {
    const newW = viewW * factor;
    const newH = viewH * factor;
    if (newW < 120 || newW > 4000) return;
    const cx = viewX + viewW/2, cy = viewY + viewH/2;
    viewX = cx - newW/2;
    viewY = cy - newH/2;
    viewW = newW;
    viewH = newH;
    _applyView();
  }
})();
