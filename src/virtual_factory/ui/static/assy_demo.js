/* M6-S04B-I04 — Frame A: ASSY Six-Sub-Line Overview Controller & Renderer */

const API = '/assy-demo';

/* ==============================
   S04B Frame A Controller
   ============================== */
const ctrl = {
  _autoTimer: null,
  _speed: 1.0,
  _scenario: 'HAPPY_PATH',

  async init() {
    await this.call('reset', { scenario: this._scenario });
    await this.refreshOverview();
  },

  async reset() {
    this.stopAuto();
    this._scenario = document.getElementById('scenario-select').value;
    await this.call('reset', { scenario: this._scenario });
    await this.refreshOverview();
  },

  async step() {
    await this.call('step');
    await this.refreshOverview();
  },

  toggleAuto() {
    if (this._autoTimer) { this.stopAuto(); return; }
    this.startAuto();
  },

  startAuto() {
    document.getElementById('btn-auto').textContent = '\u23F9 STOP';
    document.getElementById('btn-pause').disabled = false;
    this._autoTimer = setInterval(() => this.step(), Math.round(1000 / this._speed));
  },

  stopAuto() {
    if (this._autoTimer) { clearInterval(this._autoTimer); this._autoTimer = null; }
    document.getElementById('btn-auto').textContent = '\u25B6\u25B6 AUTO';
    document.getElementById('btn-pause').disabled = true;
  },

  pause() { if (this._autoTimer) this.stopAuto(); },

  setSpeed(val) {
    this._speed = parseFloat(val);
    if (this._autoTimer) { this.stopAuto(); this.startAuto(); }
  },

  setScenario(val) {
    this._scenario = val;
    this.reset();
  },

  async call(action, body) {
    const opts = body
      ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }
      : { method: 'POST' };
    const resp = await fetch(`${API}/${action}`, opts);
    if (!resp.ok) throw new Error(`${action}: ${resp.status}`);
    return resp.json();
  },

  async refreshOverview() {
    try {
      const ov = await (await fetch(`${API}/overview`)).json();
      this.renderOverview(ov);
    } catch (_) { /* overview not available — stay with last render */ }
  },

  /* ---------- Frame A SVG Render ---------- */
  renderOverview(ov) {
    const lanes = document.getElementById('svg-lanes');
    if (!lanes) return;

    // Header
    document.getElementById('demo-step').textContent = `DEMO STEP ${String(ov.demo_step_number).padStart(3,'0')}`;
    document.getElementById('global-scenario').textContent = ov.scenario || 'HAPPY_PATH';
    document.getElementById('total-created').textContent = ov.total_motors_created;
    document.getElementById('total-released').textContent = ov.total_motors_released;
    document.getElementById('total-holds').textContent = ov.total_active_holds;
    const hb = document.getElementById('total-holds-badge');
    hb.style.color = ov.total_active_holds > 0 ? '#e94560' : '#8899bb';

    // Lane layout constants
    const START_Y = 82, LANE_H = 88, GAP = 12;
    const GROUP_GAP = 20;
    const hydSl = (ov.sub_lines || []).filter(s => s.variant === 'hydraulic');
    const thmSl = (ov.sub_lines || []).filter(s => s.variant === 'thermal');

    let html = '';

    // Hydraulic group
    hydSl.forEach((sl, i) => {
      html += renderLane(sl, START_Y + i * (LANE_H + GAP), i);
    });

    // Thermal group
    const thmY = START_Y + 3 * (LANE_H + GAP) + GROUP_GAP;
    thmSl.forEach((sl, i) => {
      html += renderLane(sl, thmY + i * (LANE_H + GAP), i + 3);
    });

    lanes.innerHTML = html;
  }
};

/* ---------- Lane SVG Builder ---------- */
const STATIONS = ['PRE-ASSY','AP01','AP02','AP03','AP04','AP05','AP06','AP07','AP08','AP09','AP10','AP11'];
const STATION_X = [250,340,430,520,610,700,790,880,960,1040,1120,1200];
const COLOR = {
  hydraulic: { fill: '#111d30', stroke: '#1e3a5f', accent: '#8899bb' },
  thermal:   { fill: '#141028', stroke: '#2a1a40', accent: '#9988bb' },
};

