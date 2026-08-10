/* M6-S04 — TIPA ASSY Demo Controller & Renderer */

const API = '/assy-demo';

const ctrl = {
  _autoTimer: null,
  _speed: 1.0,
  _scenario: 'HAPPY_PATH',

  async init() {
    await this.call('reset', { scenario: this._scenario });
    this.render(await this.call('snapshot'));
  },

  async reset() {
    this.stopAuto();
    this._scenario = document.getElementById('scenario-select').value;
    await this.call('reset', { scenario: this._scenario });
    this.render(await this.call('snapshot'));
  },

  async step() {
    const snap = await this.call('step');
    this.render(snap);
  },

  toggleAuto() {
    if (this._autoTimer) { this.stopAuto(); return; }
    this.startAuto();
  },

  startAuto() {
    document.getElementById('btn-auto').textContent = '⏹ STOP';
    document.getElementById('btn-pause').disabled = false;
    this._autoTimer = setInterval(() => this.step(), Math.round(1000 / this._speed));
  },

  stopAuto() {
    if (this._autoTimer) { clearInterval(this._autoTimer); this._autoTimer = null; }
    document.getElementById('btn-auto').textContent = '▶▶ AUTO';
    document.getElementById('btn-pause').disabled = true;
  },

  pause() {
    if (this._autoTimer) { this.stopAuto(); }
  },

  setSpeed(val) {
    this._speed = parseFloat(val);
    document.getElementById('speed-display').textContent = val + 'x';
    if (this._autoTimer) { this.stopAuto(); this.startAuto(); }
  },

  setScenario(val) {
    this._scenario = val;
    document.getElementById('scenario-display').textContent = val;
    this.reset();  // immediately reset with new scenario
  },

  async call(action, body) {
    const opts = body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : { method: 'POST' };
    const resp = await fetch(`${API}/${action}`, opts);
    return resp.json();
  },

  render(snap) {
    if (!snap || !snap.positions) return;

    // Status bar
    document.getElementById('sim-time').textContent = `t=${snap.simulation_time_s.toFixed(0)}s`;
    const ls = document.getElementById('line-state');
    ls.textContent = snap.line_state.toUpperCase();
    ls.className = 'state ' + snap.line_state;
    document.getElementById('dwell').textContent = `Dwell ${snap.dwell_number}`;

    // Positions
    const container = document.getElementById('positions-container');
    container.innerHTML = '';
    for (const p of snap.positions) {
      const div = document.createElement('div');
      div.className = 'position';
      if (p.is_quality_hold) div.className += ' quality-hold';
      else if (p.is_occupied) div.className += ' occupied';
      if (p.manufacturing_status === 'released') div.className += ' released';
      if (p.position_id === 'AP04') div.className += ' ap04';

      div.innerHTML = `
        <div class="pos-id">${p.position_id}</div>
        <div class="pos-label">${p.station_label}</div>
        ${p.wip_id ? `
          <div class="wip-info">
            <div class="wip-id ${p.wip_type}">${p.wip_id}</div>
            ${p.carrier_id ? `<div class="carrier">${p.carrier_id}</div>` : ''}
            ${p.latest_quality_result ? `<div class="quality-badge ${p.latest_quality_result.toLowerCase()}">${p.latest_quality_result}${p.attempt_number > 1 ? ' #'+p.attempt_number : ''}</div>` : ''}
            ${p.is_quality_hold ? `<div class="quality-badge hold">HOLD</div>` : ''}
            ${p.manufacturing_status === 'released' ? `<div class="quality-badge pass">RELEASED</div>` : ''}
          </div>
        ` : '<div style="color:#555;font-size:0.7em;margin-top:8px;">—</div>'}
      `;
      container.appendChild(div);
    }

    // Production
    const prod = snap.production || {};
    document.getElementById('motors-completed').textContent = prod.motors_created || 0;
    document.getElementById('motors-released').textContent = prod.motors_released || 0;
    document.getElementById('wips-on-line').textContent = prod.wips_on_line || 0;
    document.getElementById('active-holds').textContent = prod.active_quality_holds || 0;
    document.getElementById('rso2-buf').textContent = prod.rso2_buffer || 0;

    // Genealogy
    const glist = document.getElementById('genealogy-list');
    glist.innerHTML = '';
    for (const g of (snap.genealogy || []).slice(-6)) {
      glist.innerHTML += `<div class="genealogy-item">
        <b style="color:#ffc107">${g.child_wip_id}</b> ← ${g.parent_wip_ids.join(' + ')}<br>
        <small>t=${g.join_time_s.toFixed(0)}s @ ${g.join_station}</small>
      </div>`;
    }

    // Quality events
    const qlist = document.getElementById('quality-events');
    qlist.innerHTML = '';
    for (const e of (snap.recent_quality_events || []).slice(-15)) {
      qlist.innerHTML += `<div class="qe-item">
        <span class="qe-disp ${e.disposition}">${e.disposition}</span>
        ${e.wip_id} @ ${e.station_id} #${e.attempt}
        <small>t=${e.simulation_time_s.toFixed(0)}s</small>
      </div>`;
    }

    document.getElementById('scenario-display').textContent = snap.scenario || 'HAPPY_PATH';
  }
};

// Initialize on load
document.addEventListener('DOMContentLoaded', () => ctrl.init());
