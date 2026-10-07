/* ══════════════════════════════════════════════════════════════
   DDAY-B3 — Bottled Water 2D target-line skin

   Binds the Bottled Water Filling & Packaging line to the B2 generic
   single-line runtime. The station order is taken from the runtime
   route returned by the API, so the drawing always follows the real
   line rather than a duplicated layout constant.

   Reuses the existing VF UI *mechanics*: a viewBox SVG canvas with
   pan/zoom, a presentation clock that paces engine ticks, selection
   with a floating popup, state highlighting by data attribute, and
   reduced-motion-aware interpolation of unit movement.
   ══════════════════════════════════════════════════════════════ */

'use strict';

function bwPublicPrefix() {
  const path = (typeof location !== 'undefined' && location.pathname) || '';
  if (path === '/factorix-sim' || path.indexOf('/factorix-sim/') === 0) {
    return '/factorix-sim';
  }
  return '/bottled-water-demo';
}
const BW_API = bwPublicPrefix();

/* Full canvas reference box (viewBox; not a fixed pixel size). */
const BW_CANVAS = { w: 1920, h: 640 };
const BW_FIT = { x: 0, y: 0, w: BW_CANVAS.w, h: BW_CANVAS.h };

const BW_LAYOUT = {
  marginX: 150,
  conveyorTop: 410,
  conveyorH: 44,
  conveyorLeft: 60,
  conveyorRight: 1860,
  stationTop: 200,
  stationW: 172,
  stationH: 140,
  labelY: 500,
  artY: 272,
};

const BW_MAX_EVENTS = 40;
const BW_POLL_MS = 350;
const BW_MOVE_MS = 420;

/* Friendly presentation labels. Raw event names stay authoritative in the API. */
const BW_EVENT_LABEL = {
  UNIT_ENTERED: 'Bottle entered line',
  WIP_MOVED: 'Bottle moved',
  STATION_START: 'Station start',
  STATION_COMPLETE: 'Station complete',
  STATION_PROGRESS: 'Station working',
  STATION_ACTION: 'Station action',
  OPERATION_RETRY: 'Station retry',
  OPERATION_TERMINAL: 'Station terminated',
  OPERATION_WAITING_COMMAND: 'Station waiting',
  QUALITY_START: 'Inspection start',
  QUALITY_OBSERVED: 'Inspection observed',
  QUALITY_RESULT: 'Inspection result',
  QUALITY_HOLD: 'Inspection hold',
  QUALITY_FAILED_FINAL: 'Inspection failed',
  REJECT: 'Bottle rejected',
  UNIT_COMPLETED: 'Bottle completed',
  DWELL_META: 'Cycle',
  LINE_RUN_STATE: 'Line control',
  SCENARIO_PHASE_CHANGED: 'Scenario phase',
  ALARM_RAISED: 'Alarm raised',
  ALARM_CLEARED: 'Alarm cleared',
  DOWNTIME_START: 'Downtime start',
  DOWNTIME_END: 'Downtime end',
};

const BW = {
  state: null,
  prevState: null,
  route: [],
  stationX: {},
  stationNodes: {},
  selected: { kind: '', id: '' },
  bottles: new Map(),
  events: [],
  eventKeys: new Set(),
  timer: null,
  rateMs: 600,
  busy: false,
  view: { ...BW_FIT },
  motion: new Map(),
  rafId: null,
  reducedMotion: false,
  didPan: false,
};

/* ══════════════════════════════════════════════════════════════
   Workspace-specific station artwork

   Each machine is a stylized industrial symbol drawn from bottling
   vocabulary: no shared drawing is borrowed from any other line.
   All coordinates are relative to the machine centre (0,0).
   ══════════════════════════════════════════════════════════════ */