function renderLane(sl, y, idx) {
  const c = COLOR[sl.variant] || COLOR.hydraulic;
  const isExc = sl.is_exception;
  const excStroke = isExc ? ' stroke="#e94560" stroke-width="2"' : ` stroke="${c.stroke}" stroke-width="1"`;
  const laneW = 1620;

  let statusColor = '#4ecca3', statusLabel = sl.line_state.toUpperCase();
  if (isExc) { statusColor = '#e94560'; statusLabel = 'QUALITY HOLD'; }
  else if (sl.line_state === 'stopped') { statusColor = '#888'; }
  else if (sl.line_state === 'ready_to_index') { statusColor = '#17a2b8'; }

  let dots = '';
  STATION_X.forEach((sx, si) => {
    const r = (si === 3 || si === 5 || si === 6 || si === 10) ? 6 : 4;
    const fill = isExc && si === 5 ? '#e94560' : '#4ecca3';
    const op = si < sl.wips_on_line ? (isExc && si === 5 ? 0.9 : 0.6) : 0.25;
    dots += `<circle cx="${sx}" cy="${y+50}" r="${r}" fill="${fill}" opacity="${op}"/>`;
  });

  const heldInfo = isExc && sl.held_station
    ? `<text x="1320" y="${y+50}" fill="#e94560" font-size="10">\u23F8 ${sl.held_station} / ${sl.held_wip_id}</text>`
    : '';

  return `
    <rect x="40" y="${y}" width="${laneW}" height="88" rx="4" fill="${isExc ? '#1a1015' : c.fill}"${excStroke}/>
    <text x="56" y="${y+24}" fill="${isExc ? '#e94560' : c.accent}" font-size="13" font-weight="600">${sl.sub_line_id}</text>
    <rect x="160" y="${y+10}" width="72" height="18" rx="3" fill="${isExc ? '#4a1a1a' : '#1b4332'}"/>
    <text x="196" y="${y+24}" fill="${statusColor}" font-size="10" text-anchor="middle">${statusLabel}</text>
    <text x="250" y="${y+24}" fill="#666" font-size="9">${sl.variant.toUpperCase()}</text>
    <rect x="250" y="${y+36}" width="1050" height="8" rx="4" fill="${isExc ? '#1a1010' : '#1a2740'}"/>
    ${dots}
    ${heldInfo}
    <text x="1330" y="${y+24}" fill="#666" font-size="9">WIP:${sl.wips_on_line} OUT:${sl.motors_released} DW:${sl.dwell_number}</text>
    <text x="1480" y="${y+24}" fill="#555" font-size="9">t=${sl.simulation_time_s.toFixed(0)}s</text>
  `;
}


/* ==============================
   S04 Fallback (preserved)
   ============================== */
