/* Virtual Factory — Settings Panels (v2)

   Provides interactive controls for:
   - Fault injection (valve stuck, pump degradation, sensor bias/drift)
   - OPC UA / IIoT export configuration

   PID controller tuning moved to the Asset Details inspector
   (click a PID controller in the process diagram to tune it).
 */

const SETTINGS = (() => {
  let faultStuck = null, faultPumpDeg = null, faultBias = null;

  function init() {
    if (typeof WIDGETS === "undefined") { setTimeout(init, 200); return; }

    // --- Fault Controls ---
    const faultCard = document.getElementById("fault-controls");
    if (faultCard) {
      faultStuck = new WIDGETS.ToggleSwitch(faultCard, {
        label: "Valve V101 Stuck",
        onChange: (v) => injectFault("valve_stuck", v ? 30 : null),
      });
      faultPumpDeg = new WIDGETS.ToggleSwitch(faultCard, {
        label: "Pump P101 Degraded (50%)",
        onChange: (v) => injectFault("pump_degradation", v ? 50 : null),
      });
      faultBias = new WIDGETS.NumberSpinner(faultCard, {
        label: "LT102 Sensor Bias (m)", min: -2, max: 2, step: 0.01, value: 0, decimals: 2, unit: "m",
        onChange: (v) => { if (Math.abs(v) < 0.001) injectFault("sensor_bias", null); else injectFault("sensor_bias", v); },
      });
    }

    // --- OPC Controls ---
    const opcCard = document.getElementById("opc-controls");
    if (opcCard) {
      opcCard.innerHTML = `
        <p style="font-size:11px;color:var(--ink-muted);margin-bottom:10px">
          Configure which signals are exported via OPC UA to external IIoT platforms, historians, and SCADA systems.
        </p>
        <div id="opc-signal-list" style="max-height:200px;overflow-y:auto;margin-bottom:10px"></div>
        <button class="topbar-btn primary" id="opc-test-connection" style="width:100%;margin-top:4px">
          🔌 Test OPC Connection
        </button>
        <span id="opc-test-result" style="display:block;font-size:11px;margin-top:6px"></span>
      `;
      populateOpcSignalList();

      document.getElementById("opc-test-connection").addEventListener("click", async () => {
        const res = document.getElementById("opc-test-result");
        res.textContent = "Testing…";
        try {
          const r = await fetch("/api/opcua/status");
          const d = await r.json();
          res.innerHTML = d.enabled
            ? '<span style="color:var(--success)">✅ OPC UA server running on ' + (d.endpoint||"default") + '</span>'
            : '<span style="color:var(--warning)">⚠️ OPC UA not enabled</span>';
        } catch (e) {
          res.innerHTML = '<span style="color:var(--danger)">❌ Connection failed</span>';
        }
      });
    }
  }

  // ---- Fault injection via API ----
  async function injectFault(faultType, value) {
    try {
      await fetch("/api/fault", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type: faultType, value: value }),
      });
    } catch (e) { console.warn("Fault injection failed:", e); }
  }

  // ---- OPC signal list ----
  function populateOpcSignalList() {
    const list = document.getElementById("opc-signal-list");
    if (!list) return;
    const signals = [
      { name: "LT102_LEVEL", desc: "T102 Level", unit: "m" },
      { name: "FT101_FLOW", desc: "V101 Outlet Flow", unit: "m³/s" },
      { name: "PT101_PRESSURE", desc: "P101 Discharge Pressure", unit: "kPa" },
      { name: "LIC102_OUT", desc: "Controller Output", unit: "%" },
      { name: "V101_OPENING_FEEDBACK", desc: "Valve Position", unit: "%" },
    ];
    list.innerHTML = signals.map(s => `
      <label style="display:flex;align-items:center;gap:8px;padding:5px 0;font-size:12px;cursor:pointer">
        <input type="checkbox" checked data-signal="${s.name}">
        <span style="flex:1">${s.name}</span>
        <span style="color:var(--ink-muted);font-size:10px">${s.desc}</span>
        <span style="color:var(--ink-muted);font-size:10px">[${s.unit}]</span>
      </label>
    `).join("");
  }

  return { init };
})();