const BW_ART = {
  /* Bottle infeed + air blower: hopper feeding a blower housing. */
  blower() {
    return `
      <path d="M-52,-46 L14,-46 L4,-22 L-42,-22 Z" fill="var(--bw-steel-light)" stroke="var(--bw-steel-dark)" stroke-width="2"/>
      <rect x="-52" y="-50" width="66" height="6" rx="3" fill="var(--bw-steel-dark)"/>
      <circle cx="34" cy="-34" r="17" fill="var(--bw-steel-light)" stroke="var(--bw-steel-dark)" stroke-width="2"/>
      <path d="M34,-45 A11,11 0 0 1 45,-34" fill="none" stroke="var(--bw-steel-dark)" stroke-width="2"/>
      <path d="M34,-23 A11,11 0 0 1 23,-34" fill="none" stroke="var(--bw-steel-dark)" stroke-width="2"/>
      <circle cx="34" cy="-34" r="3.5" fill="var(--bw-steel-dark)"/>
      <rect x="-60" y="-14" width="120" height="30" rx="6" fill="var(--bw-steel)" stroke="var(--bw-steel-dark)" stroke-width="2"/>
      <path d="M-30,-4 L6,-4" stroke="var(--bw-water)" stroke-width="2.5" stroke-linecap="round"/>
      <path d="M-30,4 L6,4" stroke="var(--bw-water)" stroke-width="2.5" stroke-linecap="round"/>
      <path d="M-30,11 L2,11" stroke="var(--bw-water)" stroke-width="2.5" stroke-linecap="round"/>
    `;
  },

  /* Rinser: spray nozzles over a bottle. */
  rinser() {
    const drops = [-26, 0, 26]
      .map((dx) => `<path d="M${dx},-18 l0,10" stroke="var(--bw-water)" stroke-width="2.5" stroke-linecap="round"/>
                    <circle cx="${dx}" cy="-4" r="2.5" fill="var(--bw-water)"/>`).join('');
    return `
      <rect x="-54" y="-46" width="108" height="12" rx="4" fill="var(--bw-steel)" stroke="var(--bw-steel-dark)" stroke-width="2"/>
      <rect x="-40" y="-34" width="12" height="8" rx="2" fill="var(--bw-steel-dark)"/>
      <rect x="-6" y="-34" width="12" height="8" rx="2" fill="var(--bw-steel-dark)"/>
      <rect x="28" y="-34" width="12" height="8" rx="2" fill="var(--bw-steel-dark)"/>
      ${drops}
      <rect x="-19" y="10" width="38" height="34" rx="8" fill="var(--bw-bottle)" stroke="var(--bw-bottle-edge)" stroke-width="2"/>
      <rect x="-8" y="0" width="16" height="12" fill="var(--bw-bottle)" stroke="var(--bw-bottle-edge)" stroke-width="2"/>
      <rect x="-9" y="-16" width="18" height="8" rx="2" fill="var(--bw-bottle-edge)"/>
    `;
  },

  /* Filler: manifold with nozzles filling a bottle to level. */
  filler() {
    return `
      <rect x="-56" y="-52" width="112" height="16" rx="5" fill="var(--bw-steel)" stroke="var(--bw-steel-dark)" stroke-width="2"/>
      <rect x="-4" y="-36" width="8" height="64" rx="3" fill="var(--bw-steel-light)" stroke="var(--bw-steel-dark)" stroke-width="1.5"/>
      <path d="M-44,-36 l0,16" stroke="var(--bw-steel-dark)" stroke-width="5" stroke-linecap="round"/>
      <path d="M0,-36 l0,16" stroke="var(--bw-steel-dark)" stroke-width="5" stroke-linecap="round"/>
      <path d="M44,-36 l0,16" stroke="var(--bw-steel-dark)" stroke-width="5" stroke-linecap="round"/>
      <rect x="-19" y="12" width="38" height="34" rx="8" fill="var(--bw-bottle)" stroke="var(--bw-bottle-edge)" stroke-width="2"/>
      <rect x="-14" y="22" width="28" height="21" rx="5" fill="var(--bw-water)"/>
      <rect x="-8" y="2" width="16" height="12" fill="var(--bw-bottle)" stroke="var(--bw-bottle-edge)" stroke-width="2"/>
      <rect x="-9" y="-14" width="18" height="8" rx="2" fill="var(--bw-cap)"/>
    `;
  },

  /* Capper: rotating head applying a cap. */
  capper() {
    return `
      <rect x="-50" y="-54" width="100" height="14" rx="4" fill="var(--bw-steel)" stroke="var(--bw-steel-dark)" stroke-width="2"/>
      <rect x="-26" y="-40" width="52" height="16" rx="4" fill="var(--bw-steel-light)" stroke="var(--bw-steel-dark)" stroke-width="2"/>
      <path d="M-24,-24 L-30,-6 L30,-6 L24,-24 Z" fill="var(--bw-steel-light)" stroke="var(--bw-steel-dark)" stroke-width="2"/>
      <path d="M-34,-40 A34,10 0 0 1 34,-40" fill="none" stroke="var(--bw-steel-dark)" stroke-width="1.5" stroke-dasharray="4 4"/>
      <rect x="-11" y="-6" width="22" height="10" rx="3" fill="var(--bw-cap)"/>
      <rect x="-8" y="4" width="16" height="12" fill="var(--bw-bottle)" stroke="var(--bw-bottle-edge)" stroke-width="2"/>
      <rect x="-19" y="14" width="38" height="32" rx="8" fill="var(--bw-bottle)" stroke="var(--bw-bottle-edge)" stroke-width="2"/>
      <rect x="-14" y="26" width="28" height="17" rx="5" fill="var(--bw-water)"/>
    `;
  },

  /* Inspection: camera with light cone over a bottle. */
  inspection() {
    return `
      <rect x="-44" y="-56" width="72" height="34" rx="6" fill="var(--bw-steel)" stroke="var(--bw-steel-dark)" stroke-width="2"/>
      <circle cx="4" cy="-39" r="12" fill="#2A3341" stroke="var(--bw-steel-dark)" stroke-width="2"/>
      <circle cx="4" cy="-39" r="5" fill="var(--bw-water-light)"/>
      <path d="M-52,-52 L-44,-44" stroke="var(--bw-steel-dark)" stroke-width="3" stroke-linecap="round"/>
      <path d="M-14,-22 L-30,6 L38,6 L22,-22 Z" fill="var(--bw-water-light)" fill-opacity="0.45" stroke="var(--bw-water)" stroke-width="1.5" stroke-dasharray="5 4"/>
      <rect x="-19" y="10" width="38" height="36" rx="8" fill="var(--bw-bottle)" stroke="var(--bw-bottle-edge)" stroke-width="2"/>
      <rect x="-14" y="24" width="28" height="19" rx="5" fill="var(--bw-water)"/>
      <path d="M-6,28 l5,6 l10,-12" fill="none" stroke="#FFFFFF" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
    `;
  },

  /* Labeler: label roll feeding an applicator. */
  labeler() {
    return `
      <circle cx="-36" cy="-30" r="19" fill="var(--bw-bg-surface)" stroke="var(--bw-steel-dark)" stroke-width="2"/>
      <circle cx="-36" cy="-30" r="7" fill="var(--bw-steel-light)" stroke="var(--bw-steel-dark)" stroke-width="1.5"/>
      <path d="M-17,-24 L22,-6" stroke="var(--bw-accent)" stroke-width="3.5" stroke-linecap="round"/>
      <rect x="20" y="-14" width="26" height="14" rx="3" fill="var(--bw-steel)" stroke="var(--bw-steel-dark)" stroke-width="2"/>
      <rect x="-30" y="-56" width="60" height="10" rx="4" fill="var(--bw-steel-light)" stroke="var(--bw-steel-dark)" stroke-width="1.5"/>
      <rect x="-19" y="12" width="38" height="36" rx="8" fill="var(--bw-bottle)" stroke="var(--bw-bottle-edge)" stroke-width="2"/>
      <rect x="-19" y="26" width="38" height="14" fill="var(--bw-accent)" fill-opacity="0.85"/>
      <rect x="-14" y="18" width="28" height="12" rx="3" fill="var(--bw-water)"/>
    `;
  },

  /* Case packer: bottles dropping into a case. */
  packer() {
    const tops = [-30, 0, 30]
      .map((dx) => `<rect x="${dx - 8}" y="-40" width="16" height="12" rx="4" fill="var(--bw-bottle)" stroke="var(--bw-bottle-edge)" stroke-width="1.5"/>
                     <rect x="${dx - 5}" y="-44" width="10" height="6" rx="2" fill="var(--bw-cap)"/>`).join('');
    return `
      <rect x="-56" y="-56" width="112" height="10" rx="4" fill="var(--bw-steel)" stroke="var(--bw-steel-dark)" stroke-width="1.5"/>
      ${tops}
      <path d="M0,-24 l0,14" stroke="var(--bw-steel-dark)" stroke-width="3" stroke-linecap="round"/>
      <path d="M-7,-16 l7,8 l7,-8" fill="none" stroke="var(--bw-steel-dark)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
      <rect x="-52" y="-2" width="104" height="46" rx="5" fill="var(--bw-case)" stroke="var(--bw-case-dark)" stroke-width="2.5"/>
      <path d="M-52,12 L52,12" stroke="var(--bw-case-dark)" stroke-width="1.5"/>
      <rect x="-22" y="20" width="44" height="16" rx="2" fill="var(--bw-bg-surface)" fill-opacity="0.7"/>
    `;
  },

  /* Palletizer: gantry placing a case onto a pallet stack. */
  palletizer() {
    const slats = [-46, -24, -2, 20, 42]
      .map((dx) => `<rect x="${dx}" y="30" width="12" height="9" rx="2" fill="var(--bw-case-dark)"/>`).join('');
    return `
      <rect x="-58" y="-58" width="116" height="9" rx="4" fill="var(--bw-steel)" stroke="var(--bw-steel-dark)" stroke-width="1.5"/>
      <rect x="30" y="-49" width="13" height="42" rx="3" fill="var(--bw-steel-light)" stroke="var(--bw-steel-dark)" stroke-width="1.5"/>
      <path d="M-26,-7 L-26,-30 L30,-30" fill="none" stroke="var(--bw-steel-dark)" stroke-width="3" stroke-linecap="round"/>
      <path d="M-33,-14 L-26,-7 L-19,-14" fill="none" stroke="var(--bw-steel-dark)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
      <rect x="-40" y="4" width="52" height="22" rx="3" fill="var(--bw-case)" stroke="var(--bw-case-dark)" stroke-width="2"/>
      <rect x="-40" y="30" width="72" height="22" rx="3" fill="var(--bw-case-dark)" fill-opacity="0.35"/>
      ${slats}
      <rect x="-46" y="39" width="96" height="7" rx="2" fill="var(--bw-case-dark)"/>
    `;
  },

  /* Fallback for a station id the skin does not know yet. */
  generic() {
    return `
      <rect x="-52" y="-46" width="104" height="30" rx="6" fill="var(--bw-steel)" stroke="var(--bw-steel-dark)" stroke-width="2"/>
      <circle cx="-22" cy="-31" r="8" fill="var(--bw-steel-light)" stroke="var(--bw-steel-dark)" stroke-width="1.5"/>
      <circle cx="22" cy="-31" r="8" fill="var(--bw-steel-light)" stroke="var(--bw-steel-dark)" stroke-width="1.5"/>
      <rect x="-40" y="-10" width="80" height="34" rx="6" fill="var(--bw-steel-light)" stroke="var(--bw-steel-dark)" stroke-width="2"/>
    `;
  },
};

