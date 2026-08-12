/* M6-S04B-I04-C01 — Frame A: Truthful Overview + Semantic Zoom Preparation */

const API = '/assy-demo';
const LANDMARKS = new Set(['AP04','AP06','AP08','AP11']);
const LANDMARK_LABELS = { AP04:'JOIN', AP06:'TEST', AP08:'VISION', AP11:'FINAL' };
const STATIONS = ['PRE-ASSY','AP01','AP02','AP03','AP04','AP05','AP06','AP07','AP08','AP09','AP10','AP11'];

/* ==============================
   S04B Frame A Controller
   ============================== */
const ctrl = {
  _autoTimer: null,
  _speed: 1.0,
  _scenario: 'HAPPY_PATH',
  _selectedSubLineId: 'ASSY-SL01',
  _selectionInitialized: false,
  _lastOverview: null,
  _liveStatus: 'INIT',

  async init() {
    await this.call('reset', { scenario: this._scenario });
    await this.refreshOverview();
  },

  async reset() {
    this.stopAuto();
    this._scenario = document.getElementById('scenario-select').value;
    this._selectionInitialized = false;
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

  setSpeed(val) { this._speed = parseFloat(val); if (this._autoTimer) { this.stopAuto(); this.startAuto(); } },

  setScenario(val) { this._scenario = val; this.reset(); },

  async call(action, body) {
    const opts = body ? { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body) } : { method:'POST' };
    const resp = await fetch(`${API}/${action}`, opts);
    if (!resp.ok) throw new Error(`${action}: ${resp.status}`);
    return resp.json();
  },

  async refreshOverview() {
    try {
      const ov = await (await fetch(`${API}/overview`)).json();
      this._lastOverview = ov;
      this._liveStatus = 'LIVE';
      this.renderOverview(ov);
    } catch (_) {
      this._liveStatus = this._lastOverview ? 'STALE' : 'UNAVAILABLE';
      this.renderStatus();
    }
  },

  renderStatus() {
    const el = document.getElementById('live-status');
    if (!el) return;
    if (this._liveStatus === 'LIVE') { el.textContent = '\u25CF LIVE'; el.style.color = '#4ecca3'; }
    else if (this._liveStatus === 'STALE') { el.textContent = '\u25CB STALE'; el.style.color = '#ffc107'; }
    else { el.textContent = '\u2715 BACKEND UNAVAILABLE'; el.style.color = '#e94560'; }
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
    this.renderStatus();

    // Initialize selection from backend on first render only
    if (!this._selectionInitialized) {
      if (ov.selected_sub_line_id) this._selectedSubLineId = ov.selected_sub_line_id;
      this._selectionInitialized = true;
    }

    const START_Y = 82, LANE_H = 88, GAP = 12, GROUP_GAP = 20;
    const hydSl = (ov.sub_lines||[]).filter(s=>s.variant==='hydraulic');
    const thmSl = (ov.sub_lines||[]).filter(s=>s.variant==='thermal');

    let html = '';
    hydSl.forEach((sl,i) => { html += renderLane(sl, START_Y + i*(LANE_H+GAP), this._selectedSubLineId); });
    const thmY = START_Y + 3*(LANE_H+GAP) + GROUP_GAP;
    thmSl.forEach((sl,i) => { html += renderLane(sl, thmY + i*(LANE_H+GAP), this._selectedSubLineId); });

    lanes.innerHTML = html;
    this._bindLaneClicks();
  },

  _bindLaneClicks() {
    document.querySelectorAll('.assy-lane').forEach(el => {
      el.addEventListener('click', () => {
        const slId = el.getAttribute('data-sl');
        if (slId) { this._selectedSubLineId = slId; this._refreshLaneStyles(); }
      });
      el.addEventListener('dblclick', () => {
        const slId = el.getAttribute('data-sl');
        if (slId) { this._selectedSubLineId = slId; openFrameB(slId); }
      });
    });
    // Detail button click
    document.querySelectorAll('.fb-detail-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const slId = btn.getAttribute('data-sl');
        if (slId) openFrameB(slId);
      });
    });
  },

  _refreshLaneStyles() {
    document.querySelectorAll('.assy-lane').forEach(el => {
      const isSel = el.getAttribute('data-sl') === this._selectedSubLineId;
      el.style.outline = isSel ? '2px solid #17a2b8' : 'none';
      el.style.outlineOffset = '-2px';
    });
  }
};


/* ---------- Lane SVG Builder (topology-only, no fake occupancy) ---------- */
const STATION_X = [250,340,430,520,610,700,790,880,960,1040,1120,1200];
const COLOR = {
  hydraulic: { fill:'#111d30', stroke:'#1e3a5f', accent:'#8899bb' },
  thermal:   { fill:'#141028', stroke:'#2a1a40', accent:'#9988bb' },
};

function renderLane(sl, y, selectedId) {
  const c = COLOR[sl.variant]||COLOR.hydraulic;
  const isExc = sl.is_exception;
  const isSel = sl.sub_line_id === selectedId;
  const excStroke = isExc ? ' stroke="#e94560" stroke-width="2"' : ` stroke="${c.stroke}" stroke-width="1"`;
  const selStyle = isSel ? ' outline:2px solid #17a2b8;' : '';
  const laneW = 1620;

  let statusColor = '#4ecca3', statusLabel = sl.line_state.toUpperCase();
  if (isExc) { statusColor = '#e94560'; statusLabel = 'QUALITY HOLD'; }
  else if (sl.line_state === 'stopped') { statusColor = '#888'; }
  else if (sl.line_state === 'ready_to_index') { statusColor = '#17a2b8'; }

  // Station dots: topology-only, landmarks highlighted, held station marked
  let dots = '';
  STATIONS.forEach((stId, si) => {
    const sx = STATION_X[si];
    const isLandmark = LANDMARKS.has(stId);
    const isHeld = isExc && sl.held_station === stId;
    const r = isLandmark ? 5 : 3;
    let fill = isHeld ? '#e94560' : (isLandmark ? '#ffc107' : '#4ecca3');
    let op = isHeld ? 0.9 : (isLandmark ? 0.6 : 0.3);
    dots += `<circle cx="${sx}" cy="${y+50}" r="${r}" fill="${fill}" opacity="${op}"/>`;
    if (isLandmark) {
      dots += `<text x="${sx}" y="${y+68}" fill="${isHeld?'#e94560':'#ffc107'}" font-size="8" text-anchor="middle">${LANDMARK_LABELS[stId]||''}</text>`;
    }
  });

  // Held info
  const heldInfo = isExc && sl.held_station
    ? `<text x="1320" y="${y+50}" fill="#e94560" font-size="11">\u23F8 ${sl.held_station} / ${sl.held_wip_id}</text>`
    : '';

  // Detail affordance
  const detailAfford = isSel
    ? `<rect x="1555" y="${y+36}" width="72" height="22" rx="3" fill="#0d2b3e" stroke="#17a2b8" stroke-width="1" class="fb-detail-btn" data-sl="${sl.sub_line_id}" style="cursor:pointer"/><text x="1590" y="${y+52}" fill="#17a2b8" font-size="10" text-anchor="middle" class="fb-detail-btn" data-sl="${sl.sub_line_id}" style="cursor:pointer;pointer-events:none">\u2197 Detail</text>`
    : '';

  return `
    <g class="assy-lane" data-sl="${sl.sub_line_id}" style="cursor:pointer;${selStyle}">
      <rect x="40" y="${y}" width="${laneW}" height="88" rx="4" fill="${isExc?'#1a1015':c.fill}"${excStroke}/>
      <text x="56" y="${y+22}" fill="${isExc?'#e94560':c.accent}" font-size="14" font-weight="600">${sl.sub_line_id}</text>
      <rect x="160" y="${y+8}" width="80" height="20" rx="3" fill="${isExc?'#4a1a1a':'#1b4332'}"/>
      <text x="200" y="${y+24}" fill="${statusColor}" font-size="11" text-anchor="middle" font-weight="600">${statusLabel}</text>
      <text x="260" y="${y+24}" fill="#666" font-size="10">${sl.variant.toUpperCase()}</text>
      <rect x="250" y="${y+38}" width="1050" height="6" rx="3" fill="${isExc?'#1a1010':'#1a2740'}"/>
      ${dots}
      ${heldInfo}
      ${detailAfford}
      <text x="1330" y="${y+58}" fill="#777" font-size="10">WIP:${sl.wips_on_line}  OUT:${sl.motors_released}  DW:${sl.dwell_number}</text>
      <text x="1520" y="${y+58}" fill="#555" font-size="9">t=${sl.simulation_time_s.toFixed(0)}s</text>
    </g>`;
}


