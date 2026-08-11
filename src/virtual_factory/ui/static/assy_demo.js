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
   M6-S04B-I05 Frame B Controller
   ============================== */
const FB_STATIONS = ['PRE-ASSY','AP01','AP02','AP03','AP04','AP05','AP06','AP07','AP08','AP09','AP10','AP11'];
const FB_LANDMARKS = { AP04:'JOIN', AP06:'TEST', AP08:'VISION', AP11:'FINAL' };
// Station X positions on the 1920 canvas (conveyor at y=380)
const FB_STATION_X = [140,240,340,440,540,640,740,840,940,1040,1140,1240];
const FB_CANVAS_W = 1920, FB_CANVAS_H = 700;
const FB_CONTENT_BOUNDS = { x:0, y:190, w:1920, h:320 };

const ctrlB = {
  _subLineId: 'ASSY-SL01',
  _autoTimer: null,
  _speed: 1.0,
  _scenario: 'HAPPY_PATH',
  _lastSnapshot: null,
  _liveStatus: 'INIT',
  _selectedStation: null,

  // Zoom/Pan state
  _zoomLevel: 1,
  _panX: 0,
  _panY: 0,

  async init(subLineId) {
    // Observational only — does NOT reset runtime.
    // Runtime state, scenario, counters, WIP positions preserved.
    this._subLineId = subLineId;
    this._selectedStation = null;
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

  setScenario(val) { this._scenario = val; this.reset(); },

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
      // Sync scenario dropdown from live snapshot
      if (snap.scenario) {
        this._scenario = snap.scenario;
        const sel = document.getElementById('fb-scenario-select');
        if (sel) sel.value = snap.scenario;
      }
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

      // Station box
      let borderColor = '#1e3a5f';
      let bgColor = '#111d30';
      if (isLandmark && stId === 'AP04') { borderColor = '#ffc107'; bgColor = '#1a1a10'; }
      else if (isLandmark && stId === 'AP11') { borderColor = '#17a2b8'; bgColor = '#0d1a20'; }
      if (isHeld) { borderColor = '#e94560'; bgColor = '#1a1015'; }
      if (isReleased && stId === 'AP11') { borderColor = '#17a2b8'; bgColor = '#0d2b3e'; }
      if (isSel) { borderColor = '#fff'; }

      html += `<g class="fb-station" data-station="${stId}" style="cursor:pointer">`;
      html += `<rect x="${sx-44}" y="${sy}" width="88" height="90" rx="4" fill="${bgColor}" stroke="${borderColor}" stroke-width="${isSel||isHeld?2:1}"/>`;

      // Station ID + landmark
      html += `<text x="${sx}" y="${sy+18}" fill="${isHeld?'#e94560':'#8899bb'}" font-size="15" font-weight="600" text-anchor="middle">${stId}</text>`;
      if (isLandmark) {
        html += `<text x="${sx}" y="${sy+34}" fill="${stId==='AP04'?'#ffc107':stId==='AP11'?'#17a2b8':'#ffc107'}" font-size="11" font-weight="600" text-anchor="middle">${FB_LANDMARKS[stId]}</text>`;
      }

      if (isOcc) {
        // Carrier
        const carrierY = sy + (isLandmark ? 42 : 40);
        html += `<rect x="${sx-38}" y="${carrierY}" width="76" height="28" rx="3" fill="none" stroke="#1e3a5f" stroke-width="1"/>`;
        if (p.carrier_id) {
          html += `<text x="${sx}" y="${carrierY+12}" fill="#8899bb" font-size="11" font-weight="400" text-anchor="middle">${p.carrier_id}</text>`;
        }
        // WIP
        const wipY = carrierY + 23;
        const wipColor = wipType === 'SSO2' ? '#4ecca3' : '#ffc107';
        html += `<text x="${sx}" y="${wipY}" fill="${wipColor}" font-size="14" font-weight="600" text-anchor="middle">${p.wip_id}</text>`;

        // Quality badge
        const badgeY = wipY + 14;
        if (qResult && !isHeld) {
          const qColor = qResult === 'PASS' ? '#4ecca3' : '#e94560';
          let qText = qResult;
          if (p.attempt_number > 1) qText += ` #${p.attempt_number}`;
          html += `<text x="${sx}" y="${badgeY}" fill="${qColor}" font-size="12" font-weight="600" text-anchor="middle">${qText}</text>`;
        }
        if (isHeld) {
          html += `<text x="${sx}" y="${badgeY}" fill="#e94560" font-size="12" font-weight="600" text-anchor="middle">HOLD</text>`;
        }
        if (isReleased) {
          html += `<text x="${sx}" y="${badgeY}" fill="#17a2b8" font-size="12" font-weight="600" text-anchor="middle">RELEASED</text>`;
        }
      } else {
        // Empty station
        const emptyY = sy + (isLandmark ? 50 : 46);
        html += `<text x="${sx}" y="${emptyY}" fill="#333" font-size="24" text-anchor="middle">\u2014</text>`;
      }

      if (isHeld && p.held_reason) {
        html += `<text x="${sx}" y="${sy+96}" fill="#e94560" font-size="9" text-anchor="middle">${p.held_reason}</text>`;
      }

      html += `</g>`;
    });

    // LINE OUT arrow indicator text
    html += `<text x="1260" y="355" fill="#17a2b8" font-size="10">LINE OUT \u2192</text>`;

    // AP04 genealogy context label on canvas
    const genealogy = snap.genealogy || [];
    if (genealogy.length > 0) {
      const latest = genealogy[genealogy.length - 1];
      const ap04x = FB_STATION_X[4]; // AP04 = index 4
      html += `<text x="${ap04x}" y="280" fill="#ffc107" font-size="9" text-anchor="middle" opacity="0.9">${latest.parent_wip_ids.join(' + ')}</text>`;
      html += `<text x="${ap04x}" y="292" fill="#ffc107" font-size="9" text-anchor="middle" opacity="0.7">\u2192 ${latest.child_wip_id}</text>`;
    }

    stationsG.innerHTML = html;

    // Bind station clicks
    this._bindStationClicks(snap);

    // Render event strip
    this._renderEventStrip(snap);

    // Render genealogy context in right panel
    this._renderGenealogyContext(snap);

    // Apply zoom
    this.applyViewBox();
  },

  _bindStationClicks(snap) {
    const posMap = {};
    for (const p of (snap.positions||[])) posMap[p.position_id] = p;

    document.querySelectorAll('#fb-stations .fb-station').forEach(el => {
      el.addEventListener('click', () => {
        const stId = el.getAttribute('data-station');
        this._selectedStation = (this._selectedStation === stId) ? null : stId;
        this.render(snap);
        this._updateInspector(posMap[stId] || null);
      });
    });
  },

  _updateInspector(pos) {
    const label = document.getElementById('fb-inspector-label');
    const hint = document.getElementById('fb-inspector-hint');
    const placeholder = document.getElementById('fb-inspector-placeholder');
    if (!pos) {
      label.textContent = 'Inspector';
      hint.textContent = 'Select a station';
      placeholder.className = 'fb-inspector-collapsed';
      return;
    }
    placeholder.className = 'fb-inspector-open';
    label.textContent = `${pos.position_id}: ${pos.station_label || pos.position_id}`;
    if (pos.wip_id) {
      hint.innerHTML = `<b>WIP:</b> ${pos.wip_id} &nbsp; <b>Carrier:</b> ${pos.carrier_id||'\u2014'} &nbsp; <b>Status:</b> ${pos.manufacturing_status||'active'}`;
      if (pos.latest_quality_result) {
        hint.innerHTML += ` &nbsp; <b>Quality:</b> <span style="color:${pos.latest_quality_result==='PASS'?'#4ecca3':'#e94560'}">${pos.latest_quality_result}${pos.attempt_number>1?' #'+pos.attempt_number:''}</span>`;
      }
      if (pos.is_quality_hold) hint.innerHTML += ` &nbsp; <b style="color:#e94560">HOLD</b>`;
      if (pos.held_reason) hint.innerHTML += ` &nbsp; <small>(${pos.held_reason})</small>`;
    } else {
      hint.textContent = 'Station empty';
    }
  },

  _renderEventStrip(snap) {
    const list = document.getElementById('fb-event-list');
    if (!list) return;
    const events = snap.recent_quality_events || [];
    let html = '';
    for (const e of events.slice(-12).reverse()) {
      const dColor = e.disposition === 'PASS' ? '#4ecca3' : '#e94560';
      html += `<div class="fb-qe-item">
        <span style="color:${dColor};font-weight:600">${e.disposition||'?'}</span>
        ${e.wip_id||''} @ ${e.station_id||''} #${e.attempt||1}
        <small>t=${(e.simulation_time_s||0).toFixed(0)}s</small>
      </div>`;
    }
    if (!html) html = '<div style="color:#555;font-size:11px">No quality events</div>';
    list.innerHTML = html;
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
