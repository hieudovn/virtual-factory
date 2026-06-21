/* Virtual Factory — SVG Icon Library

   Professional equipment icons for use in the process flow diagram,
   asset palette, and builder canvas. All icons are pure SVG paths
   rendered at a standard 64×64 viewBox for consistent scaling.
 */

const ICONS = (() => {
  const NS = "http://www.w3.org/2000/svg";

  function el(tag, attrs, text) {
    const e = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      e.setAttribute(k, v);
    }
    if (text !== undefined) e.textContent = text;
    return e;
  }

  // ==================================================================
  // Equipment Icons (64×64 viewBox)
  // ==================================================================

  function tankIcon(opts = {}) {
    const fill = opts.fill || "#e0f2fe";
    const stroke = opts.stroke || "#0284c7";
    const g = el("g", { class: "icon icon-tank" });
    // Tank body — vertical cylinder
    g.appendChild(el("path", {
      d: "M16 12 L16 56 Q16 60 20 60 L44 60 Q48 60 48 56 L48 12 Z",
      fill, stroke, "stroke-width": "2",
    }));
    // Tank top ellipse
    g.appendChild(el("ellipse", {
      cx: "32", cy: "12", rx: "16", ry: "5",
      fill: "none", stroke, "stroke-width": "2",
    }));
    // Liquid level indicator lines
    g.appendChild(el("line", { x1: "20", y1: "44", x2: "44", y2: "44", stroke, "stroke-width": "1", opacity: "0.4" }));
    g.appendChild(el("line", { x1: "20", y1: "34", x2: "44", y2: "34", stroke, "stroke-width": "1", opacity: "0.4" }));
    g.appendChild(el("line", { x1: "20", y1: "24", x2: "44", y2: "24", stroke, "stroke-width": "1", opacity: "0.4" }));
    return g;
  }

  function pumpIcon(opts = {}) {
    const fill = opts.fill || "#fce7f3";
    const stroke = opts.stroke || "#db2777";
    const g = el("g", { class: "icon icon-pump" });
    // Pump body — circle with inner detail
    g.appendChild(el("circle", { cx: "32", cy: "32", r: "18", fill, stroke, "stroke-width": "2" }));
    // Impeller triangle
    g.appendChild(el("polygon", {
      points: "32,18 24,44 40,44",
      fill: stroke, opacity: "0.3",
    }));
    // Inlet pipe stub
    g.appendChild(el("rect", { x: "4", y: "28", width: "10", height: "8", fill: stroke, rx: "2" }));
    // Outlet pipe stub
    g.appendChild(el("rect", { x: "50", y: "28", width: "10", height: "8", fill: stroke, rx: "2" }));
    // Rotation arrow
    g.appendChild(el("path", {
      d: "M40 22 A14 14 0 0 1 26 20",
      stroke, "stroke-width": "1.5", fill: "none",
    }));
    return g;
  }

  function valveIcon(opts = {}) {
    const fill = opts.fill || "#fef3c7";
    const stroke = opts.stroke || "#d97706";
    const g = el("g", { class: "icon icon-valve" });
    // Valve body — bowtie shape
    g.appendChild(el("polygon", {
      points: "12,24 32,20 52,24 52,40 32,44 12,40",
      fill, stroke, "stroke-width": "2",
    }));
    // Valve stem
    g.appendChild(el("line", { x1: "32", y1: "20", x2: "32", y2: "8", stroke, "stroke-width": "2" }));
    // Handle
    g.appendChild(el("line", { x1: "24", y1: "8", x2: "40", y2: "8", stroke, "stroke-width": "3", "stroke-linecap": "round" }));
    // Flow arrow through
    g.appendChild(el("line", { x1: "4", y1: "32", x2: "12", y2: "32", stroke, "stroke-width": "2" }));
    g.appendChild(el("line", { x1: "52", y1: "32", x2: "60", y2: "32", stroke, "stroke-width": "2" }));
    return g;
  }

  function pipeIcon(opts = {}) {
    const stroke = opts.stroke || "#64748b";
    const g = el("g", { class: "icon icon-pipe" });
    // Horizontal pipe segment
    g.appendChild(el("rect", { x: "4", y: "26", width: "56", height: "12", fill: "#e2e8f0", stroke, "stroke-width": "2", rx: "4" }));
    // Flanges
    g.appendChild(el("rect", { x: "8", y: "22", width: "4", height: "20", fill: stroke, rx: "1" }));
    g.appendChild(el("rect", { x: "52", y: "22", width: "4", height: "20", fill: stroke, rx: "1" }));
    return g;
  }

  function heatExchangerIcon(opts = {}) {
    const fill = opts.fill || "#f0fdf4";
    const stroke = opts.stroke || "#16a34a";
    const g = el("g", { class: "icon icon-hex" });
    // Shell
    g.appendChild(el("rect", { x: "8", y: "16", width: "48", height: "32", fill, stroke, "stroke-width": "2", rx: "6" }));
    // Tube bundle zigzag
    g.appendChild(el("polyline", {
      points: "16,22 24,34 32,22 40,34 48,22",
      stroke, "stroke-width": "1.5", fill: "none",
    }));
    // Hot inlet/outlet arrows
    g.appendChild(el("line", { x1: "8", y1: "28", x2: "2", y2: "28", stroke: "#dc2626", "stroke-width": "2" }));
    g.appendChild(el("line", { x1: "56", y1: "36", x2: "62", y2: "36", stroke: "#dc2626", "stroke-width": "2" }));
    // Cold inlet/outlet arrows
    g.appendChild(el("line", { x1: "8", y1: "36", x2: "2", y2: "36", stroke: "#2563eb", "stroke-width": "2" }));
    g.appendChild(el("line", { x1: "56", y1: "28", x2: "62", y2: "28", stroke: "#2563eb", "stroke-width": "2" }));
    return g;
  }

  function fanIcon(opts = {}) {
    const fill = opts.fill || "#f5f3ff";
    const stroke = opts.stroke || "#7c3aed";
    const g = el("g", { class: "icon icon-fan" });
    // Fan housing circle
    g.appendChild(el("circle", { cx: "32", cy: "32", r: "18", fill, stroke, "stroke-width": "2" }));
    // Blades
    for (let i = 0; i < 4; i++) {
      const angle = (i * 90 - 45) * Math.PI / 180;
      const x1 = 32 + 8 * Math.cos(angle);
      const y1 = 32 + 8 * Math.sin(angle);
      const x2 = 32 + 18 * Math.cos(angle);
      const y2 = 32 + 18 * Math.sin(angle);
      g.appendChild(el("line", { x1, y1, x2, y2, stroke, "stroke-width": "2.5", "stroke-linecap": "round" }));
    }
    // Center hub
    g.appendChild(el("circle", { cx: "32", cy: "32", r: "5", fill: stroke }));
    return g;
  }

  // ==================================================================
  // Instrumentation Icons
  // ==================================================================

  function sensorIcon(opts = {}) {
    const fill = opts.fill || "#fefce8";
    const stroke = opts.stroke || "#ca8a04";
    const g = el("g", { class: "icon icon-sensor" });
    // Sensor body — circle inscribed in diamond
    g.appendChild(el("polygon", {
      points: "32,8 56,32 32,56 8,32",
      fill, stroke, "stroke-width": "2",
    }));
    g.appendChild(el("circle", { cx: "32", cy: "32", r: "10", fill: "none", stroke, "stroke-width": "1.5" }));
    g.appendChild(el("text", {
      x: "32", y: "36", "text-anchor": "middle",
      fill: stroke, "font-size": "10", "font-weight": "700", "font-family": "monospace",
    }, "T"));
    return g;
  }

  function controllerIcon(opts = {}) {
    const fill = opts.fill || "#f3e8ff";
    const stroke = opts.stroke || "#7c3aed";
    const g = el("g", { class: "icon icon-controller" });
    // Controller body — hexagon
    g.appendChild(el("polygon", {
      points: "32,8 54,22 54,42 32,56 10,42 10,22",
      fill, stroke, "stroke-width": "2",
    }));
    // PID text
    g.appendChild(el("text", {
      x: "32", y: "36", "text-anchor": "middle",
      fill: stroke, "font-size": "11", "font-weight": "700", "font-family": "monospace",
    }, "PID"));
    return g;
  }

  function actuatorIcon(opts = {}) {
    const fill = opts.fill || "#ffe4e6";
    const stroke = opts.stroke || "#e11d48";
    const g = el("g", { class: "icon icon-actuator" });
    // Actuator body — rounded rectangle
    g.appendChild(el("rect", { x: "12", y: "20", width: "40", height: "24", fill, stroke, "stroke-width": "2", rx: "4" }));
    // Stem/arrow
    g.appendChild(el("line", { x1: "32", y1: "20", x2: "32", y2: "6", stroke, "stroke-width": "2" }));
    g.appendChild(el("polygon", { points: "28,12 32,6 36,12", fill: stroke }));
    // Position indicator
    g.appendChild(el("rect", { x: "18", y: "26", width: "28", height: "4", fill: stroke, rx: "2", opacity: "0.5" }));
    g.appendChild(el("rect", { x: "18", y: "34", width: "16", height: "4", fill: stroke, rx: "2" }));
    return g;
  }

  function flowTransmitterIcon(opts = {}) {
    const fill = opts.fill || "#ecfdf5";
    const stroke = opts.stroke || "#059669";
    const g = el("g", { class: "icon icon-ft" });
    g.appendChild(el("circle", { cx: "32", cy: "32", r: "18", fill, stroke, "stroke-width": "2" }));
    g.appendChild(el("text", {
      x: "32", y: "28", "text-anchor": "middle",
      fill: stroke, "font-size": "12", "font-weight": "700", "font-family": "monospace",
    }, "FT"));
    g.appendChild(el("text", {
      x: "32", y: "44", "text-anchor": "middle",
      fill: stroke, "font-size": "8", "font-family": "monospace",
    }, "m³/s"));
    return g;
  }

  function levelTransmitterIcon(opts = {}) {
    const fill = opts.fill || "#eff6ff";
    const stroke = opts.stroke || "#2563eb";
    const g = el("g", { class: "icon icon-lt" });
    g.appendChild(el("circle", { cx: "32", cy: "32", r: "18", fill, stroke, "stroke-width": "2" }));
    g.appendChild(el("text", {
      x: "32", y: "28", "text-anchor": "middle",
      fill: stroke, "font-size": "12", "font-weight": "700", "font-family": "monospace",
    }, "LT"));
    g.appendChild(el("text", {
      x: "32", y: "44", "text-anchor": "middle",
      fill: stroke, "font-size": "8", "font-family": "monospace",
    }, "m"));
    return g;
  }

  function pressureTransmitterIcon(opts = {}) {
    const fill = opts.fill || "#fff7ed";
    const stroke = opts.stroke || "#ea580c";
    const g = el("g", { class: "icon icon-pt" });
    g.appendChild(el("circle", { cx: "32", cy: "32", r: "18", fill, stroke, "stroke-width": "2" }));
    g.appendChild(el("text", {
      x: "32", y: "28", "text-anchor": "middle",
      fill: stroke, "font-size": "12", "font-weight": "700", "font-family": "monospace",
    }, "PT"));
    g.appendChild(el("text", {
      x: "32", y: "44", "text-anchor": "middle",
      fill: stroke, "font-size": "8", "font-family": "monospace",
    }, "kPa"));
    return g;
  }

  // ==================================================================
  // Status / Action Icons (24×24 viewBox)
  // ==================================================================

  function alertIcon(opts = {}) {
    const color = opts.active ? "#dc2626" : "#16a34a";
    const g = el("g", { class: "icon icon-alert" });
    g.appendChild(el("circle", { cx: "12", cy: "12", r: "10", fill: color, opacity: "0.15" }));
    g.appendChild(el("circle", { cx: "12", cy: "12", r: "5", fill: color }));
    return g;
  }

  function settingsGearIcon() {
    const g = el("g", { class: "icon icon-gear" });
    g.appendChild(el("circle", { cx: "12", cy: "12", r: "5", fill: "none", stroke: "#64748b", "stroke-width": "2" }));
    // Gear teeth
    for (let i = 0; i < 8; i++) {
      const angle = (i * 45) * Math.PI / 180;
      const x = 12 + 8 * Math.cos(angle);
      const y = 12 + 8 * Math.sin(angle);
      g.appendChild(el("rect", {
        x: x - 2, y: y - 2, width: "4", height: "4",
        fill: "#64748b", rx: "1",
        transform: `rotate(${i * 45} ${x} ${y})`,
      }));
    }
    return g;
  }

  function playIcon() {
    const g = el("g", { class: "icon icon-play" });
    g.appendChild(el("polygon", {
      points: "6,4 18,12 6,20",
      fill: "#16a34a",
    }));
    return g;
  }

  function stopIcon() {
    const g = el("g", { class: "icon icon-stop" });
    g.appendChild(el("rect", { x: "5", y: "5", width: "14", height: "14", fill: "#dc2626", rx: "2" }));
    return g;
  }

  function stepIcon() {
    const g = el("g", { class: "icon icon-step" });
    g.appendChild(el("polygon", { points: "6,6 18,12 6,18", fill: "#7c3aed" }));
    g.appendChild(el("rect", { x: "19", y: "6", width: "3", height: "12", fill: "#7c3aed", rx: "1" }));
    return g;
  }

  // ==================================================================
  // Icon map for lookup by model_type
  // ==================================================================

  const MODEL_ICON_MAP = {
    tank_v1: tankIcon,
    centrifugal_pump_v1: pumpIcon,
    control_valve_v1: valveIcon,
    pipe_v1: pipeIcon,
    level_transmitter_v1: levelTransmitterIcon,
    flow_transmitter_v1: flowTransmitterIcon,
    pressure_transmitter_v1: pressureTransmitterIcon,
    pid_controller_v1: controllerIcon,
    valve_actuator_v1: actuatorIcon,
    heat_exchanger_v1: heatExchangerIcon,
    fan_v1: fanIcon,
    compressor_v1: pumpIcon,
    separator_v1: tankIcon,
  };

  // ==================================================================
  // Public API
  // ==================================================================

  return {
    // Equipment icons (64×64)
    tank: tankIcon,
    pump: pumpIcon,
    valve: valveIcon,
    pipe: pipeIcon,
    heatExchanger: heatExchangerIcon,
    fan: fanIcon,
    // Instrument icons
    sensor: sensorIcon,
    controller: controllerIcon,
    actuator: actuatorIcon,
    flowTransmitter: flowTransmitterIcon,
    levelTransmitter: levelTransmitterIcon,
    pressureTransmitter: pressureTransmitterIcon,
    // Action icons
    alert: alertIcon,
    gear: settingsGearIcon,
    play: playIcon,
    stop: stopIcon,
    step: stepIcon,
    // Lookup
    forModelType(type) {
      const fn = MODEL_ICON_MAP[type];
      return fn ? fn() : sensorIcon();
    },
    el,
    NS,
  };
})();
