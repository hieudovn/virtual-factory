/* Virtual Factory — SVG Process Flow Editor

   Renders the plant graph as an interactive SVG diagram with live
   telemetry values overlaid on equipment nodes.
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

  // ---- State -------------------------------------------------------
  let svg = null;
  let graphData = null;
  let telemetry = new Map();
  let alarms = new Map();

  // ---- Public API --------------------------------------------------

  function init(svgEl) {
    svg = svgEl;
    svg.setAttribute("viewBox", "0 0 900 520");
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

    const g = el("g", { "data-id": node.id, class: "eq-node", style: "cursor:pointer" });

    // Click to select → show in property panel
    g.addEventListener("click", (e) => { e.stopPropagation(); showPropertyPanel(node); });

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

    const g = el("g", { "data-id": node.id });

    g.appendChild(el("circle", {
      cx, cy, r: SENSOR_R, fill: colours.fill, stroke: colours.stroke, "stroke-width": "2",
    }));

    g.appendChild(el("text", {
      x: cx, y: cy - 4, "text-anchor": "middle",
      fill: colours.text, "font-size": "11", "font-weight": "600", "font-family": FONT,
    }, node.id));

    g.appendChild(el("text", {
      x: cx, y: cy + 14, "text-anchor": "middle",
      fill: "#667474", "font-size": "9", "font-family": FONT,
    }, "Tx"));

    svg.appendChild(g);
  }

  function drawControllerNode(node) {
    const p = node.position;
    const colours = CATEGORY_COLOURS.controllers;
    const x = p.x, y = p.y;

    const g = el("g", { "data-id": node.id });

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

    // Controller output value
    const liveVal = findLiveSignal(node.id + "_OUT", null);
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

    const g = el("g", { "data-id": node.id });

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
    const fbSignal = findLiveSignal("V101_OPENING_FEEDBACK", null);
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
    // Map equipment to its sensor signals
    const map = {
      "T102": "LT102_LEVEL",
      "V101": "FT101_FLOW",
      "P101": "PT101_PRESSURE",
    };
    const signalName = map[equipmentId];
    if (!signalName) return null;
    const s = telemetry.get(signalName);
    if (!s) return null;
    return { value: s.value, unit: s.unit };
  }

  function findLiveSignal(name, defaultValue) {
    return telemetry.get(name) || defaultValue;
  }

  function hasActiveAlarm(equipmentId) {
    // Check if any alarm about this equipment is active
    const alarmPrefixes = {
      "T102": ["T102_LOW_LEVEL_ALARM", "T102_HIGH_LEVEL_ALARM"],
      "P101": ["P101_NO_FLOW_ALARM"],
      "V101": ["V101_POSITION_DEVIATION_ALARM"],
    };
    const names = alarmPrefixes[equipmentId] || [];
    for (const name of names) {
      const a = alarms.get(name);
      if (a && a.value === true) return true;
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

    // Get live telemetry signals for this equipment
    const relatedSignals = findRelatedSignals(node.id);

    let html = `<div style="margin-bottom:14px">
      <h3 style="font-size:16px;font-weight:700">${node.id}</h3>
      <p style="font-size:11px;color:var(--ink-muted)">${node.display_name||""} · ${modelType}</p>
      </div>
      <div style="display:grid;gap:6px;font-size:12px;margin-bottom:10px">
      <div style="display:flex;justify-content:space-between"><span style="color:var(--ink-muted)">Category</span><span style="font-weight:600">${category}</span></div>
      <div style="display:flex;justify-content:space-between"><span style="color:var(--ink-muted)">Alarm</span><span style="font-weight:600;color:${hasAlarm?'var(--danger)':'var(--success)'}">${hasAlarm?'⚠ Active':'✓ Clear'}</span></div>`;

    if (liveVal) {
      html += `<div style="display:flex;justify-content:space-between"><span style="color:var(--ink-muted)">Live Value</span><span style="font-weight:700;font-size:15px;color:var(--accent)">${formatVal(liveVal.value)} ${liveVal.unit||""}</span></div>`;
    }
    html += `</div>`;

    // Related signals
    if (relatedSignals.length) {
      html += `<hr style="border:none;border-top:1px solid var(--border-panel);margin:8px 0"><h4 style="font-size:11px;font-weight:600;margin-bottom:6px;color:var(--ink-muted)">Related Signals</h4>`;
      for (const s of relatedSignals) {
        html += `<div style="display:flex;justify-content:space-between;padding:2px 0;font-size:11px"><span>${s.name}</span><span style="font-weight:600">${typeof s.value==='number'?s.value.toFixed(2):s.value} ${s.unit||""}</span></div>`;
      }
    }

    body.innerHTML = html;
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

  return { init, loadGraph, updateTelemetry, render, showPropertyPanel };
})();
