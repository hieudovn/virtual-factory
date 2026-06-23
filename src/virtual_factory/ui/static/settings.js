/* Virtual Factory — Settings Panels (v2)

   Provides interactive controls for:
   - Fault injection (valve stuck, pump degradation, sensor bias/drift)
   - OPC UA / IIoT export configuration

   PID controller tuning moved to the Asset Details inspector
   (click a PID controller in the process diagram to tune it).
 */

const SETTINGS = (() => {
  let faultControls = [];

  function init() {
    if (typeof WIDGETS === "undefined") { setTimeout(init, 200); return; }
    buildFaultControls();
    buildOpcControls();
  }

  async function buildFaultControls() {
    const faultCard = document.getElementById("fault-controls");
    if (!faultCard) return;
    faultControls.forEach(c => c.el?.remove?.());
    faultControls = [];

    try {
      const r = await fetch("/api/plant-graph");
      const graph = await r.json();
      const equipmentNodes = (graph.nodes || []).filter(n => n.category === "equipment");

      if (!equipmentNodes.length) {
        faultCard.innerHTML = '<p style="color:var(--ink-muted);font-size:12px">No equipment found.</p>';
        return;
      }

      faultCard.innerHTML = '<p style="font-size:11px;color:var(--ink-muted);margin-bottom:10px">Inject faults into equipment. Changes apply immediately.</p>';

      for (const eq of equipmentNodes) {
        const section = document.createElement("div");
        section.style.cssText = "margin-bottom:12px;padding:8px;border:1px solid var(--border-panel);border-radius:6px";
        section.innerHTML = '<div style="font-weight:600;font-size:12px;margin-bottom:6px">' + eq.id + ' (' + (eq.display_name || eq.model_type || '') + ')</div>';
        faultCard.appendChild(section);

        new WIDGETS.ToggleSwitch(section, {
          label: eq.id + ' Running',
          initialState: true,
          onChange: (v) => injectFault("set_truth", { target: eq.id + ".running", value: v }),
        });

        new WIDGETS.NumberSpinner(section, {
          label: eq.id + ' Flow (m\u00B3/s)',
          min: 0, max: 10, step: 0.1, value: 1.0, decimals: 1, unit: "m\u00B3/s",
          onChange: (v) => injectFault("set_truth", { target: eq.id + ".flow_m3_s", value: v }),
        });
      }

      const sensorNodes = (graph.nodes || []).filter(n => n.category === "sensors");
      if (sensorNodes.length) {
        const sSection = document.createElement("div");
        sSection.style.cssText = "margin-top:12px;padding:8px;border:1px solid var(--border-panel);border-radius:6px";
        sSection.innerHTML = '<div style="font-weight:600;font-size:12px;margin-bottom:6px">Sensor Quality</div>';
        faultCard.appendChild(sSection);

        const sn = sensorNodes[0];
        new WIDGETS.NumberSpinner(sSection, {
          label: sn.id + ' Bias',
          min: -10, max: 10, step: 0.01, value: 0, decimals: 2,
          onChange: (v) => injectFault("sensor_bias", { target: sn.id, value: v }),
        });
        new WIDGETS.NumberSpinner(sSection, {
          label: sn.id + ' Drift (/s)',
          min: -0.1, max: 0.1, step: 0.001, value: 0, decimals: 3,
          onChange: (v) => injectFault("sensor_drift", { target: sn.id, value: v }),
        });
        new WIDGETS.ToggleSwitch(sSection, {
          label: sn.id + ' Stuck',
          onChange: (v) => injectFault("sensor_quality", { target: sn.id, value: v ? "STUCK" : "GOOD" }),
        });
      }
    } catch (e) {
      faultCard.innerHTML = '<p style="color:var(--danger);font-size:12px">Failed to load plant graph.</p>';
      console.warn("Fault controls:", e);
    }
  }

  async function injectFault(faultType, payload) {
    try {
      await fetch("/api/fault", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type: faultType, ...payload }),
      });
    } catch (e) { console.warn("Fault injection failed:", e); }
  }

  function buildOpcControls() {
    const opcCard = document.getElementById("opc-controls");
    if (!opcCard) return;
    opcCard.innerHTML = '' +
      '<p style="font-size:11px;color:var(--ink-muted);margin-bottom:10px">' +
      'Configure OPC UA export signals.</p>' +
      '<div id="opc-signal-list" style="max-height:200px;overflow-y:auto;margin-bottom:10px"></div>' +
      '<button class="topbar-btn primary" id="opc-test-connection" style="width:100%;margin-top:4px">Test OPC Connection</button>' +
      '<span id="opc-test-result" style="display:block;font-size:11px;margin-top:6px"></span>';
    populateOpcSignalList();
    document.getElementById("opc-test-connection").addEventListener("click", async () => {
      const res = document.getElementById("opc-test-result");
      res.textContent = "Testing...";
      try {
        const r = await fetch("/api/opcua/status");
        const d = await r.json();
        res.innerHTML = d.enabled
          ? '<span style="color:var(--success)">OPC UA server running on ' + (d.endpoint||"default") + '</span>'
          : '<span style="color:var(--warning)">OPC UA not enabled</span>';
      } catch (e) {
        res.innerHTML = '<span style="color:var(--danger)">Connection failed</span>';
      }
    });
  }

  async function populateOpcSignalList() {
    const list = document.getElementById("opc-signal-list");
    if (!list) return;
    try {
      const r = await fetch("/telemetry/latest");
      const frame = await r.json();
      const signals = (frame || []).filter(s => s && s.category === "industrial_signal");
      if (!signals.length) { list.innerHTML = '<p style="font-size:11px;color:var(--ink-muted)">No signals available</p>'; return; }
      list.innerHTML = signals.map(s => '' +
        '<label style="display:flex;align-items:center;gap:8px;padding:5px 0;font-size:12px;cursor:pointer">' +
        '<input type="checkbox" checked data-signal="' + s.name + '">' +
        '<span style="flex:1">' + s.name + '</span>' +
        '<span style="color:var(--ink-muted);font-size:10px">[' + (s.unit||"-") + ']</span>' +
        '</label>'
      ).join("");
    } catch (e) {
      list.innerHTML = '<p style="font-size:11px;color:var(--ink-muted)">Could not load signals</p>';
    }
  }

  return { init };
})();
