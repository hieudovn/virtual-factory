const KPI_SIGNALS = [
  "LT102_LEVEL",
  "FT101_FLOW",
  "PT101_PRESSURE",
  "LIC102_OUT",
  "V101_OPENING_FEEDBACK",
];

const ALARM_SIGNALS = [
  "T102_LOW_LEVEL_ALARM",
  "T102_HIGH_LEVEL_ALARM",
  "P101_NO_FLOW_ALARM",
  "V101_POSITION_DEVIATION_ALARM",
  "LT102_BAD_QUALITY_ALARM",
];

const state = {
  telemetry: new Map(),
  alarms: new Map(),
  pollingId: null,
  socket: null,
};

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("start-loop").addEventListener("click", () => postStatus("/start"));
  document.getElementById("stop-loop").addEventListener("click", () => postStatus("/stop"));
  document.getElementById("step-once").addEventListener("click", () => postAndRender("/step"));
  document.getElementById("run-ten").addEventListener("click", () => postAndRender("/run-steps?n=10"));
  document.getElementById("refresh").addEventListener("click", refreshAll);
  renderEmptyCards();
  refreshAll();
  connectTelemetrySocket();
});

async function refreshAll() {
  await Promise.all([loadStatus(), loadLatestTelemetry(), loadAlarms()]);
}

async function postAndRender(path) {
  const response = await fetch(path, { method: "POST" });
  const frame = await response.json();
  updateTelemetry(frame);
  await Promise.all([loadStatus(), loadAlarms()]);
}

async function postStatus(path) {
  const response = await fetch(path, { method: "POST" });
  renderStatus(await response.json());
}

async function loadStatus() {
  const response = await fetch("/status");
  renderStatus(await response.json());
}

function renderStatus(payload) {
  document.getElementById("plant-name").textContent = payload.plant_name || payload.plant_id || "Unknown";
  document.getElementById("scenario-name").textContent = payload.scenario_id || "None";
  document.getElementById("simulation-time").textContent = formatSeconds(payload.time_s);
  document.getElementById("runtime-state").textContent = payload.running ? "Running" : "Stopped";
}

async function loadLatestTelemetry() {
  const response = await fetch("/telemetry/latest");
  const frame = await response.json();
  updateTelemetry(frame);
  updateAlarms(frame);
}

async function loadAlarms() {
  const response = await fetch("/alarms");
  updateAlarms(await response.json());
}

function connectTelemetrySocket() {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${protocol}://${window.location.host}/ws/telemetry`);
  state.socket = socket;

  socket.addEventListener("open", () => {
    setConnectionState("Live");
    stopPolling();
  });

  socket.addEventListener("message", (event) => {
    const frame = JSON.parse(event.data);
    updateTelemetry(frame);
    updateAlarms(frame);
    updateTimeFromFrame(frame);
  });

  socket.addEventListener("error", () => {
    setConnectionState("Polling");
    startPolling();
  });

  socket.addEventListener("close", () => {
    setConnectionState("Polling");
    startPolling();
  });
}

function startPolling() {
  if (state.pollingId) {
    return;
  }
  state.pollingId = window.setInterval(loadLatestTelemetry, 1000);
}

function stopPolling() {
  if (state.pollingId) {
    window.clearInterval(state.pollingId);
    state.pollingId = null;
  }
}

function updateTelemetry(frame) {
  const signals = filterPublishable(frame);
  for (const signal of signals) {
    state.telemetry.set(signal.name, signal);
  }
  renderKpis();
  updateTimeFromFrame(signals);
}

function updateAlarms(frame) {
  const signals = filterPublishable(frame).filter((signal) => signal.category === "industrial_event");
  for (const signal of signals) {
    state.alarms.set(signal.name, signal);
  }
  renderAlarms();
}

function filterPublishable(frame) {
  if (!Array.isArray(frame)) {
    return [];
  }
  return frame.filter((signal) => signal && signal.category !== "internal_truth");
}

function renderEmptyCards() {
  renderKpis();
  renderAlarms();
}

function renderKpis() {
  const grid = document.getElementById("kpi-grid");
  grid.replaceChildren(...KPI_SIGNALS.map((name) => renderSignalCard(name, state.telemetry.get(name))));
}

function renderAlarms() {
  const list = document.getElementById("alarm-list");
  list.replaceChildren(...ALARM_SIGNALS.map((name) => renderAlarmRow(name, state.alarms.get(name))));
}

function renderSignalCard(name, signal) {
  const card = document.createElement("article");
  card.className = "kpi-card";
  const value = signal ? formatValue(signal.value) : "--";
  const unit = signal?.unit || "";
  const quality = signal?.quality || "UNKNOWN";
  const timestamp = signal ? formatSeconds(signal.timestamp_s) : "--";
  card.innerHTML = `
    <h3>${name}</h3>
    <p class="metric">${value}<span>${unit}</span></p>
    <dl>
      <div><dt>Quality</dt><dd>${quality}</dd></div>
      <div><dt>Timestamp</dt><dd>${timestamp}</dd></div>
    </dl>
  `;
  return card;
}

function renderAlarmRow(name, signal) {
  const active = Boolean(signal?.value);
  const row = document.createElement("article");
  row.className = `alarm-row${active ? " active" : ""}`;
  row.innerHTML = `
    <div>
      <h3>${name}</h3>
      <span>${signal?.quality || "UNKNOWN"} · ${signal ? formatSeconds(signal.timestamp_s) : "--"}</span>
    </div>
    <strong>${active ? "ACTIVE" : "CLEAR"}</strong>
  `;
  return row;
}

function updateTimeFromFrame(frame) {
  const signals = filterPublishable(frame);
  if (!signals.length) {
    return;
  }
  const latest = signals.reduce((max, signal) => Math.max(max, Number(signal.timestamp_s) || 0), 0);
  document.getElementById("simulation-time").textContent = formatSeconds(latest);
  document.getElementById("last-updated").textContent = `Updated at ${formatSeconds(latest)}`;
}

function setConnectionState(value) {
  document.getElementById("connection-state").textContent = value;
}

function formatValue(value) {
  if (typeof value === "number") {
    return value.toFixed(Math.abs(value) >= 100 ? 1 : 4);
  }
  if (value === null || value === undefined) {
    return "--";
  }
  return String(value);
}

function formatSeconds(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return "--";
  }
  return `${numeric.toFixed(1)} s`;
}