/* ==============================
   Frame A → Frame B Navigation

   INVARIANT: At most one frontend AUTO timer may invoke
   /assy-demo/step at any moment. Frame A timer is stopped
   when entering Frame B; Frame B timer is stopped when
   leaving. No competing step sources.
   ============================== */
function openFrameB(subLineId) {
  // Stop Frame A AUTO timer before entering Frame B
  if (ctrl._autoTimer) ctrl.stopAuto();
  document.getElementById('frame-a').style.display = 'none';
  document.getElementById('frame-b').style.display = 'flex';
  document.getElementById('frame-b').style.flexDirection = 'column';
  document.getElementById('frame-b').style.height = '100vh';
  ctrlB._initZoomPan();
  // Sync speed/scenario from Frame A
  ctrlB._speed = ctrl._speed;
  ctrlB._scenario = ctrl._scenario;
  ctrlB.init(subLineId);
}

function closeFrameB() {
  // Stop Frame B AUTO timer before leaving
  if (ctrlB._autoTimer) ctrlB.stopAuto();
  document.getElementById('frame-b').style.display = 'none';
  document.getElementById('frame-a').style.display = 'flex';
  document.getElementById('frame-a').style.flexDirection = 'column';
  document.getElementById('frame-a').style.height = '100vh';
  // Fresh overview from backend, not stale cache
  ctrl.refreshOverview().then(() => ctrl._refreshLaneStyles());
}


/* ==============================
   M6-S04B-I09-P02 — VF Visual Primitive Library
   ============================== */

// Position → visual token mapping (post-index snapshot, DG06-01-C02 frozen)
const VF_TOKEN = {
  'PRE-ASSY':'STATOR','AP01':'STATOR','AP02':'STATOR','AP03':'STATOR','AP04':'STATOR',
  'AP05':'JOINED','AP06':'PRETEST','AP07':'TESTED','AP08':'TESTED','AP09':'TESTED',
  'AP10':'PACKED','AP11':'PACKED'
};
const VF_TOKEN_LABEL = {STATOR:'STATOR',JOINED:'JOINED',PRETEST:'PRE-TEST',TESTED:'TESTED',PACKED:'PACKED'};

