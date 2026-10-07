'use strict';

/* Lightweight observer of the existing whole-factory snapshot.
   No second simulator, no KPI calculation. */

function ovPublicPrefix() {
  const path = (typeof location !== 'undefined' && location.pathname) || '';
  if (path === '/factorix-sim' || path.indexOf('/factorix-sim/') === 0) {
    return '/factorix-sim';
  }
  return '/bottled-water-demo';
}
const OV_API = ovPublicPrefix();
const OV_AREAS = ['BW-WT', 'BW-BP', 'BW-FP', 'BW-UT', 'BW-WH'];

function ovSignal(factory, nodeId, signalId) {
  const node = (factory.nodes || {})[nodeId] || {};
  const signal = (node.signals || {})[signalId] || {};
  return signal.value;
}

function ovFmt(value, suffix) {
  if (value == null || value === '') return '—';
  if (typeof value === 'number') {
    const rounded = Number.isInteger(value) ? String(value) : value.toFixed(3);
    return suffix ? `${rounded} ${suffix}` : rounded;
  }
  return suffix ? `${value} ${suffix}` : String(value);
}

function ovAreaAbnormal(areaId, factory) {
  if (areaId === 'BW-FP') {
    const phase = (factory.scenario || {}).phase || 'NORMAL';
    return { phase, abnormal: phase !== 'NORMAL' };
  }
  if (areaId === 'BW-UT') {
    const phase = (factory.compressor_scenario || {}).phase || 'NORMAL';
    return { phase, abnormal: phase !== 'NORMAL' };
  }
  const operating = ovSignal(factory, areaId, 'operating_state') || 'STOPPED';
  return { phase: operating, abnormal: false };
}

function ovAreaValues(areaId, factory) {
  const water = (factory.balances || {}).water || {};
  const energy = (factory.balances || {}).energy || {};
  const finished = (factory.balances || {}).finished_goods || {};
  if (areaId === 'BW-WT') {
    return {
      tank_level_pct: ovFmt(water.tank_level_pct ?? ovSignal(factory, 'BW-WT-TK01', 'level'), '%'),
      treated_water_flow_m3h: ovFmt(ovSignal(factory, 'BW-WT-RO01', 'production_flow'), 'm3/h'),
      tank_volume_m3: ovFmt(water.tank_volume_m3 ?? ovSignal(factory, 'BW-WT-TK01', 'volume_m3'), 'm3'),
    };
  }
  if (areaId === 'BW-BP') {
    return {
      operating_state: ovFmt(ovSignal(factory, 'BW-BP', 'operating_state')),
      preform_count: ovFmt(ovSignal(factory, 'BW-BP', 'preform_count')),
    };
  }
  if (areaId === 'BW-FP') {
    return {
      total_count: ovFmt(ovSignal(factory, 'BW-FP', 'total_count')),
      good_count: ovFmt(ovSignal(factory, 'BW-FP', 'good_count')),
      reject_count: ovFmt(ovSignal(factory, 'BW-FP', 'reject_count')),
    };
  }
  if (areaId === 'BW-UT') {
    return {
      air_pressure_bar: ovFmt(ovSignal(factory, 'BW-UT-CMP01', 'air_pressure'), 'bar'),
      plant_active_power_kw: ovFmt(
        energy.plant_active_power_kw ?? ovSignal(factory, 'BW-UT-PWR01', 'plant_active_power'),
        'kW'
      ),
    };
  }
  return {
    inventory_count: ovFmt(finished.inventory_count ?? ovSignal(factory, 'BW-WH-FG01', 'inventory_count')),
    receipt_count: ovFmt(finished.receipt_count ?? ovSignal(factory, 'BW-WH-FG01', 'receipt_count')),
    dispatch_count: ovFmt(finished.dispatch_count ?? ovSignal(factory, 'BW-WH-FG01', 'dispatch_count')),
  };
}

function ovRender(factory) {
  const plant = factory.factory || {};
  const name = document.getElementById('ov-plant-name');
  const identity = document.getElementById('ov-identity');
  const runChip = document.getElementById('ov-run-chip');
  const timeChip = document.getElementById('ov-time-chip');
  if (name) name.textContent = factory.plant_name || 'Bottled Water Factory';
  if (identity) identity.textContent = `${factory.plant_id || 'BW-DEMO-01'} · ${OV_AREAS.length} areas`;
  if (runChip) runChip.textContent = plant.run_state || 'STOPPED';
  if (timeChip) timeChip.textContent = `t=${Number(plant.simulation_time_s || 0).toFixed(1)} s`;
  const run = document.getElementById('ov-run-state');
  const operating = document.getElementById('ov-operating-state');
  const sim = document.getElementById('ov-sim-time');
  if (run) run.textContent = plant.run_state || 'STOPPED';
  if (operating) operating.textContent = plant.operating_state || 'STOPPED';
  if (sim) sim.textContent = `${Number(plant.simulation_time_s || 0).toFixed(1)} s`;

  OV_AREAS.forEach((areaId) => {
    const card = document.getElementById(`area-${areaId}`);
    if (!card) return;
    const values = ovAreaValues(areaId, factory);
    Object.keys(values).forEach((key) => {
      const cell = card.querySelector(`[data-raw="${key}"]`);
      if (cell) cell.textContent = values[key];
    });
    const mark = card.querySelector('.ov-abnormal');
    const abnormal = ovAreaAbnormal(areaId, factory);
    if (mark) {
      mark.textContent = abnormal.phase;
      mark.setAttribute('data-abnormal', abnormal.abnormal ? 'true' : 'false');
    }
  });
}

async function ovFetch(path, options) {
  const response = await fetch(`${OV_API}${path}`, options);
  if (!response.ok) throw new Error(`${path} ${response.status}`);
  return response.json();
}

async function ovRefresh() {
  const factory = await ovFetch('/factory');
  ovRender(factory);
}

async function ovAction(path) {
  await fetch(`${OV_API}${path}`, { method: 'POST' });
  await ovRefresh();
}

function ovStart() { return ovAction('/start'); }
function ovPause() { return ovAction('/pause'); }
function ovResume() { return ovAction('/resume'); }
function ovStop() { return ovAction('/stop'); }
function ovReset() { return ovAction('/reset'); }

const ovLineLink = document.getElementById('ov-fp-drilldown');
if (ovLineLink) ovLineLink.setAttribute('href', OV_API);

ovRefresh().catch(() => {});
setInterval(() => { ovRefresh().catch(() => {}); }, 700);