const ctrlS04 = {
  _autoTimer: null, _speed: 1.0, _scenario: 'HAPPY_PATH',

  async init() {
    await this.call('reset', { scenario: this._scenario });
    this.render(await this.call('snapshot'));
  },

  async reset() {
    this.stopAuto();
    this._scenario = document.getElementById('scenario-select-s04').value;
    await this.call('reset', { scenario: this._scenario });
    this.render(await this.call('snapshot'));
  },

  async step() {
    const snap = await this.call('step');
    this.render(snap);
  },

  toggleAuto() { this._autoTimer ? this.stopAuto() : this.startAuto(); },

  startAuto() {
    document.getElementById('btn-auto-s04').textContent = '\u23F9 STOP';
    document.getElementById('btn-pause-s04').disabled = false;
    this._autoTimer = setInterval(() => this.step(), Math.round(1000 / this._speed));
  },

  stopAuto() {
    if (this._autoTimer) { clearInterval(this._autoTimer); this._autoTimer = null; }
    document.getElementById('btn-auto-s04').textContent = '\u25B6\u25B6 AUTO';
    document.getElementById('btn-pause-s04').disabled = true;
  },

  pause() { if (this._autoTimer) this.stopAuto(); },

  setSpeed(val) { this._speed = parseFloat(val); if (this._autoTimer) { this.stopAuto(); this.startAuto(); } },

  setScenario(val) { this._scenario = val; this.reset(); },

  async call(action, body) {
    const opts = body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : { method: 'POST' };
    const resp = await fetch(`${API}/${action}`, opts);
    return resp.json();
  },

  render(snap) {
    if (!snap || !snap.positions) return;
    document.getElementById('sim-time').textContent = `t=${snap.simulation_time_s.toFixed(0)}s`;
    const ls = document.getElementById('line-state');
    ls.textContent = snap.line_state.toUpperCase();
    ls.className = 'state ' + snap.line_state;
    document.getElementById('dwell').textContent = `Dwell ${snap.dwell_number}`;
    const container = document.getElementById('positions-container');
    container.innerHTML = '';
    for (const p of snap.positions) {
      const div = document.createElement('div');
      div.className = 'position';
      if (p.is_quality_hold) div.className += ' quality-hold';
      else if (p.is_occupied) div.className += ' occupied';
      if (p.manufacturing_status === 'released') div.className += ' released';
      if (p.position_id === 'AP04') div.className += ' ap04';
      div.innerHTML = `<div class="pos-id">${p.position_id}</div><div class="pos-label">${p.station_label}</div>${
        p.wip_id ? `<div class="wip-info"><div class="wip-id ${p.wip_type}">${p.wip_id}</div>${
          p.carrier_id ? `<div class="carrier">${p.carrier_id}</div>` : ''}${
          p.latest_quality_result ? `<div class="quality-badge ${p.latest_quality_result.toLowerCase()}">${p.latest_quality_result}${p.attempt_number > 1 ? ' #'+p.attempt_number : ''}</div>` : ''}${
          p.is_quality_hold ? '<div class="quality-badge hold">HOLD</div>' : ''}${
          p.manufacturing_status === 'released' ? '<div class="quality-badge pass">RELEASED</div>' : ''}</div>`
        : '<div style="color:#555;font-size:0.7em;margin-top:8px;">\u2014</div>'}</div>`;
      container.appendChild(div);
    }
    const prod = snap.production || {};
    document.getElementById('motors-completed').textContent = prod.motors_created || 0;
    document.getElementById('motors-released').textContent = prod.motors_released || 0;
    document.getElementById('wips-on-line').textContent = prod.wips_on_line || 0;
    document.getElementById('active-holds').textContent = prod.active_quality_holds || 0;
    document.getElementById('rso2-buf').textContent = prod.rso2_buffer || 0;
    const glist = document.getElementById('genealogy-list');
    glist.innerHTML = '';
    for (const g of (snap.genealogy || []).slice(-6)) {
      glist.innerHTML += `<div class="genealogy-item"><b style="color:#ffc107">${g.child_wip_id}</b> \u2190 ${g.parent_wip_ids.join(' + ')}<br><small>t=${g.join_time_s.toFixed(0)}s @ ${g.join_station}</small></div>`;
    }
    const qlist = document.getElementById('quality-events');
    qlist.innerHTML = '';
    for (const e of (snap.recent_quality_events || []).slice(-15)) {
      qlist.innerHTML += `<div class="qe-item"><span class="qe-disp ${e.disposition}">${e.disposition}</span>${e.wip_id} @ ${e.station_id} #${e.attempt} <small>t=${e.simulation_time_s.toFixed(0)}s</small></div>`;
    }
    document.getElementById('scenario-display').textContent = snap.scenario || 'HAPPY_PATH';
  }
};


/* ==============================
   Feature Detection + Boot
   ============================== */
async function detectS04B() {
  try {
    const r = await fetch(`${API}/overview`);
    return r.ok;
  } catch (_) { return false; }
}

document.addEventListener('DOMContentLoaded', async () => {
  const s04b = await detectS04B();
  if (s04b) {
    document.getElementById('frame-a').style.display = 'flex';
    document.getElementById('frame-a').style.flexDirection = 'column';
    document.getElementById('frame-a').style.height = '100vh';
    document.getElementById('frame-s04').style.display = 'none';
    ctrl.init();
  } else {
    document.getElementById('frame-a').style.display = 'none';
    document.getElementById('frame-s04').style.display = 'flex';
    document.getElementById('frame-s04').style.flexDirection = 'column';
    document.getElementById('frame-s04').style.height = '100vh';
    ctrlS04.init();
  }
});