/* Which artwork belongs to each frozen station of this workspace. */
const BW_STATION_ART = {
  'BW-FP-BLW01': 'blower',
  'BW-FP-RIN01': 'rinser',
  'BW-FP-FIL01': 'filler',
  'BW-FP-CAP01': 'capper',
  'BW-FP-INS01': 'inspection',
  'BW-FP-LAB01': 'labeler',
  'BW-FP-CPK01': 'packer',
  'BW-FP-PAL01': 'palletizer',
};

/* ══════════════════════════════════════════════════════════════
   Small helpers
   ══════════════════════════════════════════════════════════════ */

function bwEl(id) { return document.getElementById(id); }

function bwEscape(value) {
  return String(value == null ? '' : value).replace(/[&<>"']/g, (ch) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[ch]));
}

function bwHumanise(value) {
  const text = String(value || '').replace(/_/g, ' ').trim();
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : '—';
}

function bwShort(id) {
  return String(id || '').replace(/^BW-FP-/, '');
}

/* ══════════════════════════════════════════════════════════════
   Canvas geometry + viewport (pan / zoom)
   ══════════════════════════════════════════════════════════════ */

function bwApplyView() {
  const v = BW.view;
  bwEl('bw-svg').setAttribute('viewBox', `${v.x} ${v.y} ${v.w} ${v.h}`);
}

function bwSvgPoint(evt) {
  const svg = bwEl('bw-svg');
  const pt = svg.createSVGPoint();
  pt.x = evt.clientX;
  pt.y = evt.clientY;
  return pt.matrixTransform(svg.getScreenCTM().inverse());
}

function bwZoom(factor, evt) {
  const anchor = evt ? bwSvgPoint(evt) : {
    x: BW.view.x + BW.view.w / 2, y: BW.view.y + BW.view.h / 2,
  };
  const nextW = Math.max(520, Math.min(3600, BW.view.w * factor));
  const scale = nextW / BW.view.w;
  const nextH = BW.view.h * scale;
  BW.view = {
    x: anchor.x - (anchor.x - BW.view.x) * scale,
    y: anchor.y - (anchor.y - BW.view.y) * scale,
    w: nextW,
    h: nextH,
  };
  bwApplyView();
}

function bwFitView() {
  BW.view = { ...BW_FIT };
  bwApplyView();
}

function bwInstallViewport() {
  const svg = bwEl('bw-svg');
  let dragging = false;
  let captured = false;
  let origin = null;
  let startView = null;
  let moved = false;

  svg.addEventListener('wheel', (evt) => {
    evt.preventDefault();
    bwZoom(evt.deltaY < 0 ? 0.9 : 1.1, evt);
  }, { passive: false });

  svg.addEventListener('pointerdown', (evt) => {
    if (evt.button !== 0) return;
    dragging = true;
    moved = false;
    origin = { x: evt.clientX, y: evt.clientY };
    startView = { ...BW.view };
    // The pointer is deliberately NOT captured here: capturing on press
    // retargets the follow-up mouseup/click to the canvas, which would swallow
    // clicks on a machine or bottle. Capture starts only once a real drag
    // begins.
  });

  svg.addEventListener('pointermove', (evt) => {
    if (!dragging || !origin) return;
    const dxPx = evt.clientX - origin.x;
    const dyPx = evt.clientY - origin.y;

    if (!moved) {
      if (Math.hypot(dxPx, dyPx) < 4) return;   // click, not a drag
      moved = true;
      BW.didPan = true;
      svg.classList.add('bw-panning');
      try {
        svg.setPointerCapture(evt.pointerId);
        captured = true;
      } catch (err) { captured = false; }
    }

    const rect = svg.getBoundingClientRect();
    const dx = dxPx * (BW.view.w / Math.max(rect.width, 1));
    const dy = dyPx * (BW.view.h / Math.max(rect.height, 1));
    BW.view = { ...startView, x: startView.x - dx, y: startView.y - dy };
    bwApplyView();
  });

  const endDrag = (evt) => {
    if (!dragging) return;
    dragging = false;
    origin = null;
    svg.classList.remove('bw-panning');
    if (captured && evt && evt.pointerId != null) {
      try { svg.releasePointerCapture(evt.pointerId); } catch (err) { /* already released */ }
    }
    captured = false;
    moved = false;
  };
  svg.addEventListener('pointerup', endDrag);
  svg.addEventListener('pointercancel', endDrag);
  svg.addEventListener('dblclick', bwFitView);
}

/* ══════════════════════════════════════════════════════════════
   Static line drawing (conveyor, flow, grid)
   ══════════════════════════════════════════════════════════════ */

function bwDrawGrid() {
  const lines = [];
  for (let x = 0; x <= BW_CANVAS.w; x += 80) {
    lines.push(`<path d="M${x},0 L${x},${BW_CANVAS.h}" stroke="var(--bw-grid-minor)" stroke-width="1"/>`);
  }
  for (let y = 0; y <= BW_CANVAS.h; y += 80) {
    lines.push(`<path d="M0,${y} L${BW_CANVAS.w},${y}" stroke="var(--bw-grid-minor)" stroke-width="1"/>`);
  }
  bwEl('bw-grid').innerHTML = lines.join('');
}

function bwDrawConveyor() {
  const L = BW_LAYOUT.conveyorLeft;
  const R = BW_LAYOUT.conveyorRight;
  const top = BW_LAYOUT.conveyorTop;
  const h = BW_LAYOUT.conveyorH;

  let rollers = '';
  for (let x = L + 18; x < R - 8; x += 34) {
    rollers += `<rect x="${x}" y="${top + 8}" width="7" height="${h - 16}" rx="3" fill="var(--bw-conveyor-roller)"/>`;
  }

  let chevrons = '';
  for (let x = L + 90; x < R - 40; x += 220) {
    chevrons += `<path d="M${x},${top + h / 2 - 9} l13,9 l-13,9" fill="none" stroke="#FFFFFF" stroke-opacity="0.55" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>`;
  }

  bwEl('bw-conveyor').innerHTML = `
    <rect x="${L}" y="${top + h}" width="${R - L}" height="10" rx="4" fill="var(--bw-conveyor-frame)"/>
    <rect x="${L}" y="${top}" width="${R - L}" height="${h}" rx="8" fill="var(--bw-conveyor)" stroke="var(--bw-conveyor-frame)" stroke-width="2"/>
    ${rollers}
    ${chevrons}
    <text x="${L - 14}" y="${top + h / 2 + 5}" text-anchor="end" font-size="13" font-weight="700" fill="var(--bw-text-muted)">IN</text>
    <text x="${R + 14}" y="${top + h / 2 + 5}" font-size="13" font-weight="700" fill="var(--bw-text-muted)">OUT</text>
  `;
}

function bwDrawFlow() {
  const parts = [];
  for (let i = 0; i < BW.route.length - 1; i += 1) {
    const x1 = BW.stationX[BW.route[i]];
    const x2 = BW.stationX[BW.route[i + 1]];
    const y = BW_LAYOUT.conveyorTop - 12;
    const mid = (x1 + x2) / 2;
    parts.push(`
      <path d="M${x1 + 34},${y} L${x2 - 34},${y}" stroke="var(--bw-steel-dark)" stroke-width="2" stroke-dasharray="7 6" stroke-opacity="0.7"/>
      <path d="M${mid - 7},${y - 6} l8,6 l-8,6" fill="none" stroke="var(--bw-steel-dark)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    `);
  }
  bwEl('bw-flow').innerHTML = parts.join('');
}

/* The flow/grid layers are decorative: never let them swallow a machine click. */
function bwMakeNonInteractive(layerId) {
  bwEl(layerId).setAttribute('pointer-events', 'none');
}

/* ══════════════════════════════════════════════════════════════
   Data binding helpers
   ══════════════════════════════════════════════════════════════ */

async function bwGet(path) {
  const res = await fetch(`${BW_API}${path}`, { headers: { Accept: 'application/json' } });
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return res.json();
}

async function bwPost(path) {
  const res = await fetch(`${BW_API}${path}`, {
    method: 'POST', headers: { Accept: 'application/json' },
  });
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return res.json();
}

function bwStationFor(state, stationId) {
  return (state.stations || []).find((s) => s.station_id === stationId) || null;
}

function bwStationVisualState(station, state) {
  const result = (station.last_disposition || '').toUpperCase();
  if (result === 'FAIL' || result === 'NG') return 'fail';
  if (station.station_id === 'BW-FP-CAP01') {
    const mark = ((state && state.scenario) || {}).highlight;
    if (mark === 'fault') return 'fault';
    if (mark === 'warn') return 'warn';
    if (mark === 'recover') return 'recover';
  }
  if (result === 'PASS' && station.is_occupied) return 'pass';
  if (state.run_state === 'PAUSED') return 'paused';
  if (state.run_state !== 'RUNNING') return 'stopped';
  return station.is_occupied ? 'run' : 'idle';
}

const BW_STATE_FILL = {
  run: 'var(--bw-accent-light)',
  pass: '#EAF7F0',
  fail: '#FDECEC',
  idle: '#FFF9EC',
  paused: '#FFF9EC',
  stopped: 'var(--bw-bg-surface)',
  warn: '#FFF4D6',
  fault: '#FDECEC',
  recover: '#EAF2FF',
};

const BW_STATE_DOT = {
  run: 'var(--bw-state-run)',
  pass: 'var(--bw-state-pass)',
  fail: 'var(--bw-state-fail)',
  idle: 'var(--bw-state-idle)',
  paused: 'var(--bw-state-idle)',
  stopped: 'var(--bw-state-stopped)',
  warn: '#D48B0A',
  fault: 'var(--bw-state-fail)',
  recover: 'var(--bw-accent)',
};

/* ══════════════════════════════════════════════════════════════
   Station rendering

   Station nodes are built once per route and then only have their
   attributes updated. Rebuilding the layer on every poll would break
   pointer dispatch (the node under the cursor can be replaced between
   pointerdown and click), so a running line would swallow machine
   clicks.
   ══════════════════════════════════════════════════════════════ */

function bwBuildStations() {
  const bodyTop = BW_LAYOUT.stationTop;
  const parts = [];
  BW.stationNodes = {};

  BW.route.forEach((stationId, index) => {
    const cx = BW.stationX[stationId];
    const artKind = BW_STATION_ART[stationId] || 'generic';
    const left = cx - BW_LAYOUT.stationW / 2;
    const uid = `bw-st-${index}`;

    parts.push(`
      <g class="bw-station" data-station-id="${bwEscape(stationId)}"
         tabindex="0" role="button" aria-label="${bwEscape(bwStationName(stationId))}">
        <rect class="bw-station-body" x="${left}" y="${bodyTop}"
              width="${BW_LAYOUT.stationW}" height="${BW_LAYOUT.stationH}" rx="14"
              fill="var(--bw-bg-surface)" stroke="var(--bw-border)" stroke-width="1.5"/>
        <rect x="${left}" y="${bodyTop}" width="${BW_LAYOUT.stationW}" height="26" rx="14"
              fill="var(--bw-steel-light)" fill-opacity="0.65" pointer-events="none"/>
        <circle class="bw-station-dot" cx="${left + 16}" cy="${bodyTop + 13}" r="5"
                fill="var(--bw-state-stopped)" pointer-events="none"/>
        <text x="${left + BW_LAYOUT.stationW / 2}" y="${bodyTop + 18}" text-anchor="middle"
              font-size="12" font-weight="700" fill="var(--bw-text-secondary)"
              pointer-events="none">${bwEscape(bwShort(stationId))}</text>
        <g transform="translate(${cx}, ${BW_LAYOUT.artY})" pointer-events="none">${BW_ART[artKind]()}</g>
        <g class="bw-badge-g" data-uid="${uid}" pointer-events="none" style="display:none">
          <rect class="bw-badge-rect" x="${cx - 37}" y="${bodyTop + BW_LAYOUT.stationH + 10}"
                width="74" height="20" rx="10"
                fill="var(--bw-bg-surface)" stroke="var(--bw-text-muted)" stroke-width="1.2"/>
          <text class="bw-badge-text" x="${cx}" y="${bodyTop + BW_LAYOUT.stationH + 24}"
                text-anchor="middle" font-size="11" font-weight="700"
                fill="var(--bw-text-muted)">NO RESULT</text>
        </g>
        <text x="${cx}" y="${BW_LAYOUT.labelY}" text-anchor="middle" font-size="14"
              font-weight="600" fill="var(--bw-text)" pointer-events="none">${bwEscape(bwStationName(stationId))}</text>
        <text x="${cx}" y="${BW_LAYOUT.labelY + 19}" text-anchor="middle" font-size="11"
              fill="var(--bw-text-muted)" pointer-events="none">step ${index + 1} of ${BW.route.length}</text>
        <!-- Explicit hit area: exactly the machine body, never the label band. -->
        <rect class="bw-hit" x="${left}" y="${bodyTop}" width="${BW_LAYOUT.stationW}"
              height="${BW_LAYOUT.stationH}" rx="14" fill="transparent"
              stroke="transparent" style="pointer-events:all"/>
      </g>
    `);
  });

  const host = bwEl('bw-stations');
  host.innerHTML = parts.join('');
  host.querySelectorAll('.bw-station').forEach((node) => {
    const stationId = node.getAttribute('data-station-id');
    BW.stationNodes[stationId] = {
      group: node,
      body: node.querySelector('.bw-station-body'),
      dot: node.querySelector('.bw-station-dot'),
      badgeGroup: node.querySelector('.bw-badge-g'),
      badgeRect: node.querySelector('.bw-badge-rect'),
      badgeText: node.querySelector('.bw-badge-text'),
    };
    node.addEventListener('click', (evt) => {
      evt.stopPropagation();
      bwSelectStation(stationId);
    });
    node.addEventListener('keydown', (evt) => {
      if (evt.key !== 'Enter' && evt.key !== ' ') return;
      evt.preventDefault();
      evt.stopPropagation();
      bwSelectStation(stationId);
    });
  });
}

function bwUpdateStations() {
  const state = BW.state;
  BW.route.forEach((stationId) => {
    const nodes = BW.stationNodes[stationId];
    if (!nodes) return;
    const station = bwStationFor(state, stationId) || { is_occupied: false };
    const visual = bwStationVisualState(station, state);
    const selected = BW.selected.kind === 'station' && BW.selected.id === stationId;

    nodes.body.setAttribute('fill', BW_STATE_FILL[visual]);
    nodes.dot.setAttribute('fill', BW_STATE_DOT[visual]);
    nodes.group.classList.toggle('bw-selected', selected);

    if (station.is_quality_checkpoint) {
      const result = (station.last_disposition || '').toUpperCase();
      let text = 'NO RESULT';
      let fill = 'var(--bw-text-muted)';
      let bg = 'var(--bw-bg-surface)';
      if (result === 'PASS') { text = 'PASS'; fill = 'var(--bw-state-pass)'; bg = '#EAF7F0'; }
      else if (result === 'FAIL' || result === 'NG') {
        text = result; fill = 'var(--bw-state-fail)'; bg = '#FDECEC';
      }
      nodes.badgeGroup.style.display = '';
      nodes.badgeText.textContent = text;
      nodes.badgeText.setAttribute('fill', fill);
      nodes.badgeRect.setAttribute('fill', bg);
      nodes.badgeRect.setAttribute('stroke', fill);
    } else {
      nodes.badgeGroup.style.display = 'none';
    }
  });
}

/* Workspace display names for the frozen route. */
const BW_STATION_NAME = {
  'BW-FP-BLW01': 'Blower / Infeed',
  'BW-FP-RIN01': 'Rinser',
  'BW-FP-FIL01': 'Filler',
  'BW-FP-CAP01': 'Capper',
  'BW-FP-INS01': 'Inspection',
  'BW-FP-LAB01': 'Labeler',
  'BW-FP-CPK01': 'Case Packer',
  'BW-FP-PAL01': 'Palletizer',
};

function bwStationName(stationId) {
  return BW_STATION_NAME[stationId] || stationId;
}

/* ══════════════════════════════════════════════════════════════
   Bottle tokens + movement
   ══════════════════════════════════════════════════════════════ */

function bwBottleSvg(unitId, rejected) {
  const bodyFill = rejected ? '#FDECEC' : 'var(--bw-bottle)';
  const bodyEdge = rejected ? 'var(--bw-state-fail)' : 'var(--bw-bottle-edge)';
  const liquid = rejected ? '#F4C7C7' : 'var(--bw-water)';
  return `
    <g class="bw-bottle" data-unit-id="${bwEscape(unitId)}">
      <rect class="bw-bottle-body" x="-13" y="-42" width="26" height="42" rx="7"
            fill="${bodyFill}" stroke="${bodyEdge}" stroke-width="1.5"/>
      <rect x="-9" y="-30" width="18" height="26" rx="5" fill="${liquid}"/>
      <rect x="-6" y="-52" width="12" height="11" fill="${bodyFill}" stroke="${bodyEdge}" stroke-width="1.2"/>
      <rect x="-8" y="-59" width="16" height="8" rx="2" fill="var(--bw-cap)"/>
      <!-- Whole-token hit area so the bottle is clickable over its silhouette. -->
      <rect class="bw-bottle-hit" x="-14" y="-60" width="28" height="61" rx="8"
            fill="transparent" stroke="transparent" style="pointer-events:all"/>
    </g>
  `;
}

/* Interpolate a bottle between two station x positions (VF motion convention). */
function bwAnimateBottle(entry, toX) {
  const fromX = entry.x;
  if (BW.reducedMotion) {
    entry.x = toX;
    entry.node.setAttribute('transform', `translate(${toX}, ${BW.bottleY})`);
    return;
  }
  BW.motion.set(entry.unitId, {
    node: entry.node, fromX, toX, start: performance.now(), duration: BW_MOVE_MS,
  });
}

function bwBottleFrame(now) {
  BW.motion.forEach((plan, unitId) => {
    const t = Math.min((now - plan.start) / plan.duration, 1);
    const ease = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
    const x = plan.fromX + (plan.toX - plan.fromX) * ease;
    plan.node.setAttribute('transform', `translate(${x}, ${BW.bottleY})`);
    if (t >= 1) BW.motion.delete(unitId);
  });
  if (BW.motion.size) {
    BW.rafId = requestAnimationFrame(bwBottleFrame);
  } else {
    BW.rafId = null;
  }
}

function bwDrawBottles() {
  const state = BW.state;
  const host = bwEl('bw-bottles');
  const seen = new Set();

  (state.stations || []).forEach((station) => {
    if (!station.unit_id) return;
    seen.add(station.unit_id);
    const toX = BW.stationX[station.station_id];
    if (toX == null) return;

    let entry = BW.bottles.get(station.unit_id);
    if (!entry) {
      host.insertAdjacentHTML('beforeend', bwBottleSvg(station.unit_id, false));
      const node = host.querySelector(`[data-unit-id="${CSS.escape(station.unit_id)}"]`);
      node.addEventListener('click', (evt) => {
        evt.stopPropagation();
        bwSelectUnit(station.unit_id);
      });
      entry = { node, x: toX, unitId: station.unit_id };
      BW.bottles.set(station.unit_id, entry);
      entry.node.setAttribute('transform', `translate(${toX}, ${BW.bottleY})`);
      return;
    }

    if (station.unit_status === 'rejected') {
      entry.node.querySelectorAll('rect').forEach((r) => {
        r.setAttribute('fill', '#FDECEC');
        r.setAttribute('stroke', 'var(--bw-state-fail)');
      });
    }

    if (entry.x !== toX) bwAnimateBottle(entry, toX);
    if (BW.selected.kind === 'unit' && BW.selected.id === station.unit_id) {
      entry.node.classList.add('bw-selected');
    }
  });

  BW.bottles.forEach((entry, unitId) => {
    if (seen.has(unitId)) return;
    entry.node.remove();
    BW.bottles.delete(unitId);
    BW.motion.delete(unitId);
  });

  if (BW.motion.size && BW.rafId == null) BW.rafId = requestAnimationFrame(bwBottleFrame);
}

/* ══════════════════════════════════════════════════════════════
   Facts, clock and event strip
   ══════════════════════════════════════════════════════════════ */

function bwApplyFacts() {
  const s = BW.state;
  bwEl('bw-plant-name').textContent = s.plant_id || 'Bottled Water Factory';
  bwEl('bw-line-label').textContent = s.line_label || s.line_id || '';
  bwEl('bw-identity').textContent = `${s.plant_id} · ${s.line_id}`;
  bwEl('bw-product-chip').textContent = `${s.unit_type} · ${s.product_code}`;

  const runState = bwEl('bw-run-state');
  runState.textContent = s.run_state;
  runState.setAttribute('data-state', s.run_state);
  bwEl('bw-operating-state').textContent = s.operating_state;
  const capperMark = bwEl('bw-capper-mark');
  if (capperMark) {
    const highlight = ((s.scenario || {}).highlight) || 'normal';
    capperMark.textContent = highlight;
    capperMark.setAttribute('data-mark', highlight);
  }
  const cmp = s.compressor_scenario || {};
  const cmpMark = bwEl('bw-cmp-mark');
  if (cmpMark) {
    const highlight = cmp.highlight || 'normal';
    cmpMark.textContent = highlight;
    cmpMark.setAttribute('data-mark', highlight);
  }
  const air = bwEl('bw-air-pressure');
  if (air) {
    const bar = cmp.air_pressure_bar;
    air.textContent = (bar == null || Number.isNaN(Number(bar)))
      ? '—'
      : `${Number(bar).toFixed(3)} bar`;
    air.setAttribute('data-mark', cmp.highlight || 'normal');
  }
  bwEl('bw-sim-time').textContent = `${Number(s.simulation_time_s).toFixed(1)} s`;
  bwEl('bw-dwell').textContent = s.dwell_number;
  bwEl('bw-total').textContent = s.counts.total;
  bwEl('bw-good').textContent = s.counts.good;
  bwEl('bw-reject').textContent = s.counts.reject;
  bwEl('bw-on-line').textContent = s.units_on_line;

  const checkpoint = (s.quality_checkpoints || [])[0];
  const station = checkpoint ? bwStationFor(s, checkpoint) : null;
  const result = station && station.last_disposition ? station.last_disposition.toUpperCase() : '';
  const inspection = bwEl('bw-inspection');
  inspection.textContent = result
    ? `${result}${result === 'PASS' ? ' — continues' : ' — rejected'}`
    : 'no result yet';
  inspection.setAttribute('data-result', result);

  const simState = bwEl('bw-sim-state');
  simState.textContent = s.run_state;
  simState.setAttribute('data-state', s.run_state);
  bwEl('bw-sim-clock').textContent = `t=${Number(s.simulation_time_s).toFixed(0)}s`;
  bwEl('bw-sim-dwell').textContent = `DWELL ${s.dwell_number}`;

  const notes = {
    RUNNING: `Line running — ${s.units_on_line} bottle(s) on the line`,
    PAUSED: 'Line paused — progression frozen, state preserved',
    STOPPED: 'Line stopped — controlled stop, not a fault',
  };
  bwEl('bw-sim-note').textContent = notes[s.run_state] || s.run_state;

  const running = s.run_state === 'RUNNING';
  const paused = s.run_state === 'PAUSED';
  bwEl('bw-btn-start').disabled = running;
  bwEl('bw-btn-pause').disabled = !running;
  bwEl('bw-btn-resume').disabled = !paused;
  bwEl('bw-btn-stop').disabled = s.run_state === 'STOPPED';
  bwEl('bw-live-chip').textContent = running ? '● LIVE' : '○ IDLE';
}

function bwApplyEvents() {
  const list = bwEl('bw-event-list');
  const items = BW.events.slice(-BW_MAX_EVENTS).reverse();
  list.innerHTML = items.map((ev) => {
    const label = BW_EVENT_LABEL[ev.event_type] || bwHumanise(ev.event_type);
    const cls = ev.category === 'pass' ? ' bw-ev-pass'
      : ev.category === 'fail' ? ' bw-ev-fail'
        : ev.category === 'control' ? ' bw-ev-control' : '';
    const meta = [];
    if (ev.station_id) meta.push(bwStationName(ev.station_id));
    if (ev.unit_id) meta.push(ev.unit_id);
    return `<li class="${cls.trim()}">
      <span class="bw-ev-time">t=${Number(ev.simulation_time_s).toFixed(0)}s</span>
      <span class="bw-ev-type">${bwEscape(label)}</span>
      ${meta.length ? `<span class="bw-ev-meta">${bwEscape(meta.join(' · '))}</span>` : ''}
    </li>`;
  }).join('');
  bwEl('bw-events-count').textContent = BW.events.length;
}

function bwCategoriseEvents(state) {
  const incoming = [...(state.recent_events || []), ...(state.scenario_events || [])].map((ev) => {
    const type = ev.event_type;
    let category = '';
    if (type === 'REJECT' || type === 'QUALITY_FAILED_FINAL') category = 'fail';
    else if (type === 'QUALITY_RESULT') {
      const disposition = (ev.detail || '').toUpperCase();
      category = disposition.includes('FAIL') || disposition.includes('NG') ? 'fail' : 'pass';
    } else if (type === 'UNIT_COMPLETED') category = 'pass';
    else if (type === 'LINE_RUN_STATE') category = 'control';
    else if (type === 'ALARM_RAISED' || type === 'DOWNTIME_START') category = 'fail';
    else if (type === 'ALARM_CLEARED' || type === 'DOWNTIME_END') category = 'pass';
    else if (type === 'SCENARIO_PHASE_CHANGED') category = 'control';
    return {
      key: `${type}|${ev.station_id}|${ev.unit_id}|${ev.simulation_time_s}|${ev.dwell_number}`,
      event_type: type,
      station_id: ev.station_id,
      unit_id: ev.unit_id,
      detail: ev.detail,
      simulation_time_s: ev.simulation_time_s,
      dwell_number: ev.dwell_number,
      category,
    };
  });

  if (!BW.state) {
    BW.events = incoming;
    incoming.forEach((ev) => BW.eventKeys.add(ev.key));
    return;
  }
  incoming.forEach((ev) => {
    if (BW.eventKeys.has(ev.key)) return;
    BW.eventKeys.add(ev.key);
    BW.events.push(ev);
  });
  if (BW.events.length > 400) {
    BW.events = BW.events.slice(-200);
    BW.eventKeys = new Set(BW.events.map((e) => e.key));
  }
}

/* ══════════════════════════════════════════════════════════════
   Selection + popup
   ══════════════════════════════════════════════════════════════ */

function bwClosePopup() {
  bwEl('bw-popup').classList.add('bw-hidden');
  BW.selected = { kind: '', id: '' };
  if (BW.state) { bwUpdateStations(); bwDrawBottles(); }
}

function bwOpenPopup(title, bodyHtml) {
  bwEl('bw-popup-title').textContent = title;
  bwEl('bw-popup-body').innerHTML = bodyHtml;
  bwEl('bw-popup').classList.remove('bw-hidden');
}

function bwRow(label, value) {
  return `<div class="bw-row"><span class="bw-row-label">${bwEscape(label)}</span>
          <span class="bw-row-value">${bwEscape(value)}</span></div>`;
}

function bwBadge(result) {
  const value = (result || '').toUpperCase();
  if (value === 'PASS') return '<span class="bw-badge bw-badge-pass">PASS</span>';
  if (value === 'FAIL' || value === 'NG') return `<span class="bw-badge bw-badge-fail">${bwEscape(value)}</span>`;
  return '<span class="bw-badge bw-badge-neutral">NO RESULT</span>';
}

function bwAssetSignalRows(state, stationId) {
  const bundle = ((state || {}).asset_signals || {})[stationId] || {};
  const ids = Object.keys(bundle);
  if (!ids.length) return '';
  let html = '<div class="bw-subhead">Machine signals</div>';
  ids.forEach((signalId) => {
    const fact = bundle[signalId] || {};
    const unit = fact.unit && fact.unit !== '-' ? ` ${fact.unit}` : '';
    html += bwRow(signalId.replace(/_/g, ' '), `${fact.value}${unit}`);
  });
  return html;
}

function bwClassificationFields(state, stationId) {
  const scenario = (state || {}).scenario || {};
  if (stationId !== scenario.target_asset) return '';
  const codes = (state || {}).classification || {};
  const downtime = codes.downtime_code || '';
  const failure = codes.failure_code || '';
  return `
    <div class="bw-subhead">Classify existing event</div>
    <div class="bw-empty">Codes enrich an already-raised downtime or alarm. They do not create one.</div>
    <label class="bw-rate-label">Downtime code
      <select id="bw-downtime-code" class="bw-select">
        <option value="">(none)</option>
        <option value="DT-MECH"${downtime === 'DT-MECH' ? ' selected' : ''}>DT-MECH</option>
        <option value="DT-BRG"${downtime === 'DT-BRG' ? ' selected' : ''}>DT-BRG</option>
      </select>
    </label>
    <label class="bw-rate-label">Failure code
      <select id="bw-failure-code" class="bw-select">
        <option value="">(none)</option>
        <option value="FAIL-BRG"${failure === 'FAIL-BRG' ? ' selected' : ''}>FAIL-BRG</option>
        <option value="FAIL-DRV"${failure === 'FAIL-DRV' ? ' selected' : ''}>FAIL-DRV</option>
      </select>
    </label>
    <div class="bw-actions">
      <button class="bw-btn bw-btn-outline" type="button" id="bw-btn-classify">Apply codes</button>
    </div>`;
}

function bwBindClassify() {
  const button = bwEl('bw-btn-classify');
  if (!button || button.dataset.bound === '1') return;
  button.dataset.bound = '1';
  button.addEventListener('click', (evt) => {
    evt.preventDefault();
    bwDeclareCodes();
  });
}

async function bwDeclareCodes() {
  const downtime = (bwEl('bw-downtime-code') || {}).value || '';
  const failure = (bwEl('bw-failure-code') || {}).value || '';
  try {
    if (downtime) {
      await fetch(`${BW_API}/classify`, {
        method: 'POST',
        headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
        body: JSON.stringify({ kind: 'downtime_code', code: downtime }),
      });
    }
    if (failure) {
      await fetch(`${BW_API}/classify`, {
        method: 'POST',
        headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
        body: JSON.stringify({ kind: 'failure_code', code: failure }),
      });
    }
    const state = await bwGet('/state');
    bwApplyState(state);
  } catch (err) {
    bwEl('bw-sim-note').textContent = `Classify failed: ${err.message}`;
  }
}

function bwSelectStation(stationId) {
  BW.selected = { kind: 'station', id: stationId };
  const state = BW.state;
  const station = bwStationFor(state, stationId);
  const index = BW.route.indexOf(stationId);
  const visual = bwStationVisualState(station || { is_occupied: false }, state);

  let html = '';
  html += bwRow('Station', stationId);
  html += bwRow('Step', `${index + 1} of ${BW.route.length}`);
  html += bwRow('Display state', bwHumanise(visual === 'run' ? 'running'
    : visual === 'pass' ? 'running — inspection passed'
      : visual === 'fail' ? 'inspection failed — reject'
        : visual));
  html += bwRow('Occupied', station && station.is_occupied ? 'yes' : 'no');
  if (station && station.unit_id) {
    html += bwRow('Bottle', station.unit_id);
    html += bwRow('Product', `${station.unit_type} · ${station.product_code}`);
    html += bwRow('Unit status', bwHumanise(station.unit_status));
  }
  if (station && station.is_quality_checkpoint) {
    html += '<div class="bw-subhead">Inspection</div>';
    html += `<div class="bw-actions">${bwBadge(station.last_disposition)}</div>`;
    html += '<div class="bw-empty">Result is produced automatically by the line; '
      + 'no manual disposition exists.</div>';
  }
  html += bwAssetSignalRows(state, stationId);
  html += bwClassificationFields(state, stationId);

  bwOpenPopup(bwStationName(stationId), html);
  bwBindClassify();
  bwUpdateStations();
  bwDrawBottles();
}

async function bwSelectUnit(unitId) {
  BW.selected = { kind: 'unit', id: unitId };
  // Open immediately so the panel cannot be raced closed by a slow request.
  bwOpenPopup(`Bottle ${unitId}`, '<div class="bw-empty">Reading unit context…</div>');
  bwDrawBottles();

  let detail = null;
  try {
    detail = await bwGet(`/unit/${encodeURIComponent(unitId)}`);
  } catch (err) {
    bwEl('bw-popup-body').innerHTML =
      '<div class="bw-empty">Unit is no longer on the line.</div>';
    return;
  }

  let html = '';
  html += bwRow('Bottle', detail.unit_id);
  html += bwRow('Product', `${detail.unit_type} · ${detail.product_code}`);
  html += bwRow('Unit status', bwHumanise(detail.unit_status));
  html += bwRow('At station', detail.current_station_id
    ? `${bwStationName(detail.current_station_id)} (${bwShort(detail.current_station_id)})` : '—');
  html += bwRow('Stations completed', detail.stations_completed);
  html += bwRow('Rejected', detail.rejected ? 'yes' : 'no');
  html += bwRow('Counted good', detail.counted_good ? 'yes' : 'no');
  html += bwRow('Quality status', bwHumanise(detail.quality_status));

  html += '<div class="bw-subhead">Quality records</div>';
  if (detail.quality_records.length) {
    detail.quality_records.forEach((record) => {
      html += `<div class="bw-row"><span class="bw-row-label">${bwEscape(bwStationName(record.station_id))} · attempt ${record.attempt_number}</span>
               <span class="bw-row-value">${bwBadge(record.disposition)}</span></div>`;
    });
  } else {
    html += '<div class="bw-empty">No inspection reached yet.</div>';
  }

  html += '<div class="bw-subhead">Movement</div>';
  html += '<div class="bw-empty">Position, status and counts are read from the '
    + 'running line. This panel is read-only.</div>';

  bwOpenPopup(`Bottle ${unitId}`, html);
  bwDrawBottles();
}

/* ══════════════════════════════════════════════════════════════
   Operator controls (START / PAUSE / RESUME / STOP / RESET)
   ══════════════════════════════════════════════════════════════ */

async function bwAction(path) {
  try {
    const state = await bwPost(path);
    bwApplyState(state);
  } catch (err) {
    bwEl('bw-sim-note').textContent = `Control failed: ${err.message}`;
  }
}

function bwStart() { return bwAction('/start'); }
function bwPause() { return bwAction('/pause'); }
function bwResume() { return bwAction('/resume'); }
function bwStop() { return bwAction('/stop'); }

function bwReset() {
  if (!window.confirm('RESET returns the factory to t=0 and cannot be undone. Continue?')) {
    return;
  }
  BW.events = [];
  BW.eventKeys.clear();
  BW.motion.clear();
  BW.bottles.forEach((entry) => entry.node.remove());
  BW.bottles.clear();
  bwClosePopup();
  return bwAction('/reset');
}

function bwPresentAdvancedControls() {
  const panel = bwEl('bw-sim-advanced-body');
  const resume = bwEl('bw-btn-resume');
  const reset = bwEl('bw-btn-reset');
  if (!panel) return;
  if (resume) panel.appendChild(resume);
  if (reset) panel.appendChild(reset);
}

function bwSetRate(value) {
  // Display refresh only: the server owns the production clock.
  BW.rateMs = Math.max(80, Number(value) || 600);
  bwRestartClock();
}

/* ══════════════════════════════════════════════════════════════
   Observer poll — the server owns the production clock

   DDAY-B4: the simulation advances autonomously on the server. This skin only
   reads state and renders it; it never requests a production step. START /
   PAUSE / RESUME / STOP / RESET remain operator controls. The poll interval is
   presentation only and has no influence on simulation truth.
   ══════════════════════════════════════════════════════════════ */

async function bwTick() {
  if (BW.busy) return;
  BW.busy = true;
  try {
    const state = await bwGet('/state');
    bwApplyState(state);
  } catch (err) {
    bwEl('bw-sim-note').textContent = `Line link unavailable: ${err.message}`;
  } finally {
    BW.busy = false;
  }
}

function bwRestartClock() {
  if (BW.timer) clearInterval(BW.timer);
  BW.timer = setInterval(bwTick, BW.rateMs);
}

/* ══════════════════════════════════════════════════════════════
   State application
   ══════════════════════════════════════════════════════════════ */

function bwApplyState(state) {
  BW.prevState = BW.state;
  BW.state = state;

  if (state.route.join('|') !== BW.route.join('|')) {
    BW.route = state.route.slice();
    bwComputeLayout();
    bwDrawConveyor();
    bwDrawFlow();
    bwBuildStations();
  }

  bwCategoriseEvents(state);
  bwApplyFacts();
  bwUpdateStations();
  bwDrawBottles();
  bwApplyEvents();

  if (BW.selected.kind === 'station' && BW.selected.id) {
    const station = bwStationFor(state, BW.selected.id);
    if (station) bwRefreshStationPopup(station);
  }
}

function bwRefreshStationPopup(station) {
  const index = BW.route.indexOf(station.station_id);
  let html = '';
  html += bwRow('Station', station.station_id);
  html += bwRow('Step', `${index + 1} of ${BW.route.length}`);
  html += bwRow('Occupied', station.is_occupied ? 'yes' : 'no');
  if (station.unit_id) {
    html += bwRow('Bottle', station.unit_id);
    html += bwRow('Unit status', bwHumanise(station.unit_status));
  }
  if (station.is_quality_checkpoint) {
    html += '<div class="bw-subhead">Inspection</div>';
    html += `<div class="bw-actions">${bwBadge(station.last_disposition)}</div>`;
  }
  html += bwAssetSignalRows(BW.state, station.station_id);
  html += bwClassificationFields(BW.state, station.station_id);
  bwEl('bw-popup-body').innerHTML = html;
  bwBindClassify();
}

/* Station x positions are derived from the runtime route length. */
function bwComputeLayout() {
  const count = Math.max(BW.route.length, 1);
  const span = BW_CANVAS.w - BW_LAYOUT.marginX * 2;
  const step = count > 1 ? span / (count - 1) : 0;
  BW.stationX = {};
  BW.route.forEach((stationId, index) => {
    BW.stationX[stationId] = BW_LAYOUT.marginX + step * index;
  });
  BW.bottleY = BW_LAYOUT.conveyorTop - 4;
}

/* ══════════════════════════════════════════════════════════════
   Bootstrap
   ══════════════════════════════════════════════════════════════ */

async function bwInit() {
  BW.reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  window.matchMedia('(prefers-reduced-motion: reduce)')
    .addEventListener('change', (evt) => { BW.reducedMotion = evt.matches; });

  bwDrawGrid();
  bwMakeNonInteractive('bw-grid');
  bwMakeNonInteractive('bw-flow');
  bwInstallViewport();
  bwApplyView();
  // Clicking empty canvas closes the panel; clicking a machine or bottle must
  // never be treated as a background click, and the click that ends a pan must
  // be ignored.
  bwEl('bw-svg').addEventListener('click', (evt) => {
    if (BW.didPan) { BW.didPan = false; return; }
    const target = evt.target;
    if (target && target.closest && target.closest('.bw-station, .bw-bottle')) return;
    bwClosePopup();
  });

  try {
    const state = await bwGet('/state');
    bwApplyState(state);
  } catch (err) {
    bwEl('bw-sim-note').textContent = `Line link unavailable: ${err.message}`;
    return;
  }
  bwRestartClock();
}

document.addEventListener('DOMContentLoaded', () => {
  const factoryLink = document.getElementById('bw-factory-link');
  if (factoryLink) factoryLink.setAttribute('href', `${BW_API}/overview`);
  bwPresentAdvancedControls();
  bwInit();
});