const VF = {
  // Wooden pallet carrier
  pallet(x, y) {
    const w=72, h=24;
    return `<rect x="${x-w/2}" y="${y}" width="${w}" height="${h}" rx="3" fill="var(--vf-pallet-wood)"/>
      <line x1="${x-w/2+4}" y1="${y+8}" x2="${x+w/2-4}" y2="${y+8}" stroke="#B08050" stroke-width="0.8" opacity="0.5"/>
      <line x1="${x-w/2+4}" y1="${y+16}" x2="${x+w/2-4}" y2="${y+16}" stroke="#B08050" stroke-width="0.8" opacity="0.5"/>`;
  },

  // STATOR ASSY — circular housing with central opening
  statorAssy(x, y) {
    const r=15;
    return `<circle cx="${x}" cy="${y}" r="${r}" fill="var(--vf-obj-stator)" stroke="#1FA0B0" stroke-width="1.5"/>
      <circle cx="${x}" cy="${y}" r="6" fill="var(--vf-bg-canvas)" opacity="0.6"/>
      <rect x="${x-12}" y="${y-8}" width="6" height="4" rx="1" fill="#1FA0B0" opacity="0.7"/>
      <rect x="${x+6}" y="${y-8}" width="6" height="4" rx="1" fill="#1FA0B0" opacity="0.7"/>`;
  },

  // ROTOR — elongated shaft
  rotor(x, y) {
    return `<rect x="${x-18}" y="${y-5}" width="36" height="10" rx="5" fill="var(--vf-obj-rotor)" stroke="#D09030" stroke-width="1"/>
      <rect x="${x-2}" y="${y-6}" width="4" height="12" rx="2" fill="#D09030"/>
      <line x1="${x-15}" y1="${y}" x2="${x+15}" y2="${y}" stroke="#C08028" stroke-width="1" opacity="0.5"/>`;
  },

  // MTR JOINED — compact cylindrical motor body
  motorJoined(x, y) {
    return `<rect x="${x-14}" y="${y-9}" width="28" height="18" rx="6" fill="var(--vf-obj-joined)" stroke="#308A72" stroke-width="1.2"/>
      <circle cx="${x}" cy="${y}" r="3" fill="#308A72" opacity="0.6"/>
      <rect x="${x-6}" y="${y-12}" width="4" height="3" rx="1" fill="#308A72" opacity="0.5"/>
      <rect x="${x+2}" y="${y-12}" width="4" height="3" rx="1" fill="#308A72" opacity="0.5"/>`;
  },

  // MTR PRE-TEST — complete motor body with mounting feet
  motorPreTest(x, y) {
    return `<rect x="${x-16}" y="${y-10}" width="32" height="20" rx="7" fill="var(--vf-obj-pretest)" stroke="#2E7098" stroke-width="1.2"/>
      <circle cx="${x}" cy="${y}" r="3.5" fill="#2E7098" opacity="0.5"/>
      <rect x="${x-18}" y="${y-5}" width="4" height="5" rx="1" fill="var(--vf-obj-pretest)" stroke="#2E7098" stroke-width="0.8"/>
      <rect x="${x+14}" y="${y-5}" width="4" height="5" rx="1" fill="var(--vf-obj-pretest)" stroke="#2E7098" stroke-width="0.8"/>
      <circle cx="${x-10}" cy="${y+2}" r="1.5" fill="#2E7098" opacity="0.4"/>
      <circle cx="${x+10}" cy="${y+2}" r="1.5" fill="#2E7098" opacity="0.4"/>`;
  },

  // TESTED MTR — motor body + test-complete marker
  motorTested(x, y) {
    return `<rect x="${x-16}" y="${y-10}" width="32" height="20" rx="7" fill="var(--vf-obj-pretest)" stroke="#2E7098" stroke-width="1.2"/>
      <circle cx="${x}" cy="${y}" r="3.5" fill="#2E7098" opacity="0.5"/>
      <rect x="${x-18}" y="${y-5}" width="4" height="5" rx="1" fill="var(--vf-obj-pretest)" stroke="#2E7098" stroke-width="0.8"/>
      <rect x="${x+14}" y="${y-5}" width="4" height="5" rx="1" fill="var(--vf-obj-pretest)" stroke="#2E7098" stroke-width="0.8"/>
      <circle cx="${x+12}" cy="${y-8}" r="4" fill="var(--vf-state-pass)" opacity="0.8"/>
      <text x="${x+12}" y="${y-5}" fill="#fff" font-size="6" text-anchor="middle" font-weight="bold">\u2713</text>`;
  },

  // PACKED GOODS — carton on pallet
  packedGoods(x, y) {
    return `<rect x="${x-16}" y="${y-10}" width="32" height="20" rx="4" fill="var(--vf-obj-packed)" stroke="#9A6838" stroke-width="1.2"/>
      <line x1="${x}" y1="${y-10}" x2="${x}" y2="${y+10}" stroke="#9A6838" stroke-width="0.8" opacity="0.4"/>
      <line x1="${x-16}" y1="${y}" x2="${x+16}" y2="${y}" stroke="#9A6838" stroke-width="0.8" opacity="0.4"/>
      <rect x="${x-8}" y="${y-11}" width="5" height="2" rx="1" fill="#9A6838" opacity="0.5"/>
      <rect x="${x+3}" y="${y-11}" width="5" height="2" rx="1" fill="#9A6838" opacity="0.5"/>`;
  },

  // State overlay — quality state only, never implies category
  stateOverlay(x, y, state) {
    if (!state || state==='PASS'|| state==='clear'|| state==='CLEAR') return '';
    const isHold = state==='HOLD'||state==='retest_pending'||state==='reinspect_pending';
    const isTerminal = state==='FAILED_FINAL'||state==='failed_final';
    const color = isHold ? 'var(--vf-state-hold)' : 'var(--vf-state-fail)';
    const r = isTerminal ? 7 : 5;
    return `<rect x="${x+10}" y="${y-18}" width="${r*2}" height="${r*2}" rx="2" fill="${color}" opacity="0.9"/>
      <text x="${x+10+r}" y="${y-9}" fill="#fff" font-size="${r+2}" text-anchor="middle" font-weight="bold">!</text>`;
  },

  // Equipment icons (small plan-view SVG)
  joinIcon(x, y) {
    return `<circle cx="${x}" cy="${y}" r="7" fill="none" stroke="#B8860B" stroke-width="1.2"/>
      <line x1="${x-5}" y1="${y}" x2="${x+5}" y2="${y}" stroke="#B8860B" stroke-width="1"/>
      <line x1="${x}" y1="${y-5}" x2="${x}" y2="${y+5}" stroke="#B8860B" stroke-width="1"/>`;
  },
  testIcon(x, y) {
    return `<rect x="${x-8}" y="${y-5}" width="16" height="10" rx="2" fill="none" stroke="var(--vf-state-selected)" stroke-width="1.2"/>
      <text x="${x}" y="${y+3}" fill="var(--vf-state-selected)" font-size="7" text-anchor="middle">T</text>`;
  },
  visionIcon(x, y) {
    return `<rect x="${x-7}" y="${y-5}" width="14" height="8" rx="2" fill="none" stroke="var(--vf-state-selected)" stroke-width="1"/>
      <circle cx="${x}" cy="${y-1}" r="3" fill="none" stroke="var(--vf-state-selected)" stroke-width="0.8"/>
      <circle cx="${x}" cy="${y-1}" r="1" fill="var(--vf-state-selected)"/>`;
  },
  finalIcon(x, y) {
    return `<rect x="${x-7}" y="${y-5}" width="14" height="10" rx="2" fill="none" stroke="var(--vf-state-selected)" stroke-width="1.2"/>
      <polyline points="${x-4},${y} ${x-1},${y+3} ${x+5},${y-3}" fill="none" stroke="var(--vf-state-pass)" stroke-width="1.5"/>`;
  },
  hmiIcon(x, y) {
    return `<rect x="${x-6}" y="${y-4}" width="12" height="8" rx="2" fill="#E8F0FE" stroke="var(--vf-text-muted)" stroke-width="0.8"/>
      <line x1="${x-3}" y1="${y+2}" x2="${x+3}" y2="${y+2}" stroke="var(--vf-text-muted)" stroke-width="0.6"/>`;
  },
  operatorIcon(x, y) {
    return `<circle cx="${x}" cy="${y-3}" r="4" fill="none" stroke="var(--vf-text-secondary)" stroke-width="1"/>
      <path d="M${x-5},${y+5} L${x+5},${y+5}" stroke="var(--vf-text-secondary)" stroke-width="1" fill="none"/>`;
  },
  packageIcon(x, y) {
    return `<rect x="${x-8}" y="${y-5}" width="16" height="10" rx="2" fill="none" stroke="#B68B57" stroke-width="1.2"/>
      <line x1="${x}" y1="${y-5}" x2="${x}" y2="${y+5}" stroke="#B68B57" stroke-width="0.6" opacity="0.5"/>
      <line x1="${x-8}" y1="${y}" x2="${x+8}" y2="${y}" stroke="#B68B57" stroke-width="0.6" opacity="0.5"/>`;
  },
  qualityCheckIcon(x, y) {
    return `<rect x="${x-7}" y="${y-4}" width="14" height="10" rx="2" fill="none" stroke="var(--vf-text-muted)" stroke-width="1"/>
      <polyline points="${x-4},${y} ${x-1},${y+3} ${x+5},${y-3}" fill="none" stroke="var(--vf-text-secondary)" stroke-width="1.2"/>`;
  },

  // Station cell scaffold
  stationCell(x, y, stId, archetype, occupied, isLandmark, isSel) {
    let html = '';
    const cx = x, cy = y + 45;
    // Archetype-specific icon + background
    let iconHtml = '', bgFill = '#F8F9FB', border = 'var(--vf-border-soft)', bw = isSel ? 2 : 1;
    if (archetype === 'INPUT') {
      iconHtml = VF.hmiIcon(cx+22, cy-12);
    } else if (archetype === 'JOIN') {
      iconHtml = VF.joinIcon(cx+22, cy-12);
      bgFill = '#FFFDF5'; border = '#B8860B'; bw = isSel ? 2 : 1.5;
    } else if (archetype === 'TEST') {
      iconHtml = VF.testIcon(cx+22, cy-12);
      border = 'var(--vf-state-selected)'; bw = isSel ? 2 : 1.2;
    } else if (archetype === 'VISION') {
      iconHtml = VF.visionIcon(cx+22, cy-12);
      border = 'var(--vf-state-selected)'; bw = isSel ? 2 : 1.2;
    } else if (archetype === 'FINAL') {
      iconHtml = VF.qualityCheckIcon(cx+22, cy-12);
      bgFill = '#F0F5FF'; border = 'var(--vf-state-selected)'; bw = isSel ? 2 : 1.2;
    } else if (archetype === 'PACK') {
      iconHtml = VF.packageIcon(cx+22, cy-12);
    } else if (archetype === 'CHECK') {
      iconHtml = VF.qualityCheckIcon(cx+22, cy-12);
    } else if (archetype === 'MANUAL') {
      iconHtml = VF.operatorIcon(cx+22, cy-12);
    } else {
      iconHtml = VF.operatorIcon(cx+22, cy-12);
    }
    html += `<rect x="${cx-40}" y="${cy-32}" width="80" height="64" rx="6" fill="${bgFill}" stroke="${border}" stroke-width="${bw}"/>`;
    html += iconHtml;
    html += `<text x="${cx}" y="${cy-18}" fill="var(--vf-text-secondary)" font-size="13" font-weight="600" text-anchor="middle">${stId}</text>`;
    if (isLandmark) {
      html += `<text x="${cx}" y="${cy-6}" fill="${archetype==='JOIN'?'#B8860B':'var(--vf-state-selected)'}" font-size="10" font-weight="600" text-anchor="middle">${FB_LANDMARKS[stId]}</text>`;
    }
    html += `<rect x="${cx-10}" y="${cy+30}" width="20" height="6" rx="2" fill="var(--vf-conveyor-roller)"/>`;
    return html;
  }
};
const FB_STATIONS = ['PRE-ASSY','AP01','AP02','AP03','AP04','AP05','AP06','AP07','AP08','AP09','AP10','AP11'];
const FB_LANDMARKS = { AP04:'JOIN', AP06:'TEST', AP08:'VISION', AP11:'FINAL' };
// Station X positions on the 1920 canvas (RIGHT→LEFT flow, I09-P01)
// PRE-ASSY rightmost (~1780), AP11 leftmost (~680)
const FB_STATION_X = [1780,1680,1580,1480,1380,1280,1180,1080,980,880,780,680];
const FB_CANVAS_W = 1920, FB_CANVAS_H = 700;
const FB_CONTENT_BOUNDS = { x:100, y:190, w:1720, h:320 };

const ctrlB = {
  _subLineId: 'ASSY-SL01',
  _autoTimer: null,
  _speed: 1.0,
  _scenario: 'HAPPY_PATH',
  _lastSnapshot: null,
  _liveStatus: 'INIT',
  _selectedStation: null,
  _selectedWipId: null,
  _inspectorOpen: false,

  // Zoom/Pan state
  _zoomLevel: 1,
  _panX: 0,
  _panY: 0,

  async init(subLineId) {
    // Observational only — does NOT reset runtime.
    this._subLineId = subLineId;
    this._selectedStation = null;
    this._selectedWipId = null;
    this._inspectorOpen = false;
    this._zoomLevel = 1; this._panX = 0; this._panY = 0;
    // Sync UI controls from carried-over values
    document.getElementById('fb-scenario-select').value = this._scenario || 'HAPPY_PATH';
    document.getElementById('fb-speed-select').value = String(this._speed);
    await this.refresh();
  },

  async reset() {
    // Explicit user RESET action — calls backend reset
    this.stopAuto();
    this._scenario = document.getElementById('fb-scenario-select').value;
    this._selectedStation = null;
    this._selectedWipId = null;
    this._inspectorOpen = false;
    this._zoomLevel = 1; this._panX = 0; this._panY = 0;
    await this.call('reset', { scenario: this._scenario });
    await this.refresh();
  },

  async step() {
    await this.call('step');
    await this.refresh();
  },

  back() { this.stopAuto(); closeFrameB(); },

  toggleAuto() {
    if (this._autoTimer) { this.stopAuto(); return; }
    this.startAuto();
  },

  startAuto() {
    document.getElementById('fb-btn-auto').textContent = '\u23F9 STOP';
    document.getElementById('fb-btn-pause').disabled = false;
    this._autoTimer = setInterval(() => this.step(), Math.round(1000 / this._speed));
  },

  stopAuto() {
    if (this._autoTimer) { clearInterval(this._autoTimer); this._autoTimer = null; }
    document.getElementById('fb-btn-auto').textContent = '\u25B6\u25B6 AUTO';
    document.getElementById('fb-btn-pause').disabled = true;
  },

  pause() { if (this._autoTimer) this.stopAuto(); },

  setSpeed(val) {
    this._speed = parseFloat(val);
    if (this._autoTimer) { this.stopAuto(); this.startAuto(); }
  },

  setScenario(val) {
    this._scenario = val;
    // Cross-frame sync: keep Frame A global scenario in agreement
    ctrl._scenario = val;
    const selA = document.getElementById('scenario-select');
    if (selA) selA.value = val;
    this.reset();
  },

  async call(action, body) {
    const opts = body ? { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body) } : { method:'POST' };
    const resp = await fetch(`${API}/${action}`, opts);
    if (!resp.ok) throw new Error(`${action}: ${resp.status}`);
    return resp.json();
  },

  async refresh() {
    try {
      const resp = await fetch(`${API}/sub-line/${encodeURIComponent(this._subLineId)}`);
      if (!resp.ok) throw new Error(`detail: ${resp.status}`);
      const snap = await resp.json();
      this._lastSnapshot = snap;
      this._liveStatus = 'LIVE';
      // NOTE: snap.scenario is the effective sub-line scenario,
      // NOT the global requested demo scenario.  Do not overwrite
      // ctrlB._scenario or the scenario dropdown from snap.scenario.
      this.render(snap);
    } catch (_) {
      this._liveStatus = this._lastSnapshot ? 'STALE' : 'UNAVAILABLE';
      this.renderStatus();
    }
  },

  renderStatus() {
    const el = document.getElementById('fb-live-status');
    if (!el) return;
    if (this._liveStatus === 'LIVE') { el.textContent = '\u25CF LIVE'; el.style.color = '#4ecca3'; }
    else if (this._liveStatus === 'STALE') { el.textContent = '\u25CB STALE'; el.style.color = '#ffc107'; }
    else { el.textContent = '\u2715 BACKEND UNAVAILABLE'; el.style.color = '#e94560'; }
  },

  /* ---------- SVG Render ---------- */
  render(snap) {
    this.renderStatus();
    if (!snap) return;

    // Header
    document.getElementById('fb-sub-line-id').textContent = snap.sub_line_id || this._subLineId;
    document.getElementById('fb-variant').textContent = (snap.variant||'').toUpperCase();
    document.getElementById('fb-sim-time').textContent = `t=${(snap.simulation_time_s||0).toFixed(0)}s`;
    document.getElementById('fb-dwell').textContent = `DWELL ${snap.dwell_number||0}`;
    document.getElementById('fb-scenario').textContent = snap.scenario || this._scenario;

    // Line state badge
    const lsEl = document.getElementById('fb-line-state');
    const ls = snap.line_state || 'stopped';
    lsEl.textContent = ls.toUpperCase();
    lsEl.className = 'fb-state-badge';
    if (ls === 'operating') { lsEl.style.background = '#1b4332'; lsEl.style.color = '#4ecca3'; }
    else if (ls === 'stopped') { lsEl.style.background = '#1a2332'; lsEl.style.color = '#888'; }
    else if (ls === 'ready_to_index') { lsEl.style.background = '#0d2b3e'; lsEl.style.color = '#17a2b8'; }
    else if (ls === 'indexing') { lsEl.style.background = '#4a1a1a'; lsEl.style.color = '#e94560'; }
    else { lsEl.style.background = '#1a2332'; lsEl.style.color = '#888'; }

    // Production text
    const prod = snap.production || {};
    document.getElementById('fb-prod-text').textContent =
      `Created: ${prod.motors_created||0}  Released: ${prod.motors_released||0}  On Line: ${prod.wips_on_line||0}  Holds: ${prod.active_quality_holds||0}`;

    // Refresh persistence: if WIP selected, update its current position
    if (this._inspectorOpen && this._selectedWipId) {
      const pos = (snap.positions||[]).find(p => p.wip_id === this._selectedWipId);
      if (pos) {
        this._selectedStation = pos.position_id;
      } else {
        // WIP exited — keep _selectedWipId, clear station
        this._selectedStation = null;
      }
    }

    // Build position lookup
    const posMap = {};
    for (const p of (snap.positions||[])) posMap[p.position_id] = p;

    // Render stations
    const stationsG = document.getElementById('fb-stations');
    if (!stationsG) return;
    let html = '';
    const selSt = this._selectedStation;

    // SSO2 input label
    html += `<text x="26" y="400" fill="#4ecca3" font-size="9" text-anchor="middle">INPUT</text>`;

    FB_STATIONS.forEach((stId, si) => {
      const sx = FB_STATION_X[si];
      const sy = 340;
      const p = posMap[stId] || {};
      const isLandmark = FB_LANDMARKS[stId];
      const isOcc = p.is_occupied && p.wip_id;
      const isHeld = p.is_quality_hold;
      const isSel = selSt === stId;
      const wipType = p.wip_type || '';
      const qResult = p.latest_quality_result || '';
      const isReleased = p.manufacturing_status === 'released';

      // I09-P02: determine station archetype + visual token
      let archetype = 'MANUAL';
      if (stId === 'PRE-ASSY') archetype = 'INPUT';
      else if (stId === 'AP03') archetype = 'CHECK';
      else if (stId === 'AP04') archetype = 'JOIN';
      else if (stId === 'AP06') archetype = 'TEST';
      else if (stId === 'AP08') archetype = 'VISION';
      else if (stId === 'AP09') archetype = 'PACK';
      else if (stId === 'AP10') archetype = 'PACK';
      else if (stId === 'AP11') archetype = 'FINAL';

      const tokenType = VF_TOKEN[stId] || 'STATOR';
      const tokenLabel = VF_TOKEN_LABEL[tokenType] || '';

      // Station border treatment
      let stBorder = isSel ? 'var(--vf-state-selected)' : 'var(--vf-border-soft)';
      if (isHeld) stBorder = 'var(--vf-state-fail)';

      html += `<g class="fb-station" data-station="${stId}" style="cursor:pointer">`;
      html += VF.stationCell(sx, sy, stId, archetype, isOcc, isLandmark, isSel);

      if (isOcc) {
        // Pallet + WIP token group
        const tokenX = sx, tokenY = sy + 60;
        html += `<g class="fb-wip-token" data-wip="${p.wip_id}" style="cursor:pointer">`;
        html += VF.pallet(tokenX, tokenY);
        // WIP visual by position
        if (tokenType === 'STATOR') html += VF.statorAssy(tokenX, tokenY - 6);
        else if (tokenType === 'JOINED') html += VF.motorJoined(tokenX, tokenY - 6);
        else if (tokenType === 'PRETEST') html += VF.motorPreTest(tokenX, tokenY - 6);
        else if (tokenType === 'TESTED') html += VF.motorTested(tokenX, tokenY - 6);
        else if (tokenType === 'PACKED') html += VF.packedGoods(tokenX, tokenY - 6);
        // State overlay
        if (isHeld || qResult === 'FAIL' || qResult === 'NG') {
          html += VF.stateOverlay(tokenX, tokenY, isHeld ? 'HOLD' : qResult);
        }
        // WIP ID label
        html += `<text x="${tokenX}" y="${tokenY+22}" fill="var(--vf-text-muted)" font-size="9" text-anchor="middle">${p.wip_id}</text>`;
        // Token label
        html += `<text x="${tokenX}" y="${tokenY-20}" fill="var(--vf-text-secondary)" font-size="9" text-anchor="middle" font-weight="600">${tokenLabel}</text>`;
        if (p.carrier_id) {
          html += `<text x="${tokenX}" y="${tokenY+33}" fill="var(--vf-text-muted)" font-size="8" text-anchor="middle">${p.carrier_id}</text>`;
        }
        html += `</g>`;
      } else {
        // Empty station
        html += `<text x="${sx}" y="${sy+68}" fill="var(--vf-text-muted)" font-size="14" text-anchor="middle">\u2014</text>`;
      }

      if (isHeld && p.held_reason) {
        html += `<text x="${sx}" y="${sy+96}" fill="var(--vf-state-fail)" font-size="9" text-anchor="middle">${p.held_reason}</text>`;
      }

      html += `</g>`;
    });

    // LINE OUT arrow indicator text (LEFT side)
    html += `<text x="120" y="355" fill="var(--vf-state-selected)" font-size="10">LINE OUT \u2190</text>`;

    // AP04 genealogy context label on canvas
    const genealogy = snap.genealogy || [];
    if (genealogy.length > 0) {
      const latest = genealogy[genealogy.length - 1];
      const ap04x = FB_STATION_X[4]; // AP04 = index 4
      // ROTOR visual at RSO2 branch point (above AP04)
      html += `<g transform="translate(${ap04x}, 300)">${VF.rotor(0, -8)}</g>`;
    }

    stationsG.innerHTML = html;

    // Physical highlights
    this._applyHighlights();

    // Bind station clicks
    this._bindStationClicks();

    // Bind WIP token clicks (independent, no double-trigger)
    this._bindWipTokenClicks();

    // Render event strip
    this._renderEventStrip(snap);

    // Render genealogy context in right panel
    this._renderGenealogyContext(snap);

    // Render Inspector
    this._renderInspector(snap);

    // Apply zoom
    this.applyViewBox();
  },

  _applyHighlights() {
    // Remove old highlights
    document.querySelectorAll('#fb-stations .fb-station').forEach(el => {
      const rect = el.querySelector('rect');
      if (rect) rect.style.filter = '';
    });
    // Apply selection highlight
    if (this._selectedStation) {
      const el = document.querySelector(`#fb-stations .fb-station[data-station="${this._selectedStation}"]`);
      if (el) {
        const rect = el.querySelector('rect');
        if (rect) rect.style.filter = 'drop-shadow(0 0 4px #17a2b8)';
      }
    }
  },

  _bindStationClicks() {
    document.querySelectorAll('#fb-stations .fb-station').forEach(el => {
      el.addEventListener('click', (e) => {
        if (e.target.closest('.fb-wip-token')) return;
        const stId = el.getAttribute('data-station');
        this.selectStation(stId);
      });
    });
  },

  _bindWipTokenClicks() {
    document.querySelectorAll('#fb-stations .fb-wip-token').forEach(el => {
      el.addEventListener('click', (e) => {
        e.stopPropagation();
        const wipId = el.getAttribute('data-wip');
        if (wipId) this.selectWip(wipId);
      });
    });
  },

  /* ---------- Selection Model ---------- */
  selectStation(stId) {
    if (this._selectedStation === stId) { this.closeInspector(); return; }
    this._selectedStation = stId;
    this._selectedWipId = null;

    // Derive WIP from current snapshot
    const snap = this._lastSnapshot;
    if (snap) {
      const pos = (snap.positions||[]).find(p => p.position_id === stId);
      if (pos && pos.wip_id) this._selectedWipId = pos.wip_id;
    }
    this._inspectorOpen = true;
    if (snap) { this._applyHighlights(); this._renderInspector(snap); }
  },

  selectWip(wipId) {
    this._selectedWipId = wipId;
    this._selectedStation = null;
    // Find current station from snapshot
    const snap = this._lastSnapshot;
    if (snap) {
      const pos = (snap.positions||[]).find(p => p.wip_id === wipId);
      if (pos) this._selectedStation = pos.position_id;
    }
    this._inspectorOpen = true;
    if (snap) { this._applyHighlights(); this._renderInspector(snap); }
  },

  selectEvent(stationId, wipId) {
    this._selectedWipId = wipId || null;
    this._inspectorOpen = true;
    const snap = this._lastSnapshot;
    if (snap && wipId) {
      const pos = (snap.positions||[]).find(p => p.wip_id === wipId);
      this._selectedStation = pos ? pos.position_id : null;
    } else if (snap && stationId && !wipId) {
      this._selectedStation = stationId;
    } else {
      this._selectedStation = null;
    }
    if (snap) { this._applyHighlights(); this._renderInspector(snap); }
  },

  closeInspector() {
    this._inspectorOpen = false;
    this._selectedStation = null;
    this._selectedWipId = null;
    this._applyHighlights();
    this._renderInspector(this._lastSnapshot);
  },

  /* I09-P01 popup scaffold */
  openPopup() { document.getElementById('vf-popup').classList.add('vf-popup-open'); },
  closePopup() { document.getElementById('vf-popup').classList.remove('vf-popup-open'); },

  /* ---------- Inspector Render ---------- */
  _renderInspector(snap) {
    const insp = document.getElementById('fb-inspector');
    if (!insp) return;

    if (!this._inspectorOpen || !snap) {
      insp.className = 'fb-inspector-collapsed';
      document.getElementById('fb-insp-title').textContent = 'Inspector';
      document.getElementById('fb-insp-summary-content').innerHTML = '<span class="fb-insp-empty">Select a station, WIP, or event</span>';
      this._clearInspectorSections();
      return;
    }
    insp.className = 'fb-inspector-open';

    const stId = this._selectedStation;
    const wipId = this._selectedWipId;
    const posMap = {};
    for (const p of (snap.positions||[])) posMap[p.position_id] = p;

    const pos = stId ? (posMap[stId] || null) : null;
    const title = stId ? `${stId}${pos&&pos.station_label?': '+pos.station_label:''}` : (wipId||'Inspector');
    document.getElementById('fb-insp-title').textContent = title;

    // --- Summary ---
    this._renderSummary(pos, wipId, snap);

    // --- Quality History ---
    this._renderQualityHistory(wipId, snap);

    // --- Measurements ---
    this._renderMeasurements(wipId, snap);

    // --- Checklist ---
    this._renderChecklist(wipId, snap);

    // --- Genealogy ---
    this._renderInspGenealogy(wipId, snap);
  },

  _clearInspectorSections() {
    ['fb-insp-quality-content','fb-insp-measurements-content','fb-insp-checklist-content','fb-insp-genealogy-content'].forEach(id => {
      const el = document.getElementById(id); if (el) el.innerHTML = '';
    });
    ['fb-insp-measurements','fb-insp-checklist','fb-insp-genealogy'].forEach(id => {
      const el = document.getElementById(id); if (el) el.style.display = 'none';
    });
  },

  _renderSummary(pos, wipId, snap) {
    const el = document.getElementById('fb-insp-summary-content');
    if (!el) return;

    if (pos && pos.is_occupied && pos.wip_id) {
      const qColor = pos.latest_quality_result === 'PASS' ? '#4ecca3' : pos.latest_quality_result ? '#e94560' : '#8899bb';
      let html = `<div class="fb-insp-row"><span class="fb-insp-k">Station</span><span class="fb-insp-v">${pos.position_id} — ${pos.station_label||pos.position_id}</span></div>`;
      html += `<div class="fb-insp-row"><span class="fb-insp-k">WIP</span><span class="fb-insp-v" style="color:${pos.wip_type==='SSO2'?'#4ecca3':'#ffc107'};font-weight:600">${pos.wip_id}</span></div>`;
      html += `<div class="fb-insp-row"><span class="fb-insp-k">Type</span><span class="fb-insp-v">${pos.wip_type||'—'}</span></div>`;
      if (pos.carrier_id) html += `<div class="fb-insp-row"><span class="fb-insp-k">Carrier</span><span class="fb-insp-v">${pos.carrier_id}</span></div>`;
      html += `<div class="fb-insp-row"><span class="fb-insp-k">Mfg Status</span><span class="fb-insp-v">${pos.manufacturing_status||'active'}</span></div>`;
      html += `<div class="fb-insp-row"><span class="fb-insp-k">Quality</span><span class="fb-insp-v" style="color:${qColor}">${pos.latest_quality_result||'clear'}${pos.attempt_number>1?' #'+pos.attempt_number:''}</span></div>`;
      if (pos.is_quality_hold) html += `<div class="fb-insp-row"><span class="fb-insp-k">HOLD</span><span class="fb-insp-v" style="color:#e94560;font-weight:600">${pos.held_reason||'Active'}</span></div>`;
      el.innerHTML = html;
    } else if (pos && !pos.is_occupied) {
      el.innerHTML = `<div class="fb-insp-row"><span class="fb-insp-k">Station</span><span class="fb-insp-v">${pos.position_id} — ${pos.station_label||pos.position_id}</span></div><div class="fb-insp-empty">EMPTY — no WIP at this station</div>`;
    } else if (wipId) {
      // WIP selected but may be historical/exited
      const histRecs = (snap.quality_records||[]).filter(qr => qr.wip_id === wipId);
      const onLine = (snap.positions||[]).some(p => p.wip_id === wipId);
      let html = `<div class="fb-insp-row"><span class="fb-insp-k">WIP</span><span class="fb-insp-v" style="font-weight:600">${wipId}</span></div>`;
      if (!onLine) html += `<div class="fb-insp-historical">HISTORICAL — NOT CURRENTLY ON LINE</div>`;
      html += `<div class="fb-insp-row"><span class="fb-insp-k">Records</span><span class="fb-insp-v">${histRecs.length} quality records available</span></div>`;
      el.innerHTML = html;
    } else {
      el.innerHTML = '<span class="fb-insp-empty">Select a station or WIP</span>';
    }
  },

  _renderQualityHistory(wipId, snap) {
    const el = document.getElementById('fb-insp-quality-content');
    if (!el) return;
    if (!wipId) { el.innerHTML = '<span class="fb-insp-empty">Select a WIP to see quality history</span>'; return; }

    const recs = (snap.quality_records||[]).filter(qr => qr.wip_id === wipId).sort((a,b) => a.simulation_time_s - b.simulation_time_s);
    if (!recs.length) { el.innerHTML = '<span class="fb-insp-empty">No quality records for this WIP</span>'; return; }

    let html = '';
    for (const r of recs) {
      const dColor = r.disposition === 'PASS' ? '#4ecca3' : '#e94560';
      html += `<div class="fb-insp-qr">
        <div class="fb-insp-qr-head">
          <span class="fb-insp-qr-station">${r.station_id}</span>
          <span style="color:${dColor};font-weight:600">${r.disposition}</span>
          <span style="color:#666">#${r.attempt_number}</span>
          <span style="color:#555;font-size:11px">t=${(r.simulation_time_s||0).toFixed(0)}s</span>
        </div>
        <div class="fb-insp-qr-type">${r.check_type||'?'}</div>`;
      if (r.reason_code) html += `<div class="fb-insp-qr-reason">Reason: ${r.reason_code}</div>`;
      html += `</div>`;
    }
    el.innerHTML = html;
  },

  _renderMeasurements(wipId, snap) {
    const section = document.getElementById('fb-insp-measurements');
    const el = document.getElementById('fb-insp-measurements-content');
    if (!section || !el) return;
    if (!wipId) { section.style.display = 'none'; return; }

    const recs = (snap.quality_records||[]).filter(qr => qr.wip_id === wipId && qr.measurements && qr.measurements.length > 0);
    if (!recs.length) { section.style.display = 'none'; return; }
    section.style.display = '';

    let html = '';
    for (const r of recs) {
      html += `<div class="fb-insp-meas-group"><div class="fb-insp-meas-station">${r.station_id} — ${r.check_type} #${r.attempt_number} <small>t=${(r.simulation_time_s||0).toFixed(0)}s</small></div>`;
      for (const m of (r.measurements||[])) {
        const v = m.value, lo = m.expected_min, hi = m.expected_max;
        let inRange = true;
        if (lo !== undefined && v < lo) inRange = false;
        if (hi !== undefined && v > hi) inRange = false;
        const rangeColor = inRange ? '#4ecca3' : '#e94560';
        const rangeLabel = inRange ? 'IN RANGE' : 'OUT OF RANGE';
        html += `<div class="fb-insp-meas-row">
          <span class="fb-insp-meas-name">${m.name}</span>
          <span class="fb-insp-meas-val">${v} ${m.unit||''}</span>
          ${lo!==undefined&&hi!==undefined?`<span class="fb-insp-meas-range">Expected ${lo}–${hi} ${m.unit||''}</span>`:''}
          ${lo!==undefined||hi!==undefined?`<span class="fb-insp-meas-inrange" style="color:${rangeColor}">${rangeLabel}</span>`:''}
        </div>`;
      }
      html += `</div>`;
    }
    el.innerHTML = html;
  },

  _renderChecklist(wipId, snap) {
    const section = document.getElementById('fb-insp-checklist');
    const el = document.getElementById('fb-insp-checklist-content');
    if (!section || !el) return;
    if (!wipId) { section.style.display = 'none'; return; }

    const recs = (snap.quality_records||[]).filter(qr => qr.wip_id === wipId && qr.checklist_items && qr.checklist_items.length > 0);
    if (!recs.length) { section.style.display = 'none'; return; }
    section.style.display = '';

    let html = '';
    for (const r of recs) {
      const dColor = r.disposition === 'PASS' ? '#4ecca3' : '#e94560';
      html += `<div class="fb-insp-cl-group">
        <div class="fb-insp-cl-head">${r.station_id} — ${r.check_type} <span style="color:${dColor};font-weight:600">${r.disposition}</span> #${r.attempt_number} <small>t=${(r.simulation_time_s||0).toFixed(0)}s</small></div>
        <div class="fb-insp-cl-items">`;
      for (const item of r.checklist_items) {
        html += `<div class="fb-insp-cl-item">&#8226; ${item}</div>`;
      }
      html += `</div></div>`;
    }
    el.innerHTML = html;
  },

  _renderInspGenealogy(wipId, snap) {
    const section = document.getElementById('fb-insp-genealogy');
    const el = document.getElementById('fb-insp-genealogy-content');
    if (!section || !el) return;
    if (!wipId || !wipId.startsWith('MTR')) { section.style.display = 'none'; return; }

    const gen = (snap.genealogy||[]).filter(g => g.child_wip_id === wipId);
    if (!gen.length) { section.style.display = ''; el.innerHTML = '<span class="fb-insp-empty">No genealogy record</span>'; return; }
    section.style.display = '';

    let html = '';
    for (const g of gen) {
      html += `<div class="fb-insp-gen-row">
        <span style="color:#ffc107">${(g.parent_wip_ids||[]).join(' + ')}</span>
        → <span style="color:#ffc107;font-weight:600">${g.child_wip_id}</span>
        <div style="color:#666;font-size:11px">@ ${g.join_station} t=${(g.join_time_s||0).toFixed(0)}s</div>
      </div>`;
    }
    el.innerHTML = html;
  },

  _renderEventStrip(snap) {
    const list = document.getElementById('fb-event-list');
    if (!list) return;
    const events = snap.recent_quality_events || [];
    let html = '';
    for (const e of events.slice(-12).reverse()) {
      const dColor = e.disposition === 'PASS' ? '#4ecca3' : '#e94560';
      const sid = e.station_id||'', wid = e.wip_id||'';
      html += `<div class="fb-qe-item fb-qe-clickable" data-ev-station="${sid}" data-ev-wip="${wid}">
        <span style="color:${dColor};font-weight:600">${e.disposition||'?'}</span>
        ${wid} @ ${sid} #${e.attempt||1}
        <small>t=${(e.simulation_time_s||0).toFixed(0)}s</small>
      </div>`;
    }
    if (!html) html = '<div style="color:#555;font-size:11px">No quality events</div>';
    list.innerHTML = html;

    // Bind event clicks
    list.querySelectorAll('.fb-qe-clickable').forEach(el => {
      el.addEventListener('click', () => {
        const sid = el.getAttribute('data-ev-station');
        const wid = el.getAttribute('data-ev-wip');
        this.selectEvent(sid, wid);
      });
    });
  },

  _renderGenealogyContext(snap) {
    const el = document.getElementById('fb-genealogy-text');
    if (!el) return;
    const genealogy = snap.genealogy || [];
    if (genealogy.length === 0) {
      el.textContent = 'No JOIN records yet';
      return;
    }
    let html = '';
    for (const g of genealogy.slice(-4).reverse()) {
      html += `<div style="padding:3px 0;border-bottom:1px solid #1a2332">`;
      html += `<span style="color:#ffc107">${g.parent_wip_ids.join(' + ')}</span>`;
      html += ` → <span style="color:#ffc107;font-weight:600">${g.child_wip_id}</span>`;
      html += ` <small style="color:#555">@ ${g.join_station} t=${(g.join_time_s||0).toFixed(0)}s</small>`;
      html += `</div>`;
    }
    el.innerHTML = html;
  },

  /* ---------- Zoom / Pan ---------- */
  svgPointFromClient(svg, clientX, clientY) {
    const pt = svg.createSVGPoint();
    pt.x = clientX; pt.y = clientY;
    const ctm = svg.getScreenCTM();
    if (!ctm) return null;
    return pt.matrixTransform(ctm.inverse());
  },

  applyViewBox() {
    const svg = document.getElementById('fb-canvas-svg');
    if (!svg) return;
    const vw = FB_CANVAS_W / this._zoomLevel;
    const vh = FB_CANVAS_H / this._zoomLevel;
    const vx = this._panX * FB_CANVAS_W / 1920;
    const vy = this._panY * FB_CANVAS_H / 700;
    svg.setAttribute('viewBox', `${vx} ${vy} ${vw} ${vh}`);
  },

  zoomOut() { this._zoomLevel = Math.max(0.5, this._zoomLevel - 0.25); this.applyViewBox(); },
  zoomIn() { this._zoomLevel = Math.min(2.0, this._zoomLevel + 0.25); this.applyViewBox(); },
  zoomReset() { this._zoomLevel = 1; this._panX = 0; this._panY = 0; this.applyViewBox(); },

  zoomFit() {
    const wrap = document.getElementById('fb-canvas-wrap');
    const wrapW = wrap ? wrap.clientWidth : 1920;
    const wrapH = wrap ? wrap.clientHeight : 700;
    const c = FB_CONTENT_BOUNDS;
    const scaleX = wrapW / c.w, scaleY = wrapH / c.h;
    const scale = Math.min(scaleX, scaleY);
    this._zoomLevel = FB_CANVAS_W / (c.w / scale);
    this._panX = c.x * FB_CANVAS_W / 1920;
    this._panY = c.y * FB_CANVAS_H / 700;
    this.applyViewBox();
  },

  _initZoomPan() {
    const wrap = document.getElementById('fb-canvas-wrap');
    const svg = document.getElementById('fb-canvas-svg');
    if (!wrap || !svg) return;
    if (wrap._fbZoomInited) return;
    wrap._fbZoomInited = true;

    // Wheel zoom
    wrap.addEventListener('wheel', (e) => {
      e.preventDefault();
      const p = this.svgPointFromClient(svg, e.clientX, e.clientY);
      if (!p) return;
      const oldZoom = this._zoomLevel;
      const delta = -e.deltaY * 0.005;
      this._zoomLevel = Math.max(0.5, Math.min(2.0, oldZoom + delta));
      if (this._zoomLevel === oldZoom) return;
      this.applyViewBox();
      const q = this.svgPointFromClient(svg, e.clientX, e.clientY);
      if (!q) return;
      this._panX += (p.x - q.x) * 1920 / FB_CANVAS_W;
      this._panY += (p.y - q.y) * 700 / FB_CANVAS_H;
      this.applyViewBox();
    }, { passive: false });

    // Left-drag pan
    let dragging = false, startX, startY, startPanX, startPanY;
    svg.addEventListener('mousedown', (e) => {
      if (e.target === svg || (e.target.tagName === 'rect' && !e.target.closest('.fb-station'))) {
        dragging = true; startX = e.clientX; startY = e.clientY;
        startPanX = this._panX; startPanY = this._panY;
        svg.style.cursor = 'grabbing'; e.preventDefault();
      }
    });
    window.addEventListener('mousemove', (e) => {
      if (!dragging) return;
      const dx = (e.clientX - startX) * (FB_CANVAS_W / 1920) / this._zoomLevel;
      const dy = (e.clientY - startY) * (FB_CANVAS_H / 700) / this._zoomLevel;
      this._panX = startPanX - dx; this._panY = startPanY - dy;
      this.applyViewBox();
    });
    window.addEventListener('mouseup', () => {
      if (dragging) { dragging = false; svg.style.cursor = ''; }
    });
  }
};
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
    this.render(await this.call('step'));
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
    const opts = body ? { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body) } : { method:'POST' };
    const resp = await fetch(`${API}/${action}`, opts);
    return resp.json();
  },

  render(snap) {
    if (!snap||!snap.positions) return;
    document.getElementById('sim-time').textContent = `t=${snap.simulation_time_s.toFixed(0)}s`;
    const ls=document.getElementById('line-state'); ls.textContent=snap.line_state.toUpperCase(); ls.className='state '+snap.line_state;
    document.getElementById('dwell').textContent=`Dwell ${snap.dwell_number}`;
    const c=document.getElementById('positions-container'); c.innerHTML='';
    for(const p of snap.positions){
      const d=document.createElement('div'); d.className='position';
      if(p.is_quality_hold)d.className+=' quality-hold'; else if(p.is_occupied)d.className+=' occupied';
      if(p.manufacturing_status==='released')d.className+=' released'; if(p.position_id==='AP04')d.className+=' ap04';
      d.innerHTML=`<div class="pos-id">${p.position_id}</div><div class="pos-label">${p.station_label}</div>${p.wip_id?`<div class="wip-info"><div class="wip-id ${p.wip_type}">${p.wip_id}</div>${p.carrier_id?`<div class="carrier">${p.carrier_id}</div>`:''}${p.latest_quality_result?`<div class="quality-badge ${p.latest_quality_result.toLowerCase()}">${p.latest_quality_result}${p.attempt_number>1?' #'+p.attempt_number:''}</div>`:''}${p.is_quality_hold?'<div class="quality-badge hold">HOLD</div>':''}${p.manufacturing_status==='released'?'<div class="quality-badge pass">RELEASED</div>':''}</div>`:'<div style="color:#555;font-size:0.7em;margin-top:8px;">\u2014</div>'}`;
      c.appendChild(d);
    }
    const prod=snap.production||{};
    document.getElementById('motors-completed').textContent=prod.motors_created||0;
    document.getElementById('motors-released').textContent=prod.motors_released||0;
    document.getElementById('wips-on-line').textContent=prod.wips_on_line||0;
    document.getElementById('active-holds').textContent=prod.active_quality_holds||0;
    document.getElementById('rso2-buf').textContent=prod.rso2_buffer||0;
    const gl=document.getElementById('genealogy-list'); gl.innerHTML='';
    for(const g of(snap.genealogy||[]).slice(-6)){gl.innerHTML+=`<div class="genealogy-item"><b style="color:#ffc107">${g.child_wip_id}</b> \u2190 ${g.parent_wip_ids.join(' + ')}<br><small>t=${g.join_time_s.toFixed(0)}s @ ${g.join_station}</small></div>`;}
    const ql=document.getElementById('quality-events'); ql.innerHTML='';
    for(const e of(snap.recent_quality_events||[]).slice(-15)){ql.innerHTML+=`<div class="qe-item"><span class="qe-disp ${e.disposition}">${e.disposition}</span>${e.wip_id} @ ${e.station_id} #${e.attempt} <small>t=${e.simulation_time_s.toFixed(0)}s</small></div>`;}
    document.getElementById('scenario-display').textContent=snap.scenario||'HAPPY_PATH';
  }
};


/* ==============================
   Feature Detection + Boot
   ============================== */
async function detectS04B() {
  try { const r = await fetch(`${API}/overview`); return r.ok; } catch (_) { return false; }
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
