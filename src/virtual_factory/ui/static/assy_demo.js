/* M6-S04B-I09-P02-C03R — Reference-Locked Visual Implementation */
/* Design Authority: VF_DESIGN_AUTHORITY_REFERENCE_LOCKED_I09_P02_C03R.md */
/* Baseline: 27f3ed6 (EXH-UI-01-C01) */
/* EXH-UI-01-C02: Physical composition readability — tighter viewBox, larger fonts */

const API = '/assy-demo';
const LANDMARKS = new Set(['AP04','AP06','AP08','AP11']);
const LANDMARK_LABELS = { AP04:'JOIN', AP06:'TEST', AP08:'VISION', AP11:'FINAL' };
const STATIONS = ['PRE-ASSY','AP01','AP02','AP03','AP04','AP05','AP06','AP07','AP08','AP09','AP10','AP11'];
const FB_STATIONS = STATIONS;
const FB_LANDMARKS = LANDMARK_LABELS;
// EXH-UI-01-C02: canvasH 820 (cropped from 1080), pallet 100×80, off-line zone
const VF_LAYOUT = {
  canvasW: 1920, canvasH: 820,
  // X positions RIGHT→LEFT (normal gap ~120px, landmarks ~130px)
  lineInX: 1890,
  stationX: [1720, 1600, 1485, 1370, 1240, 1115, 985, 865, 735, 615, 495, 365],
  lineOutX: 135,
  preX: 1720, ap04X: 1240, ap06X: 985, ap08X: 735, ap11X: 365,
  // Y positions — EXH-UI-01-C02: canvas 820, conveyor 150px
  conveyorY: 420, conveyorH: 150,
  stationY: 330,
  wipY: 495,
  rso2BranchX: 1240, rso2BranchTopY: 230,
  // Zone positions
  rawX: 1720, rawW: 180, rawY: 70, rawH: 300,
  fgX: 30, fgW: 180, fgY: 70, fgH: 300,
  offLineX: 500, offLineW: 700, offLineY: 630, offLineH: 130,
  lineOutConnX: 1050, lineInConnX: 650,
  // Conveyor span
  convStartX: 110, convEndX: 1830,
};
const FB_STATION_X = VF_LAYOUT.stationX;
const FB_CANVAS_W = 1920, FB_CANVAS_H = 820;

// Position → visual token mapping (DG06-01-C02 frozen)
const VF_TOKEN = {
  'PRE-ASSY':'STATOR','AP01':'STATOR','AP02':'STATOR','AP03':'STATOR','AP04':'STATOR',
  'AP05':'JOINED','AP06':'PRETEST','AP07':'TESTED','AP08':'TESTED','AP09':'TESTED',
  'AP10':'PACKED','AP11':'PACKED'
};
const VF_TOKEN_LABEL = {STATOR:'STATOR',JOINED:'JOINED',PRETEST:'PRE-TEST',TESTED:'TESTED',PACKED:'PACKED'};

// Station operation names (C03R canonical)
const STATION_OPS = {
  'PRE-ASSY':'Prep','AP01':'TBox fit','AP02':'TBox wire','AP03':'SSO2 QC',
  'AP04':'Rotor join','AP05':'Motor fit','AP06':'E-test','AP07':'Finish',
  'AP08':'Visual QC','AP09':'Box','AP10':'Pack','AP11':'Final QC'
};
const STATION_ARIA_OPS = {
  'PRE-ASSY':'Preparation','AP01':'Terminal box installation','AP02':'Terminal box wiring','AP03':'SSO2 and terminal-box quality check',
  'AP04':'RSO2 and bearing / lock-screw join','AP05':'Bearing, fan and cover assembly','AP06':'Electrical test','AP07':'Nameplate and finish',
  'AP08':'Visual inspection','AP09':'Boxing','AP10':'Pack and palletize','AP11':'Packing quality check'
};

/* ═══════════════════════════════════════
   VF Icon Library — Lucide-style Line Icons
   All icons: 24px viewBox, 1.5 stroke, round caps/joins
   No external dependencies, all embedded SVG paths
   ═══════════════════════════════════════ */
const VF_ICON = {
  // Core path data (viewBox 24x24)
  paths: {
    activity: 'M22 12h-4l-3 9L9 3l-3 9H2',
    wrench: 'M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z',
    eye: 'M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z',
    package: 'M16.5 9.4 7.55 4.24 M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z M3.29 7 12 12l8.71-5 M12 22V12',
    clipboard: 'M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2 M15 2H9a1 1 0 0 0-1 1v2a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V3a1 1 0 0 0-1-1z',
    checkCircle: 'M22 11.08V12a10 10 0 1 1-5.93-9.14 M22 4 12 14.01l-3-3',
    alertTriangle: 'M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z M12 9v4 M12 17h.01',
    xCircle: 'M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0z M15 9l-6 6 M9 9l6 6',
    monitor: 'M20 3H4a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2z M8 21h8 M12 17v4',
    camera: 'M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z M12 16a3 3 0 1 0 0-6 3 3 0 0 0 0 6z',
    user: 'M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2 M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z',
    box: 'M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z',
    check: 'M20 6 9 17l-5-5',
    link: 'M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71 M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71',
    zap: 'M13 2 3 14h9l-1 8 10-12h-9l1-8z',
    loader: 'M21 12a9 9 0 1 1-6.219-8.56',
    search: 'M21 21l-4.3-4.3 M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16z',
    settings: 'M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z',
    helpCircle: 'M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3 M12 17h.01 M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0z',
    maximize: 'M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3',
    arrowLeft: 'M19 12H5 M12 19l-7-7 7-7',
    play: 'M6 4l14 8-14 8z',
    pause: 'M6 4h4v16H6z M14 4h4v16h-4z',
    plus: 'M12 5v14 M5 12h14',
    minus: 'M5 12h14',
    refresh: 'M21 2v6h-6 M3 12a9 9 0 0 1 15-6.7L21 8 M3 22v-6h6 M21 12a9 9 0 0 1-15 6.7L3 16',
    download: 'M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4 M7 10l5 5 5-5 M12 15V3'
  },

  // Render icon by name at given x,y with size and optional color
  svg(name, x, y, size, color) {
    const d = this.paths[name];
    if (!d) return '';
    const s = size || 16;
    const c = color || 'currentColor';
    return `<svg x="${x-s/2}" y="${y-s/2}" width="${s}" height="${s}" viewBox="0 0 24 24" fill="none" stroke="${c}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="${d}"/></svg>`;
  }
};

/* ═══════════════════════════════════════
   VF Visual Primitive Library (C03R Enhanced)
   ═══════════════════════════════════════ */
const VF = {
  // ── Carrier pallet — a neutral carrier, visually separate from the WIP. ──
  pallet(x, y) {
    const w=104, h=48;
    return `<g class="vf-pallet-shell">
      <rect x="${x-w/2}" y="${y-h/2}" width="${w}" height="${h}" rx="5" fill="var(--vf-pallet)" stroke="#5c4e3f" stroke-width="1.5"/>
      <rect x="${x-w/2+7}" y="${y-h/2+7}" width="${w-14}" height="9" rx="2" fill="var(--vf-pallet-light)" opacity=".85"/>
      <rect x="${x-w/2+7}" y="${y-2}" width="${w-14}" height="4" rx="2" fill="#5c4e3f" opacity=".65"/>
      <rect x="${x-w/2+7}" y="${y+h/2-13}" width="${w-14}" height="6" rx="2" fill="var(--vf-pallet-light)" opacity=".78"/>
      <path d="M${x-38} ${y+24}v8M${x-12} ${y+24}v8M${x+12} ${y+24}v8M${x+38} ${y+24}v8" stroke="#5c4e3f" stroke-width="5" stroke-linecap="round"/>
    </g>`;
  },

  // ── Product visual stages are derived only from position (frozen contract). ──
  statorAssy(x, y) {
    return `<g aria-label="Stator assembly">
      <circle cx="${x}" cy="${y-8}" r="27" fill="#64748b" stroke="#334155" stroke-width="2"/>
      <circle cx="${x}" cy="${y-8}" r="18" fill="#e2e8f0" stroke="#475569" stroke-width="2"/>
      <circle cx="${x}" cy="${y-8}" r="10" fill="#334155"/>
      <path d="M${x-25} ${y-8}h50M${x} ${y-33}v50M${x-18} ${y-26}l36 36M${x+18} ${y-26}l-36 36" stroke="#94a3b8" stroke-width="2" opacity=".85"/>
      <rect x="${x+16}" y="${y-35}" width="22" height="15" rx="3" fill="#475569" stroke="#334155"/>
      <path d="M${x+21} ${y-20}v8m5-8v8m5-8v8" stroke="#fbbf24" stroke-width="2"/>
    </g>`;
  },

  // ── ROTOR — shaft (C02-C01: 1.5x for wider conveyor) ──
  rotor(x, y) {
    return `<g aria-label="Rotor component"><rect x="${x-34}" y="${y-7}" width="68" height="14" rx="7" fill="#64748b" stroke="#334155" stroke-width="1.5"/><circle cx="${x-17}" cy="${y}" r="13" fill="#94a3b8" stroke="#475569" stroke-width="1.5"/><circle cx="${x+17}" cy="${y}" r="13" fill="#94a3b8" stroke="#475569" stroke-width="1.5"/><path d="M${x-40} ${y}h80" stroke="#e2e8f0" stroke-width="3"/></g>`;
  },

  // ── MTR JOINED — assembled motor (C02-C01: 1.5x for wider conveyor) ──
  motorJoined(x, y) {
    return `<g aria-label="Joined motor"><rect x="${x-34}" y="${y-22}" width="68" height="36" rx="14" fill="#475569" stroke="#1e293b" stroke-width="2"/><circle cx="${x-25}" cy="${y-4}" r="17" fill="#64748b" stroke="#1e293b" stroke-width="2"/><circle cx="${x-25}" cy="${y-4}" r="7" fill="#cbd5e1"/><path d="M${x+34} ${y-4}h20" stroke="#94a3b8" stroke-width="7" stroke-linecap="round"/><rect x="${x-8}" y="${y-35}" width="22" height="13" rx="3" fill="#64748b" stroke="#1e293b"/><path d="M${x-10} ${y+14}v8m26-8v8" stroke="#1e293b" stroke-width="5" stroke-linecap="round"/><path d="M${x-8} ${y-12}h32m-32 8h32" stroke="#94a3b8" stroke-width="1.4" opacity=".9"/></g>`;
  },

  // ── MTR PRE-TEST — complete motor (C02-C01: 1.5x for wider conveyor) ──
  motorPreTest(x, y) {
    return `${this.motorJoined(x, y)}<g aria-label="Pre-test motor"><circle cx="${x-25}" cy="${y-4}" r="22" fill="none" stroke="#0f766e" stroke-width="5"/><path d="M${x-44} ${y-4}h8" stroke="#0f766e" stroke-width="4" stroke-linecap="round"/></g>`;
  },

  // ── TESTED MTR — blue T marker (C02-C01: 1.5x for wider conveyor) ──
  motorTested(x, y) {
    return `${this.motorPreTest(x, y)}<g aria-label="Tested motor"><rect x="${x-3}" y="${y-18}" width="22" height="11" rx="2" fill="#e2e8f0" stroke="#0f766e"/><path d="m${x+2} ${y-12} 3 3 7-7" fill="none" stroke="#15803d" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></g>`;
  },

  // ── PACKED GOODS — carton (C02-C01: 1.5x for wider conveyor) ──
  packedGoods(x, y) {
    return `<g aria-label="Packed goods"><path d="M${x-34} ${y-18}h68v42h-68z" fill="#cbd5e1" stroke="#475569" stroke-width="2"/><path d="M${x-34} ${y-18}v-10h68v10M${x} ${y-28}v52M${x-34} ${y-2}h68" fill="none" stroke="#64748b" stroke-width="1.5"/><rect x="${x-18}" y="${y-12}" width="22" height="10" rx="2" fill="#f8fafc"/><path d="M${x-14} ${y-7}h14" stroke="#94a3b8" stroke-width="1.5"/></g>`;
  },

  // ── Quality state overlay ──
  stateOverlay(x, y, state) {
    if (!state || state==='PASS'||state==='clear'||state==='CLEAR') return '';
    const isHold = state==='HOLD'||state==='retest_pending'||state==='reinspect_pending';
    const isTerminal = state==='FAILED_FINAL'||state==='failed_final';
    const color = isHold ? 'var(--vf-state-hold)' : 'var(--vf-state-fail)';
    const r = isTerminal ? 9 : 7;
    if (isTerminal) {
      return `<circle cx="${x+18}" cy="${y-20}" r="${r}" fill="${color}"/>
        <text x="${x+18}" y="${y-15}" fill="#fff" font-size="10" text-anchor="middle" font-weight="bold">✕</text>`;
    }
    return `<rect x="${x+10}" y="${y-28}" width="${r*2}" height="${r*2}" rx="3" fill="${color}" opacity="0.92"/>
      <text x="${x+10+r}" y="${y-17}" fill="#fff" font-size="${r+2}" text-anchor="middle" font-weight="bold">!</text>`;
  },

  // ── Station cells: one calm industrial language, operation icon carries the distinction. ──
  stationBody(x, y, archetype, stId) {
    const cx = x, cy = y;
    const isJoin = stId === 'AP04';
    const isCritical = ['AP06','AP08','AP11'].includes(stId);
    const stroke = isJoin ? '#b45309' : isCritical ? 'var(--vf-accent)' : '#64748b';
    let icon = '<path d="M-16 8h32M-12-8h24M-8-14v28M8-14v28"/>';
    if (stId === 'AP01') icon = '<rect x="-14" y="-10" width="28" height="20" rx="3"/><path d="M-6-10v-6m6 6v-6m6 6v-6"/>';
    if (stId === 'AP02') icon = '<path d="M-16-10c10 0 2 20 12 20S2-10 16-10M-16 9h32"/>';
    if (stId === 'AP03') icon = '<path d="M-14-10h28M-10-10v20m20-20v20M-16 10h32"/><circle cx="0" cy="0" r="4"/>';
    if (stId === 'AP04') icon = '<circle cx="-10" cy="0" r="8"/><circle cx="10" cy="0" r="8"/><path d="M-2 0h4M0-15v7"/>';
    if (stId === 'AP05') icon = '<circle cx="0" cy="0" r="13"/><path d="M0-13v26M-13 0h26M-9-9l18 18M9-9-9 9"/>';
    if (stId === 'AP06') icon = '<rect x="-14" y="-11" width="28" height="22" rx="3"/><path d="M-9 5 0-4l5 5 4-7"/>';
    if (stId === 'AP07') icon = '<rect x="-13" y="-10" width="26" height="20" rx="2"/><path d="M-8-4h16M-8 1h11M-8 6h8"/>';
    if (stId === 'AP08') icon = '<rect x="-14" y="-9" width="28" height="18" rx="3"/><circle cx="-3" cy="0" r="5"/><path d="M10-5h4v10h-4"/>';
    if (stId === 'AP09') icon = '<path d="M-14-8 0-15 14-8v16L0 15-14 8Z M-14-8 0 0l14-8M0 0v15"/>';
    if (stId === 'AP10') icon = '<path d="M-14-4h28v12h-28zM-10 8v6m10-6v6m10-6v6M-10-10h20"/>';
    if (stId === 'AP11') icon = '<rect x="-13" y="-12" width="26" height="24" rx="3"/><path d="m-7 1 5 5 9-11M-7-6h8"/>';
    if (stId === 'PRE-ASSY') icon = '<path d="M-16 7h32M-11 7V-8h22V7M-7-3h14"/>';
    return `<g class="vf-station-shell" filter="url(#vf-soft-shadow)">
      <rect x="${cx-48}" y="${cy-34}" width="96" height="68" rx="8" fill="#f8fafc" stroke="${stroke}" stroke-width="${isJoin || isCritical ? 2 : 1.3}"/>
      <g transform="translate(${cx} ${cy})" fill="none" stroke="${stroke}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${icon}</g>
      <circle cx="${cx+35}" cy="${cy-21}" r="4" fill="${isJoin ? '#f59e0b' : isCritical ? 'var(--vf-accent)' : '#94a3b8'}"/>
    </g>`;
  },

  // ── AP badge (larger for readability) ──
  apBadge(x, y, stId) {
    const cy = y - 46;
    const landmark = LANDMARK_LABELS[stId];
    const label = landmark ? `${stId} · ${landmark}` : stId.replace('PRE-ASSY','PRE');
    const width = landmark ? 82 : 50;
    return `<rect x="${x-width/2}" y="${cy-11}" width="${width}" height="22" rx="5" fill="#fff" stroke="#94a3b8" stroke-width="1.2"/>
      <text x="${x}" y="${cy+5}" fill="#334155" font-size="${landmark ? 10 : 12}" font-weight="800" text-anchor="middle" font-family="Consolas,monospace">${label}</text>`;
  },

  opName(x, y, stId) {
    const cy = y - 24;
    const name = STATION_OPS[stId] || stId;
    return `<text x="${x}" y="${cy}" fill="#334155" font-size="12" font-weight="700" text-anchor="middle">${name}</text>`;
  },

  badgeConnector(x, y) {
    return `<line x1="${x}" y1="${y-54}" x2="${x}" y2="${y-34}" stroke="var(--vf-accent-light)" stroke-width="1" stroke-dasharray="2,4"/>`;
  },

  conveyorRoller(x, y) {
    return `<rect x="${x-14}" y="${y+68}" width="28" height="5" rx="2.5" fill="var(--vf-conveyor-roller)"/>`;
  },

  // ── Complete station rendering ──
  station(x, y, stId, archetype, isLandmark, isSel, isHeld) {
    let html = '';
    const cy = y + 24;
    html += VF.badgeConnector(x, cy);
    html += `<g class="vf-station-group" data-station="${stId}" tabindex="0" role="button" aria-label="${stId}: ${STATION_ARIA_OPS[stId] || stId}">`;
    html += VF.stationBody(x, cy, archetype, stId);
    html += VF.conveyorRoller(x, y);
    html += VF.apBadge(x, y, stId);
    html += VF.opName(x, y, stId);
    html += `</g>`;
    return html;
  },

  // ── WIP token on pallet (EXH-UI-01: no permanent carrier text) ──
  wipToken(x, y, wipId, tokenType, isHeld, qResult, carrierId) {
    const ty = y + 165;  // from stationY(330) to wipY(495)
    let html = `<g class="vf-wip-group" data-wip="${wipId}" style="cursor:pointer;">`;
    html += VF.pallet(x, ty);
    if (tokenType === 'STATOR') html += VF.statorAssy(x, ty - 2);
    else if (tokenType === 'JOINED') html += VF.motorJoined(x, ty - 2);
    else if (tokenType === 'PRETEST') html += VF.motorPreTest(x, ty - 2);
    else if (tokenType === 'TESTED') html += VF.motorTested(x, ty - 2);
    else if (tokenType === 'PACKED') html += VF.packedGoods(x, ty - 2);
    if (isHeld || qResult === 'FAIL' || qResult === 'NG') {
      html += VF.stateOverlay(x, ty, isHeld ? 'HOLD' : qResult);
    }
    // Only show WIP ID (readable)
    html += `<text x="${x}" y="${ty+16}" fill="var(--vf-text-secondary)" font-size="10" text-anchor="middle">${wipId}</text>`;
    html += `</g>`;
    return html;
  }
};

/* Overview controls the composition; detail controls the selected sub-line.
   Each timer maps to a real runtime endpoint, so cards never claim a state
   that the simulation has not actually advanced. */
const SimulationCoordinator = {
  _allTimer: null,
  _lineTimers: new Map(),
  _pausedAllLines: new Set(),
  _speed: 100,
  _scenario: 'HAPPY_PATH',
  _locked: false,
  intervalMs() { return Math.round(120000 / this._speed); },
  speedNote() { const s = this.intervalMs() / 1000; return `${this._speed}× · ${s % 1 ? s.toFixed(1) : s} s/step`; },
  syncControls({ syncValues = false, source = null } = {}) {
    const allRunning = !!this._allTimer;
    const runningLines = this._runningLineCount();
    const activeDetailId = ctrlB && ctrlB._subLineId;
    const detailRunning = !!(activeDetailId && (allRunning || this._lineTimers.has(activeDetailId)));
    if (syncValues) {
      document.querySelectorAll('[data-sim-speed]').forEach(el => { if (el !== source) el.value = String(this._speed); });
      document.querySelectorAll('[data-sim-scenario]').forEach(el => { if (el !== source) el.value = this._scenario; });
    }
    document.querySelectorAll('[data-sim-speed-note]').forEach(el => { el.textContent = this.speedNote(); });
    this._setControlState('[data-sim-command="all-run"]', allRunning, 'Run all');
    this._setControlState('[data-sim-command="detail-run"]', detailRunning, 'Run line');
    document.querySelectorAll('[data-sim-command="all-pause"]').forEach(el => { el.disabled = !allRunning; });
    document.querySelectorAll('[data-sim-command="detail-pause"]').forEach(el => { el.disabled = !detailRunning; });
    document.querySelectorAll('[data-sim-command="all-step"], [data-sim-command="detail-step"], [data-sim-command="reset"]').forEach(el => { el.disabled = this._locked; });
    const overviewState = document.getElementById('vf-overview-sim-state');
    if (overviewState) { overviewState.textContent = runningLines ? `Simulation: RUNNING · ${runningLines}/6` : 'Simulation: PAUSED'; overviewState.classList.toggle('running', !!runningLines); }
    const detailState = document.getElementById('vf-detail-sim-state');
    if (detailState) { detailState.textContent = detailRunning ? 'Simulation: RUNNING' : 'Simulation: STOPPED'; detailState.classList.toggle('running', detailRunning); }
  },
  _setControlState(selector, running, label) {
    document.querySelectorAll(selector).forEach(el => {
      el.setAttribute('aria-pressed', String(running));
      el.className = running ? 'vf-btn primary' : 'vf-btn outline';
      el.innerHTML = running ? '<svg aria-hidden="true" viewBox="0 0 24 24"><path d="M6 6l12 12M18 6 6 18"/></svg>Running' : `<svg aria-hidden="true" viewBox="0 0 24 24"><path d="m5 4 14 8-14 8Zm0 0v16"/></svg>${label}`;
    });
  },
  _allLineIds() { return ['ASSY-SL01','ASSY-SL02','ASSY-SL03','ASSY-SL04','ASSY-SL05','ASSY-SL06']; },
  _activeAllLineIds() { return this._allLineIds().filter(id => !this._pausedAllLines.has(id)); },
  _runningLineCount() { return this._allTimer ? this._activeAllLineIds().length : this._lineTimers.size; },
  isLineRunning(subLineId) { return !!((this._allTimer && !this._pausedAllLines.has(subLineId)) || this._lineTimers.has(subLineId)); },
  async refreshActive() {
    await ctrl.refreshOverview();
    if (_inFrameB()) await ctrlB.refresh();
  },
  async stepAll() {
    if (this._locked || MotionEngine.isAnimating) return;
    this._locked = true;
    try {
      const activeIds = this._activeAllLineIds();
      if (activeIds.length === 6) await ctrl._stepRaw();
      else if (activeIds.length) await ctrl.call('step-lines', { sub_line_ids: activeIds });
      await ctrl.refreshOverview();
      if (_inFrameB() && this.isLineRunning(ctrlB._subLineId)) await ctrlB.refresh();
    } finally {
      this._locked = false;
      this.syncControls();
    }
  },
  async stepLine(subLineId) {
    if (!subLineId || this._locked || MotionEngine.isAnimating) return;
    this._locked = true;
    try {
      await ctrlB._stepLineRaw(subLineId);
      await ctrl.refreshOverview();
    } finally {
      this._locked = false;
      this.syncControls();
    }
  },
  startAll() {
    if (this._allTimer) return;
    [...this._lineTimers.keys()].forEach(id => this.stopLine(id));
    this._pausedAllLines.clear();
    this._allTimer = setInterval(() => { if (!this._locked && !MotionEngine.isAnimating) this.stepAll(); }, this.intervalMs());
    this.syncControls();
  },
  stopAll() {
    if (this._allTimer) clearInterval(this._allTimer);
    this._allTimer = null;
    this._pausedAllLines.clear();
    this.syncControls();
  },
  toggleAll() { this._allTimer ? this.stopAll() : this.startAll(); },
  pauseAll() { this._stopAllTimers(); },
  startLine(subLineId) {
    if (!subLineId || this._lineTimers.has(subLineId)) return;
    if (this._allTimer) {
      this._pausedAllLines.delete(subLineId);
      this.syncControls();
      ctrl.refreshOverview();
      return;
    }
    const timer = setInterval(() => { if (!this._locked && !MotionEngine.isAnimating) this.stepLine(subLineId); }, this.intervalMs());
    this._lineTimers.set(subLineId, timer);
    this.syncControls();
    ctrl.refreshOverview();
  },
  stopLine(subLineId) {
    if (this._allTimer) {
      this._pausedAllLines.add(subLineId);
      this.syncControls();
      ctrl.refreshOverview();
      return;
    }
    const timer = this._lineTimers.get(subLineId);
    if (timer) clearInterval(timer);
    this._lineTimers.delete(subLineId);
    this.syncControls();
    ctrl.refreshOverview();
  },
  toggleLine(subLineId) { this.isLineRunning(subLineId) ? this.stopLine(subLineId) : this.startLine(subLineId); },
  pauseLine(subLineId) { this.stopLine(subLineId); },
  _stopAllTimers() {
    this.stopAll();
    [...this._lineTimers.keys()].forEach(id => this.stopLine(id));
  },
  setSpeed(value, source = null) {
    const speed = Number(value);
    this._speed = [1,2,5,10,20,50,100,200].includes(speed) ? speed : 100;
    ctrl._speed = this._speed; ctrlB._speed = this._speed;
    if (this._allTimer) { clearInterval(this._allTimer); this._allTimer = setInterval(() => { if (!this._locked && !MotionEngine.isAnimating) this.stepAll(); }, this.intervalMs()); }
    this._lineTimers.forEach((timer, id) => { clearInterval(timer); this._lineTimers.set(id, setInterval(() => { if (!this._locked && !MotionEngine.isAnimating) this.stepLine(id); }, this.intervalMs())); });
    this.syncControls({ syncValues: true, source });
  },
  async setScenario(value, source = null) { this._scenario = value || 'HAPPY_PATH'; this.syncControls({ syncValues: true, source }); await this.reset(); },
  async reset() {
    this._stopAllTimers();
    this._locked = true;
    MotionEngine.cancel();
    ctrl._scenario = this._scenario; ctrlB._scenario = this._scenario;
    ctrl._selectionInitialized = false;
    ctrlB.clearInteraction();
    this.syncControls({ syncValues: true });
    try {
      await ctrl.call('reset', { scenario: this._scenario });
      await this.refreshActive();
    } finally {
      this._locked = false;
      this.syncControls({ syncValues: true });
    }
  }
};
const ctrl = {
  _autoTimer: null,
  _speed: 100,
  _scenario: 'HAPPY_PATH',
  _selectedSubLineId: 'ASSY-SL01',
  _selectionInitialized: false,
  _lastOverview: null,
  _liveStatus: 'INIT',

  async init() {
    await this.call('reset', { scenario: this._scenario });
    await this.refreshOverview();
    SimulationCoordinator.syncControls();
  },

  async reset() {
    return SimulationCoordinator.reset();
  },

  async step() {
    return SimulationCoordinator.stepAll();
  },

  async _stepRaw() {
    await this.call('step');
    await this.refreshOverview();
  },

  toggleAuto() { SimulationCoordinator.toggleAll(); },
  startAuto() { SimulationCoordinator.startAll(); },
  stopAuto() { SimulationCoordinator.stopAll(); },
  pause() { SimulationCoordinator.pauseAll(); },
  setSpeed(val) { SimulationCoordinator.setSpeed(val); },
  setScenario(val) { return SimulationCoordinator.setScenario(val); },

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
    if (this._liveStatus === 'LIVE') { el.textContent = 'Live'; el.style.color = 'var(--vf-state-pass)'; }
    else if (this._liveStatus === 'STALE') { el.textContent = 'Stale data'; el.style.color = 'var(--vf-state-hold)'; }
    else { el.textContent = 'Backend unavailable'; el.style.color = 'var(--vf-state-fail)'; }
  },

  /* ── Frame A Card Render ── */
  renderOverview(ov) {
    // Update shared top bar
    document.getElementById('demo-step').textContent = `DEMO STEP ${String(ov.demo_step_number).padStart(3,'0')}`;
    document.getElementById('global-scenario').textContent = ov.scenario || 'HAPPY_PATH';
    document.getElementById('total-created').textContent = ov.total_motors_created;
    document.getElementById('total-released').textContent = ov.total_motors_released;
    document.getElementById('total-holds').textContent = ov.total_active_holds;

    const wip = (ov.sub_lines||[]).reduce((s,sl)=>s+(sl.wips_on_line||0), 0);
    const wipEl = document.getElementById('vf-sb-wip'); if (wipEl) wipEl.textContent = wip;
    const summary = {
      'vf-overview-created': ov.total_motors_created,
      'vf-overview-released': ov.total_motors_released,
      'vf-overview-wip': wip,
      'vf-overview-holds': ov.total_active_holds,
    };
    Object.entries(summary).forEach(([id, value]) => { const el = document.getElementById(id); if (el) el.textContent = value ?? 0; });

    const hb = document.getElementById('total-holds-badge');
    if (hb) hb.style.color = ov.total_active_holds > 0 ? 'var(--vf-state-fail)' : 'var(--vf-text-muted)';

    this.renderStatus();

    if (!this._selectionInitialized) {
      if (ov.selected_sub_line_id) this._selectedSubLineId = ov.selected_sub_line_id;
      this._selectionInitialized = true;
    }

    const hydSl = (ov.sub_lines||[]).filter(s=>s.variant==='hydraulic');
    const thmSl = (ov.sub_lines||[]).filter(s=>s.variant==='thermal');

    document.getElementById('vf-hyd-cards').innerHTML = hydSl.map(sl => this._renderCard(sl)).join('');
    document.getElementById('vf-thm-cards').innerHTML = thmSl.map(sl => this._renderCard(sl)).join('');
    this._bindCardClicks();
  },

  _renderCard(sl) {
    const isExc = sl.is_exception;
    const isSel = sl.sub_line_id === this._selectedSubLineId;
    let cls = 'vf-subline-card';
    if (isSel) cls += ' selected';
    if (isExc) cls += ' exception';

    const isRunning = SimulationCoordinator.isLineRunning(sl.sub_line_id);
    let stateCls = isRunning ? 'operating' : 'stopped';
    let stateLabel = isRunning ? 'RUNNING' : 'STOPPED';
    if (isExc) { stateCls = 'hold'; stateLabel = 'QUALITY HOLD'; }

    // Mini process strip
    let dots = '';
    [...STATIONS].reverse().forEach((stId) => {
      const isLandmark = LANDMARKS.has(stId);
      const isHeld = isExc && sl.held_station === stId;
      let bg = '#D5DBE1';
      if (isHeld) bg = 'var(--vf-state-fail)';
      else if (isLandmark) bg = '#FFD700';
      else bg = '#A0C4A0';
      const dc = isLandmark ? ' landmark' : '';
      const dh = isHeld ? ' held' : '';
      dots += `<span class="vf-sc-dot${dc}${dh}" style="background:${bg};" title="${stId}${isLandmark?' ('+LANDMARK_LABELS[stId]+')':''}"></span>`;
    });

    return `<article class="${cls}" data-sl="${sl.sub_line_id}" data-variant="${sl.variant}" tabindex="0" role="button" aria-label="${sl.sub_line_id}, ${stateLabel}. View line detail.">
      <div class="vf-sc-header">
        <span class="vf-sc-id">${sl.sub_line_id}</span>
        <span class="vf-sc-state ${stateCls}">${stateLabel}</span>
      </div>
      <div class="vf-sc-meta">${sl.variant.toUpperCase()}</div>
      <div class="vf-sc-flow-cue" aria-label="Product flow from input on the right to output on the left">OUT ← IN</div><div class="vf-sc-strip">${dots}</div>
      <div class="vf-sc-stats">
        <span>WIP: <b>${sl.wips_on_line}</b></span>
        <span>OUT: <b>${sl.motors_released}</b></span>
        <span>DW: <b>${sl.dwell_number}</b></span>
        <span>t=<b>${sl.simulation_time_s.toFixed(0)}s</b></span>
      </div>
      ${isExc && sl.held_station ? `<div style="font-size:10px;color:var(--vf-state-fail);margin-top:4px;font-weight:700;">Hold · ${sl.held_station} / ${sl.held_wip_id}</div>` : ''}
      <span class="vf-sc-detail-hint">View line →</span>
    </article>`;
  },

  _bindCardClicks() {
    document.querySelectorAll('.vf-subline-card').forEach(card => {
      card.addEventListener('click', () => {
        const slId = card.getAttribute('data-sl');
        // A card is the visible entry point to the line, so a single click must
        // match its accessible name and keyboard behavior.  The selected-line
        // state and the simulation runtime are otherwise untouched.
        if (slId) { this._selectedSubLineId = slId; openFrameB(slId); }
      });
      card.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          const slId = card.getAttribute('data-sl');
          if (slId) { this._selectedSubLineId = slId; openFrameB(slId); }
        }
      });
    });
  },

  _refreshCardStyles() {
    document.querySelectorAll('.vf-subline-card').forEach(card => {
      const isSel = card.getAttribute('data-sl') === this._selectedSubLineId;
      card.classList.toggle('selected', isSel);
    });
  }
};

/* ═══════════════════════════════════════
   Frame A ↔ Frame B Navigation
   ═══════════════════════════════════════ */
function openFrameB(subLineId) {
  document.getElementById('frame-a').style.display = 'none';
  document.getElementById('frame-b').style.display = 'flex';
  document.getElementById('frame-b').style.flexDirection = 'column';
  document.getElementById('frame-b').style.height = '100%';

  // Toggle top bar elements: show Frame B context
  document.getElementById('demo-step').style.display = 'none';
  document.getElementById('global-scenario').style.display = 'none';
  document.getElementById('live-status').style.display = 'none';  // I09-P06: panel owns live indicator in Frame B
  document.getElementById('fb-sim-time').style.display = '';
  document.getElementById('fb-dwell').style.display = '';
  document.getElementById('fb-sub-line-id').style.display = '';
  document.getElementById('fb-variant').style.display = '';
  document.getElementById('fb-line-state').style.display = '';
  document.getElementById('fb-scenario').style.display = '';
  document.getElementById('fb-live-status').style.display = '';

  // Frame B owns its command bar; keep the legacy footer hidden.
  document.getElementById('vf-scenario-label-a').style.display = 'none';
  document.getElementById('speed-select').style.display = 'none';
  document.getElementById('vf-speed-label-a').style.display = 'none';
  document.getElementById('vf-footer').style.display = 'none';

  ctrlB._initZoomPan();
  ctrlB._speed = SimulationCoordinator._speed;
  ctrlB._scenario = SimulationCoordinator._scenario;
  ctrlB.init(subLineId).then(() => SimulationCoordinator.syncControls());
}

function closeFrameB() {
  MotionEngine.cancel();
  document.getElementById('frame-b').style.display = 'none';
  document.getElementById('frame-a').style.display = 'flex';
  document.getElementById('frame-a').style.flexDirection = 'column';
  document.getElementById('frame-a').style.height = '100%';

  // Toggle top bar elements: show Frame A context
  document.getElementById('demo-step').style.display = '';
  document.getElementById('global-scenario').style.display = '';
  document.getElementById('live-status').style.display = '';  // I09-P06: restore Frame A live indicator
  document.getElementById('fb-sim-time').style.display = 'none';
  document.getElementById('fb-dwell').style.display = 'none';
  document.getElementById('fb-sub-line-id').style.display = 'none';
  document.getElementById('fb-variant').style.display = 'none';
  document.getElementById('fb-line-state').style.display = 'none';
  document.getElementById('fb-scenario').style.display = 'none';
  document.getElementById('fb-live-status').style.display = 'none';

  // Restore the small Frame A selector strip.
  document.getElementById('vf-scenario-label-a').style.display = '';
  document.getElementById('speed-select').style.display = '';
  document.getElementById('vf-speed-label-a').style.display = '';
  document.getElementById('vf-footer').style.display = 'none';

  ctrl.refreshOverview().then(() => { ctrl._refreshCardStyles(); SimulationCoordinator.syncControls(); });
}

/* ═══════════════════════════════════════
   Frame-Aware Top-Bar Control Router
   ═══════════════════════════════════════ */
function _inFrameB() {
  const fb = document.getElementById('frame-b');
  return !!fb && fb.style.display !== 'none';
}

function uiReset() {
  SimulationCoordinator.reset();
}

function uiStep() {
  SimulationCoordinator.stepAll();
}

function uiToggleAuto() {
  SimulationCoordinator.toggleAll();
}

function uiPause() {
  SimulationCoordinator.pauseAll();
}

/* ═══════════════════════════════════════
   I07 Motion Engine — Controlled Runtime-Truth Motion
   ═══════════════════════════════════════ */
const MotionEngine = {
  _plans: [],
  _rafId: null,
  _settleCallback: null,
  _animating: false,
  _prefersReduced: false,

  init() {
    this._prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    window.matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change', (e) => {
      this._prefersReduced = e.matches;
    });
  },

  /** Compare two snapshots, return MotionPlan[] for valid adjacent station transitions */
  detect(prevSnap, newSnap) {
    const plans = [];
    if (!prevSnap || !newSnap) return plans;
    if (prevSnap.sub_line_id !== newSnap.sub_line_id) return plans; // no cross-subline

    const prevMap = {};
    (prevSnap.positions || []).forEach(p => { prevMap[p.wip_id] = p.position_id; });

    for (const p of (newSnap.positions || [])) {
      const wipId = p.wip_id;
      const newPos = p.position_id;
      const prevPos = prevMap[wipId];
      if (!prevPos || prevPos === newPos) continue;

      const isHeld = p.is_quality_hold;
      const qResult = (p.latest_quality_result || '').toUpperCase();
      // I07-C02: quality_status is orthogonal to latest_quality_result.
      // FAILED_FINAL is terminal containment state, NOT a detection result.
      const qStatus = (p.quality_status || '').toUpperCase();

      // I07-C01: HOLD gates motion — held WIP never creates a plan
      if (isHeld) continue;

      // I07 frozen invariants: AP06 FAIL / AP08 NG → NO MOVE
      if (qResult === 'FAIL' || qResult === 'NG') continue;

      // I07-C02: FAILED_FINAL (terminal) gates motion independently
      if (qStatus === 'FAILED_FINAL') continue;

      const fromIdx = FB_STATIONS.indexOf(prevPos);
      const toIdx = FB_STATIONS.indexOf(newPos);
      if (fromIdx < 0 || toIdx < 0) continue;

      // I07-C01: forward-adjacent ONLY (reverse → direct settle, no interpolation)
      if (toIdx !== fromIdx + 1) continue;

      // AP04→AP05 normally changes WIP identity, so same-ID transitions are
      // not expected here. The genealogy-backed child handoff is added below.
      if (prevPos === 'AP04' && newPos === 'AP05') continue;

      plans.push({
        wip_id: wipId,
        fromX: FB_STATION_X[fromIdx],
        toX: FB_STATION_X[toIdx],
        tokenType: VF_TOKEN[newPos] || 'STATOR',
        duration: 450,
        transition_type: 'FORWARD_ADJACENT',
      });
    }
    // AP04 join creates a new motor child at AP05. Animate that child only
    // when the authoritative genealogy record proves the AP04 parentage.
    const nextMap = {};
    (newSnap.positions || []).forEach(p => { if (p.wip_id) nextMap[p.wip_id] = p; });
    for (const link of (newSnap.genealogy || [])) {
      const childId = link.child_wip_id;
      const child = nextMap[childId];
      const parents = link.parent_wip_ids || [];
      const hasAp04Parent = parents.some(parentId => prevMap[parentId] === 'AP04');
      const qResult = (child?.latest_quality_result || '').toUpperCase();
      const qStatus = (child?.quality_status || '').toUpperCase();
      if (!child || child.position_id !== 'AP05' || !hasAp04Parent || child.is_quality_hold || qResult === 'FAIL' || qResult === 'NG' || qStatus === 'FAILED_FINAL') continue;
      plans.push({
        wip_id: childId,
        fromX: FB_STATION_X[FB_STATIONS.indexOf('AP04')],
        toX: FB_STATION_X[FB_STATIONS.indexOf('AP05')],
        tokenType: VF_TOKEN.AP05 || 'JOINED',
        duration: 450,
        transition_type: 'JOIN_GENEALOGY_HANDOFF',
      });
    }
    return plans;
  },

  /** Start animation for detected plans; calls onSettle when all complete */
  animate(plans, onSettle) {
    this.cancel();
    if (!plans.length) { if (onSettle) onSettle(); return; }

    // Reduced motion: skip animation, settle immediately
    if (this._prefersReduced) {
      for (const plan of plans) {
        const el = document.getElementById(`wip-${plan.wip_id}`);
        if (el) el.removeAttribute('transform');
      }
      if (onSettle) onSettle();
      return;
    }

    this._plans = plans;
    this._settleCallback = onSettle;
    this._animating = true;
    const startTime = performance.now();
    const rollers = document.getElementById('vf-conveyor-rollers');

    // Pre-offset: move WIPs to fromX (they were rendered at toX)
    for (const plan of plans) {
      const el = document.getElementById(`wip-${plan.wip_id}`);
      if (!el) continue;
      const dx = plan.fromX - plan.toX;
      el.setAttribute('transform', `translate(${dx}, 0)`);
    }

    const tick = (now) => {
      const elapsed = now - startTime;
      let allDone = true;
      let beltEase = 0;

      for (let i = this._plans.length - 1; i >= 0; i--) {
        const plan = this._plans[i];
        const el = document.getElementById(`wip-${plan.wip_id}`);
        if (!el) { this._plans.splice(i, 1); continue; }

        const t = Math.min(elapsed / plan.duration, 1.0);
        // easeInOutCubic
        const ease = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
        beltEase = Math.max(beltEase, ease);
        const dx = (plan.fromX - plan.toX) * (1 - ease);
        el.setAttribute('transform', `translate(${dx}, 0)`);

        if (t < 1) allDone = false;
      }
      if (rollers) rollers.setAttribute('transform', `translate(${-40 * beltEase}, 0)`);

      if (!allDone && this._plans.length > 0) {
        this._rafId = requestAnimationFrame(tick);
      } else {
        // Settle: remove all transforms, re-render clean
        this._settle();
      }
    };

    this._rafId = requestAnimationFrame(tick);
  },

  _settle() {
    for (const plan of this._plans) {
      const el = document.getElementById(`wip-${plan.wip_id}`);
      if (el) el.removeAttribute('transform');
    }
    const rollers = document.getElementById('vf-conveyor-rollers');
    if (rollers) rollers.removeAttribute('transform');
    this._plans = [];
    this._animating = false;
    if (this._settleCallback) {
      const cb = this._settleCallback;
      this._settleCallback = null;
      cb();
    }
  },

  cancel() {
    if (this._rafId) { cancelAnimationFrame(this._rafId); this._rafId = null; }
    // Remove transforms from any remaining animated elements
    for (const plan of this._plans) {
      const el = document.getElementById(`wip-${plan.wip_id}`);
      if (el) el.removeAttribute('transform');
    }
    const rollers = document.getElementById('vf-conveyor-rollers');
    if (rollers) rollers.removeAttribute('transform');
    this._plans = [];
    this._animating = false;
    this._settleCallback = null;
  },

  get isAnimating() { return this._animating; },

  /** Clear previous snapshot context (sub-line switch, reset) */
  clearContext() {
    this.cancel();
  },
};

MotionEngine.init();

/* ═══════════════════════════════════════
   Frame B Controller
   ═══════════════════════════════════════ */
const ctrlB = {
  _subLineId: 'ASSY-SL01',
  _autoTimer: null,
  _speed: 100,
  _scenario: 'HAPPY_PATH',
  _lastSnapshot: null,
  _liveStatus: 'INIT',
  _selectedStation: null,
  _selectedWipId: null,
  _contextType: null,   // I09-P04: 'sso2' | 'rso2' | 'offline' | null
  _inspectorOpen: false,
  _popupTab: 'overview',
  _zoomLevel: 1,
  _panX: 0,
  _panY: 0,
  _stepLocked: false,  // I07: prevent overlapping step animations
  _snapVersion: 0,     // I07: increment per snapshot for tracking
  _proposedFlow: false,

  async init(subLineId) {
    this._subLineId = subLineId;
    this._selectedStation = null;
    this._selectedWipId = null;
    this._contextType = null;
    this._inspectorOpen = false;
    this._zoomLevel = 1; this._panX = 0; this._panY = 0;
    this._stepLocked = false;
    this._proposedFlow = false;
    this._snapVersion = 0;
    MotionEngine.clearContext();
    this._lastSnapshot = null;  // I07: no cross-subline motion
    document.getElementById('fb-scenario-select').value = SimulationCoordinator._scenario;
    document.getElementById('fb-speed-select').value = String(SimulationCoordinator._speed);
    this._renderGridAndConveyor();
    this._bindDrawerTabs();
    this._applyProposedFlow();
    await this.refresh();
  },

  clearInteraction() {
    MotionEngine.cancel();
    this._stepLocked = false;
    this._snapVersion = 0;
    this._selectedStation = null;
    this._selectedWipId = null;
    this._contextType = null;
    this._inspectorOpen = false;
    // I09-P04-C01: close stale popup/inspector presentation immediately,
    // BEFORE the async reset/refresh round-trip, so stale truth is never shown.
    this.closePopup();
    this._renderInspector(null);
    this._zoomLevel = 1; this._panX = 0; this._panY = 0;
    this._lastSnapshot = null;  // I07: discard stale snapshot
  },

  async reset() {
    return SimulationCoordinator.reset();
  },

  async step() {
    return SimulationCoordinator.stepLine(this._subLineId);
  },

  async _stepRaw() {
    return this._stepLineRaw(this._subLineId);
  },

  async _stepLineRaw(subLineId) {
    // I07-C01: block STEP during active motion or in-flight step
    if (this._stepLocked || MotionEngine.isAnimating) return;
    this._stepLocked = true;
    try {
      const snap = await this.call(`sub-line/${subLineId}/step`);
      this._liveStatus = 'LIVE';
      this._renderSnapshot(snap);
    } finally {
      this._stepLocked = false;
    }
  },

  back() { closeFrameB(); },
  toggleAuto() { SimulationCoordinator.toggleLine(this._subLineId); },
  startAuto() { SimulationCoordinator.startLine(this._subLineId); },
  stopAuto() { SimulationCoordinator.stopLine(this._subLineId); },
  pause() { SimulationCoordinator.pauseLine(this._subLineId); },
  setSpeed(val) { SimulationCoordinator.setSpeed(val); },
  setScenario(val) { return SimulationCoordinator.setScenario(val); },

  _syncAutoControls(isRunning) {
    SimulationCoordinator.syncControls();
  },

  toggleProposedFlow() {
    this._proposedFlow = !this._proposedFlow;
    if (this._proposedFlow) {
      this._contextType = 'proposed';
      this._selectedStation = null; this._selectedWipId = null;
      this._inspectorOpen = true;
      this._renderContextPopup(this._lastSnapshot);
    } else {
      this._contextType = null; this._inspectorOpen = false;
      this.closePopup();
    }
    this._applyProposedFlow();
  },

  _applyProposedFlow() {
    const toggle = document.getElementById('vf-proposed-flow-toggle');
    if (toggle) toggle.setAttribute('aria-expanded', String(!!this._proposedFlow));
  },

  _bindDrawerTabs() {
    const tabs = document.querySelectorAll('#vf-popup-tabs .vf-popup-tab');
    tabs.forEach(tab => {
      if (tab.dataset.bound === 'true') return;
      tab.dataset.bound = 'true';
      tab.addEventListener('click', () => this.setPopupTab(tab.dataset.tab || 'overview'));
      tab.addEventListener('keydown', (e) => {
        if (!['ArrowLeft','ArrowRight','Home','End'].includes(e.key)) return;
        e.preventDefault();
        const list = [...document.querySelectorAll('#vf-popup-tabs .vf-popup-tab')];
        const current = list.indexOf(tab);
        const next = e.key === 'Home' ? 0 : e.key === 'End' ? list.length - 1 : (current + (e.key === 'ArrowRight' ? 1 : -1) + list.length) % list.length;
        list[next].focus();
        this.setPopupTab(list[next].dataset.tab || 'overview');
      });
    });
  },

  setPopupTab(tab) {
    this._popupTab = tab;
    document.querySelectorAll('#vf-popup-tabs .vf-popup-tab').forEach(button => {
      const active = button.dataset.tab === tab;
      button.classList.toggle('active', active);
      button.setAttribute('aria-selected', String(active));
      button.tabIndex = active ? 0 : -1;
    });
    if (this._lastSnapshot && this._inspectorOpen) this._renderPopup(this._lastSnapshot);
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
      this._liveStatus = 'LIVE';
      this._renderSnapshot(snap);
    } catch (_) {
      this._liveStatus = this._lastSnapshot ? 'STALE' : 'UNAVAILABLE';
      this.renderStatus();
    }
  },

  _renderSnapshot(snap) {
    this._snapVersion++;
    // One shared rendering path is used for both initial refresh and the
    // detail bar's per-line Step/Run command, so motion cannot disappear
    // merely because the control surface changed.
    const plans = MotionEngine.detect(this._lastSnapshot, snap);
    this._renderStatic(snap);
    this._renderWips(snap);
    if (plans.length > 0) {
      MotionEngine.animate(plans, () => this._renderWips(snap));
    }
    this._lastSnapshot = snap;
  },

  renderStatus() {
    const el = document.getElementById('fb-live-status');
    if (!el) return;
    if (this._liveStatus === 'LIVE') { el.textContent = 'Live'; el.style.color = 'var(--vf-state-pass)'; }
    else if (this._liveStatus === 'STALE') { el.textContent = 'Stale data'; el.style.color = 'var(--vf-state-hold)'; }
    else { el.textContent = 'Backend unavailable'; el.style.color = 'var(--vf-state-fail)'; }
  },

  /* ── Grid + Conveyor Background (static, rendered once) ── */
  _renderGridAndConveyor() {
    // Grid
    const gridG = document.getElementById('vf-grid-bg');
    if (!gridG) return;
    let gh = '';
    for (let gx = 0; gx <= 1920; gx += 40) {
      gh += `<line x1="${gx}" y1="0" x2="${gx}" y2="1080" stroke="var(--vf-grid-minor)" stroke-width="0.5"/>`;
    }
    for (let gy = 0; gy <= 1080; gy += 40) {
      gh += `<line x1="0" y1="${gy}" x2="1920" y2="${gy}" stroke="var(--vf-grid-minor)" stroke-width="0.5"/>`;
    }
    // Major grid every 200
    for (let gx = 0; gx <= 1920; gx += 200) {
      gh += `<line x1="${gx}" y1="0" x2="${gx}" y2="1080" stroke="var(--vf-grid-major)" stroke-width="0.8"/>`;
    }
    for (let gy = 0; gy <= 1080; gy += 200) {
      gh += `<line x1="0" y1="${gy}" x2="1920" y2="${gy}" stroke="var(--vf-grid-major)" stroke-width="0.8"/>`;
    }
    gridG.innerHTML = gh;

    // Zone boxes (EXH-UI-01: corrected zone labels per frozen contract)
    const zonesG = document.getElementById('vf-zones');
    if (!zonesG) return;
    const L = VF_LAYOUT;
    zonesG.innerHTML = `
      <!-- ASSY INPUT / LINE START (RIGHT) -->
      <rect x="${L.rawX}" y="${L.rawY}" width="${L.rawW}" height="${L.rawH}" rx="5" fill="#FBFCFD" stroke="var(--vf-border)" stroke-width="1.2" stroke-dasharray="6,4"/>
      <text x="${L.rawX+L.rawW/2}" y="${L.rawY+16}" fill="var(--vf-text)" font-size="12" text-anchor="middle" font-weight="600">ASSY INPUT</text>
      <text x="${L.rawX+L.rawW/2}" y="${L.rawY+30}" fill="var(--vf-text-secondary)" font-size="10" text-anchor="middle">LINE START</text>

      <!-- ASSY OUTPUT / LINE END (LEFT) -->
      <rect x="${L.fgX}" y="${L.fgY}" width="${L.fgW}" height="${L.fgH}" rx="5" fill="#FBFCFD" stroke="var(--vf-border)" stroke-width="1.2" stroke-dasharray="6,4"/>
      <text x="${L.fgX+L.fgW/2}" y="${L.fgY+16}" fill="var(--vf-text)" font-size="12" text-anchor="middle" font-weight="600">ASSY OUTPUT</text>
      <text x="${L.fgX+L.fgW/2}" y="${L.fgY+30}" fill="var(--vf-text-secondary)" font-size="10" text-anchor="middle">LINE END</text>

       <!-- Proposed LINE OUT / LINE IN routing lives in the right-hand context drawer. -->`;

    // EXH-UI-01-C01: Global RIGHT→LEFT product-flow arrow in dedicated flow-cue layer
    // Rendered ABOVE conveyor, BELOW stations — visible at low opacity
    const flowG = document.getElementById('vf-flow-cue');
    if (flowG) {
      flowG.innerHTML = `<g opacity="0.14">
        <rect x="250" y="445" width="1500" height="65" rx="10" fill="var(--vf-accent)"/>
        <polygon points="250,445 160,477 250,510" fill="var(--vf-accent)"/>
      </g>`;
    }

    // Conveyor (EXH-UI-01: 150px height, pallet 100×80 fits inside)
    const convG = document.getElementById('vf-conveyor-group');
    if (!convG) return;
    let ch = '';
    ch += `<defs><clipPath id="vf-conveyor-clip"><rect x="${L.convStartX+6}" y="${L.conveyorY+16}" width="${L.convEndX-L.convStartX-12}" height="118" rx="5"/></clipPath></defs>`;
    ch += `<rect x="${L.convStartX}" y="${L.conveyorY+10}" width="${L.convEndX-L.convStartX}" height="130" rx="8" fill="var(--vf-conveyor-body)"/>`;
    ch += `<rect x="${L.convStartX}" y="${L.conveyorY}" width="${L.convEndX-L.convStartX}" height="10" rx="4" fill="var(--vf-conveyor-frame)"/>`;
    ch += `<rect x="${L.convStartX}" y="${L.conveyorY+L.conveyorH-10}" width="${L.convEndX-L.convStartX}" height="10" rx="4" fill="var(--vf-conveyor-frame)"/>`;
    // The roller surface moves only when an authoritative WIP motion plan exists.
    ch += `<g id="vf-conveyor-rollers" clip-path="url(#vf-conveyor-clip)">`;
    for (let rx = L.convStartX - 20; rx < L.convEndX + 40; rx += 40) {
      ch += `<rect x="${rx}" y="${L.conveyorY+22}" width="16" height="106" rx="4" fill="var(--vf-conveyor-roller)" opacity="0.4"/>`;
    }
    ch += `</g>`;

    convG.innerHTML = ch;

    // UI-CTX-02: render contextual source cues + off-line representative items
    this._renderContextSources();
    this._renderContextOffline();
  },

  /* ── UI-CTX-02: SSO2/RSO2 contextual source cues (static, context-only) ── */
  _renderContextSources() {
    const g = document.getElementById('fb-context-sources');
    if (!g) return;
    const source = (kind, x, title, subtitle, visual, targetX) => {
      const top = 102, visualY = 166, targetY = VF_LAYOUT.stationY - 10;
      return `<g class="vf-upstream-compact" data-context="${kind}" tabindex="0" role="button" aria-label="${title} upstream context">
        <rect x="${x-58}" y="${top-20}" width="116" height="126" rx="8"/>
        <text x="${x}" y="${top}" text-anchor="middle" class="vf-upstream-title">${title}</text>
        <text x="${x}" y="${top+13}" text-anchor="middle" class="vf-upstream-sub">${subtitle}</text>
        <g transform="translate(${x}, ${visualY})" opacity=".68">${visual}</g>
        <text x="${x}" y="${visualY+42}" text-anchor="middle" class="vf-upstream-output">OUTPUT</text>
        <path d="M${x} ${top+106}V${targetY-12}H${targetX}V${targetY}" class="vf-upstream-feed" marker-end="url(#arrowJoin)"/>
      </g>`;
    };
    g.innerHTML = source('sso2', VF_LAYOUT.stationX[1], 'SSO2', 'Stator source', VF.statorAssy(0, 0), VF_LAYOUT.stationX[1])
      + source('rso2', VF_LAYOUT.stationX[4], 'RSO2', 'Rotor source', VF.rotor(0, 0), VF_LAYOUT.stationX[4]);
    this._bindContextClicks();
  },

  /* ── UI-CTX-02: Off-line context tray (representative items, NOT runtime WIP) ── */
  _renderContextOffline() {
    const g = document.getElementById('fb-context-offline');
    if (!g) return;
    // LINE OUT / LINE IN is a proposed-context drawer, not a physical route
    // in the current factory model. Keep this legacy renderer inert.
    g.innerHTML = '';
    return;
    const L = VF_LAYOUT;
    const cx = L.offLineX + L.offLineW / 2;   // ~850
    const itemY = L.offLineY + 56;
    let html = '';

    // 3 representative ghost items (semi-finished / WIP / finished)
    html += `<g data-context="offline" style="cursor:pointer;">`;
    const items = [
      { x: cx - 230, type: 'stator', label: 'WIP' },
      { x: cx, type: 'mtr', label: 'MTR' },
      { x: cx + 230, type: 'packed', label: 'PACKED' },
    ];
    for (const it of items) {
      html += `<g opacity="0.45">`;
      html += `<rect x="${it.x - 34}" y="${itemY - 26}" width="68" height="52" rx="6" fill="none" stroke="var(--vf-text-muted)" stroke-width="1" stroke-dasharray="4,3"/>`;
      if (it.type === 'stator') html += VF.statorAssy(it.x, itemY - 4);
      else if (it.type === 'mtr') html += VF.motorJoined(it.x, itemY - 4);
      else html += VF.packedGoods(it.x, itemY - 2);
      html += `<text x="${it.x}" y="${itemY + 34}" fill="var(--vf-text-muted)" font-size="9" text-anchor="middle" font-weight="600">${it.label}</text>`;
      html += `</g>`;
    }
    // CONTEXT watermark
    html += `<text x="${L.offLineX + L.offLineW - 14}" y="${L.offLineY + L.offLineH - 10}" fill="var(--vf-text-muted)" font-size="9" text-anchor="end" opacity="0.7">CONTEXT — not live WIP</text>`;
    html += `</g>`;

    g.innerHTML = html;
    this._bindContextClicks();
  },

  /* ── I09-P04: Bind context source/offline click handlers ── */
  _bindContextClicks() {
    document.querySelectorAll('#fb-context-sources [data-context], #fb-context-offline [data-context]').forEach(el => {
      if (el._ctxBound) return;
      el._ctxBound = true;
      el.addEventListener('click', (e) => {
        e.stopPropagation();
        this.selectContext(el.getAttribute('data-context'));
      });
      el.addEventListener('keydown', (e) => {
        if (e.key !== 'Enter' && e.key !== ' ') return;
        e.preventDefault(); e.stopPropagation();
        this.selectContext(el.getAttribute('data-context'));
      });
    });
  },

  /* ── I09-P04: Context popup for source/off-line zones ── */
  selectContext(type) {
    this._proposedFlow = false;
    this._applyProposedFlow();
    this._contextType = type;
    this._selectedStation = null;
    this._selectedWipId = null;
    this._inspectorOpen = true;
    const snap = this._lastSnapshot;
    if (snap) { this._applyHighlights(); this._renderContextPopup(snap); this._renderInspector(snap); }
  },

  _renderContextPopup(snap) {
    const popup = document.getElementById('vf-popup');
    const title = document.getElementById('vf-popup-title');
    const body = document.getElementById('vf-popup-body');
    const tabs = document.getElementById('vf-popup-tabs');
    if (!this._contextType || !snap) { this.closePopup(); return; }
    if (tabs) tabs.style.display = 'none';

    const prod = snap.production || {};
    if (this._contextType === 'sso2') {
      title.textContent = 'SSO2 INPUT';
      body.innerHTML = `
        <div class="vf-context-note">Upstream stator + shield source feeding ASSY start / PRE-ASSY.</div>
        <div class="vf-popup-row"><span class="vf-popup-k">Context</span><span class="vf-popup-v">source</span></div>
        <div class="vf-popup-row"><span class="vf-popup-k">SSO2 buffer</span><span class="vf-popup-v">${prod.sso2_buffer !== undefined ? prod.sso2_buffer : 'not exposed'}</span></div>
        <div class="vf-context-tag">Context source — upstream line not simulated</div>`;
    } else if (this._contextType === 'rso2') {
      title.textContent = 'RSO2 ROTOR FEED';
      body.innerHTML = `
        <div class="vf-context-note">Rotor source feeding AP04 JOIN.</div>
        <div class="vf-popup-row"><span class="vf-popup-k">Feeds</span><span class="vf-popup-v">AP04 JOIN</span></div>
        <div class="vf-popup-row"><span class="vf-popup-k">RSO2 buffer</span><span class="vf-popup-v">${prod.rso2_buffer !== undefined ? prod.rso2_buffer : 'not exposed'}</span></div>
        <div class="vf-context-tag">Context source — upstream line not simulated</div>`;
    } else if (this._contextType === 'offline' || this._contextType === 'proposed') {
      title.textContent = 'LINE-OUT / OFF-LINE CONTEXT';
      body.innerHTML = `
        <div class="vf-context-note">Proposed flow only. Items may leave the main line for inspection, diagnosis or verification; this is not factory-confirmed runtime routing.</div>
        <div class="vf-popup-row"><span class="vf-popup-k">Active off-line occupancy</span><span class="vf-popup-v">not tracked in current demo</span></div>
        <div class="vf-context-tag">Proposed flow — context-only, not live WIP</div>`;
    } else {
      this.closePopup();
      return;
    }
    this.openPopup();
  },

  /* ── I07: Static elements rendered once per snapshot (stations, context, zones) ── */
  _renderStatic(snap) {
    this.renderStatus();
    if (!snap) return;

    // Top bar context
    document.getElementById('fb-sub-line-id').textContent = snap.sub_line_id || this._subLineId;
    const lineTitle = document.getElementById('vf-line-title');
    if (lineTitle) lineTitle.textContent = snap.sub_line_id || this._subLineId;
    document.getElementById('fb-variant').textContent = (snap.variant||'').toUpperCase();
    document.getElementById('fb-sim-time').textContent = `t=${(snap.simulation_time_s||0).toFixed(0)}s`;
    document.getElementById('fb-dwell').textContent = `DWELL ${snap.dwell_number||0}`;
    document.getElementById('fb-scenario').textContent = snap.scenario || this._scenario;

    const lsEl = document.getElementById('fb-line-state');
    const ls = snap.line_state || 'stopped';
    // I09-P04: present conveyor state semantically (stopped ≠ production stopped)
    if (ls === 'stopped') { lsEl.textContent = 'Conveyor: stopped (post-index)'; lsEl.style.background = '#EEF0F3'; lsEl.style.color = 'var(--vf-text-muted)'; }
    else if (ls === 'operating') { lsEl.textContent = 'Conveyor: station work'; lsEl.style.background = '#E6F5EC'; lsEl.style.color = 'var(--vf-state-pass)'; }
    else if (ls === 'ready_to_index') { lsEl.textContent = 'Conveyor: ready to index'; lsEl.style.background = '#EAF2FF'; lsEl.style.color = 'var(--vf-accent)'; }
    else if (ls === 'indexing') { lsEl.textContent = 'Conveyor: indexing'; lsEl.style.background = '#FFF3CD'; lsEl.style.color = 'var(--vf-state-hold)'; }
    else { lsEl.textContent = ls.toUpperCase(); lsEl.style.background = '#EEF0F3'; lsEl.style.color = 'var(--vf-text-muted)'; }

    const prod = snap.production || {};
    document.getElementById('fb-prod-text').textContent =
      `Created: ${prod.motors_created||0}  Released: ${prod.motors_released||0}  On Line: ${prod.wips_on_line||0}  Holds: ${prod.active_quality_holds||0}`;

    const wipEl = document.getElementById('vf-sb-wip'); if (wipEl) wipEl.textContent = prod.wips_on_line||0;
    document.getElementById('total-created').textContent = prod.motors_created||0;
    document.getElementById('total-released').textContent = prod.motors_released||0;
    document.getElementById('total-holds').textContent = prod.active_quality_holds||0;
    const inlineMetrics = {
      'vf-created-inline': prod.motors_created||0,
      'vf-released-inline': prod.motors_released||0,
      'vf-wip-inline': prod.wips_on_line||0,
      'vf-holds-inline': prod.active_quality_holds||0,
    };
    Object.entries(inlineMetrics).forEach(([id, value]) => { const el = document.getElementById(id); if (el) el.textContent = value; });

    if (this._inspectorOpen && this._selectedWipId) {
      const pos = (snap.positions||[]).find(p => p.wip_id === this._selectedWipId);
      this._selectedStation = pos ? pos.position_id : null;
    }

    const posMap = {};
    for (const p of (snap.positions||[])) posMap[p.position_id] = p;

    const stationsG = document.getElementById('fb-stations');
    if (!stationsG) return;
    let html = '';
    const selSt = this._selectedStation;
    const L = VF_LAYOUT;

    // Stations (static — no motion on these)
    FB_STATIONS.forEach((stId, si) => {
      const sx = FB_STATION_X[si];
      const sy = L.stationY;
      const p = posMap[stId] || {};
      const isLandmark = !!FB_LANDMARKS[stId];
      const isHeld = p.is_quality_hold;
      const isSel = selSt === stId;

      let archetype = 'MANUAL';
      if (stId === 'PRE-ASSY') archetype = 'INPUT';
      else if (stId === 'AP03') archetype = 'CHECK';
      else if (stId === 'AP04') archetype = 'JOIN';
      else if (stId === 'AP06') archetype = 'TEST';
      else if (stId === 'AP08') archetype = 'VISION';
      else if (stId === 'AP09') archetype = 'PACK';
      else if (stId === 'AP10') archetype = 'PACK';
      else if (stId === 'AP11') archetype = 'FINAL';

      html += VF.station(sx, sy, stId, archetype, isLandmark, isSel, isHeld);
      if (isHeld && p.held_reason) {
        html += `<text x="${sx}" y="${sy+96}" fill="var(--vf-state-fail)" font-size="9" text-anchor="middle">${p.held_reason}</text>`;
      }
    });

    // UI-CTX-02: SSO2/RSO2 source cues moved to _renderContextSources.
    // Only PACKED GOODS contextual pallet remains in ASSY OUTPUT zone.
    html += `<g transform="translate(${L.fgX+L.fgW/2}, ${L.fgY+220})">${VF.pallet(0, 0)}${VF.packedGoods(0, -2)}</g>`;
    html += `<text x="${L.fgX+L.fgW/2}" y="${L.fgY+178}" fill="var(--vf-text-secondary)" font-size="11" text-anchor="middle" font-weight="600">PACKED GOODS</text>`;

    stationsG.innerHTML = html;
    this._applyHighlights();
    this._bindStationClicks();
    this._renderEventStrip(snap);
    this._renderGenealogyContext(snap);
    this._renderInspector(snap);
    this.applyViewBox();
  },

  /* ── I07: WIP rendering with IDs for motion targeting ── */
  _renderWips(snap) {
    const wipsG = document.getElementById('fb-wips');
    if (!wipsG || !snap) return;
    const posMap = {};
    for (const p of (snap.positions||[])) posMap[p.position_id] = p;
    const L = VF_LAYOUT;
    const sy = L.stationY;
    let html = '';

    FB_STATIONS.forEach((stId, si) => {
      const p = posMap[stId] || {};
      if (!p.is_occupied || !p.wip_id) return;
      const sx = FB_STATION_X[si];
      const isHeld = p.is_quality_hold;
      const qResult = p.latest_quality_result || '';
      const tokenType = VF_TOKEN[stId] || 'STATOR';

      // I07: render WIP with unique ID for motion targeting
      const isSelWip = (p.wip_id === this._selectedWipId);
      html += `<g id="wip-${p.wip_id}" class="vf-wip-group${isSelWip?' selected':''}" data-wip="${p.wip_id}" tabindex="0" role="button" aria-label="WIP ${p.wip_id} at ${stId}">`;
      // I09-P05: dedicated selection ring behind WIP (visible on .selected, no text blur)
      html += `<rect class="vf-wip-sel-halo" x="${sx-56}" y="${sy+119}" width="112" height="92" rx="10"/>`;
      html += VF.pallet(sx, sy + 165);
      if (stId === 'PRE-ASSY') { /* preparation carrier intentionally empty */ }
      else if (tokenType === 'STATOR') html += VF.statorAssy(sx, sy + 163);
      else if (tokenType === 'JOINED') html += VF.motorJoined(sx, sy + 163);
      else if (tokenType === 'PRETEST') html += VF.motorPreTest(sx, sy + 163);
      else if (tokenType === 'TESTED') html += VF.motorTested(sx, sy + 163);
      else if (tokenType === 'PACKED') html += VF.packedGoods(sx, sy + 163);
      if (isHeld || qResult === 'FAIL' || qResult === 'NG') {
        html += VF.stateOverlay(sx, sy + 165, isHeld ? 'HOLD' : qResult);
      }
      // Keep the WIP identity legible on top of the dark conveyor.  Its physical
      // position is unchanged; this is just a label plate in the visual layer.
      html += `<rect class="vf-wip-label-plate" x="${sx-46}" y="${sy+104}" width="92" height="20" rx="5"/>`;
      html += `<text x="${sx}" y="${sy+118}" class="vf-wip-label" text-anchor="middle">${p.wip_id}</text>`;
      html += `</g>`;
    });

    wipsG.innerHTML = html;
    this._bindWipClicks();
  },

  _applyHighlights() {
    document.querySelectorAll('#fb-stations .vf-station-group').forEach(el => {
      const bg = el.querySelector('rect');
      if (bg) { bg.style.filter = ''; bg.classList.remove('selected'); }
    });
    if (this._selectedStation) {
      const el = document.querySelector(`#fb-stations .vf-station-group[data-station="${this._selectedStation}"]`);
      if (el) {
        const rects = el.querySelectorAll('rect');
        if (rects.length > 0) rects[0].style.filter = 'drop-shadow(0 0 6px rgba(47,111,219,0.4))';
      }
    }
    // I09-P04: selected-WIP highlight follow
    document.querySelectorAll('#fb-wips .vf-wip-group').forEach(el => {
      el.classList.toggle('selected', this._selectedWipId === el.getAttribute('data-wip'));
    });
  },

  _bindStationClicks() {
    document.querySelectorAll('#fb-stations .vf-station-group').forEach(el => {
      const select = (e) => {
        if (e.target.closest('.vf-wip-group')) return;
        const stId = el.getAttribute('data-station');
        this.selectStation(stId);
      };
      el.addEventListener('click', select);
      el.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); select(e); } });
    });
  },

  _bindWipClicks() {
    document.querySelectorAll('#fb-wips .vf-wip-group').forEach(el => {
      const select = (e) => {
        e.stopPropagation();
        const wipId = el.getAttribute('data-wip');
        if (wipId) this.selectWip(wipId);
      };
      el.addEventListener('click', select);
      el.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); select(e); } });
    });
  },

  /* ── Selection Model ── */
  selectStation(stId) {
    if (this._selectedStation === stId && !this._selectedWipId) { this.closeInspector(); return; }
    this._selectedStation = stId;
    this._selectedWipId = null;
    this._contextType = null;
    const snap = this._lastSnapshot;
    if (snap) {
      const pos = (snap.positions||[]).find(p => p.position_id === stId);
      if (pos && pos.wip_id) this._selectedWipId = pos.wip_id;
    }
    this._inspectorOpen = true;
    this._popupTab = 'overview';
    if (snap) { this._applyHighlights(); this._renderInspector(snap); this._renderPopup(snap); }
  },

  selectWip(wipId) {
    this._selectedWipId = wipId;
    this._selectedStation = null;
    this._contextType = null;
    const snap = this._lastSnapshot;
    if (snap) {
      const pos = (snap.positions||[]).find(p => p.wip_id === wipId);
      if (pos) this._selectedStation = pos.position_id;
    }
    this._inspectorOpen = true;
    this._popupTab = 'overview';
    if (snap) { this._applyHighlights(); this._renderInspector(snap); this._renderPopup(snap); }
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
    } else { this._selectedStation = null; }
    if (snap) { this._applyHighlights(); this._renderInspector(snap); }
  },

  closeInspector() {
    this._inspectorOpen = false;
    this._selectedStation = null;
    this._selectedWipId = null;
    this._contextType = null;
    this._proposedFlow = false;
    this._applyProposedFlow();
    this._applyHighlights();
    this._renderInspector(this._lastSnapshot);
    this.closePopup();
  },

  /* ── Popup ── */
  openPopup() { const el = document.getElementById('vf-popup'); el.classList.add('open'); el.setAttribute('aria-hidden', 'false'); },
  closePopup() { const el = document.getElementById('vf-popup'); el.classList.remove('open'); el.setAttribute('aria-hidden', 'true'); },

  _renderPopup(snap) {
    if (!this._inspectorOpen || !snap) { this.closePopup(); return; }
    const title = document.getElementById('vf-popup-title');
    const body = document.getElementById('vf-popup-body');
    const tabs = document.getElementById('vf-popup-tabs');
    if (tabs) tabs.style.display = '';

    const stId = this._selectedStation;
    const wipId = this._selectedWipId;
    const posMap = {};
    for (const p of (snap.positions||[])) posMap[p.position_id] = p;
    const pos = stId ? (posMap[stId] || null) : null;
    const effectiveWipId = pos?.wip_id || wipId;
    const recs = (snap.quality_records||[]).filter(qr => qr.wip_id === effectiveWipId)
      .sort((a,b) => (a.simulation_time_s||0) - (b.simulation_time_s||0));
    const tab = this._popupTab || 'overview';
    this.setPopupTabState(tab);

    if (pos && !pos.is_occupied) {
      title.textContent = `${stId} — Empty`;
      body.innerHTML = `<div class="vf-popup-empty">No WIP at this station</div>`;
    } else if (!effectiveWipId && !pos) {
      title.textContent = 'Inspector';
      body.innerHTML = '<div class="vf-popup-empty">Select a station or WIP</div>';
    } else {
      title.textContent = pos ? `${stId} — ${effectiveWipId}` : `WIP ${effectiveWipId}`;
      if (tab === 'quality') body.innerHTML = this._popupQualityHtml(recs);
      else if (tab === 'history') body.innerHTML = this._popupHistoryHtml(effectiveWipId, pos, snap, recs);
      else if (tab === 'genealogy') body.innerHTML = this._popupGenealogyHtml(effectiveWipId, snap);
      else body.innerHTML = this._popupSummaryHtml(effectiveWipId, pos, snap, recs);
    }
    this.openPopup();
  },

  setPopupTabState(tab) {
    document.querySelectorAll('#vf-popup-tabs .vf-popup-tab').forEach(button => {
      const active = button.dataset.tab === tab;
      button.classList.toggle('active', active);
      button.setAttribute('aria-selected', String(active));
      button.tabIndex = active ? 0 : -1;
    });
  },

  _popupSummaryHtml(wipId, pos, snap, recs) {
    const onLine = (snap.positions||[]).some(p => p.wip_id === wipId);
    const q = pos?.latest_quality_result || 'clear';
    const qColor = q === 'PASS' ? 'var(--vf-state-pass)' : q === 'clear' ? 'var(--vf-text-muted)' : 'var(--vf-state-fail)';
    let html = pos ? `<div class="vf-popup-row"><span class="vf-popup-k">Station</span><span class="vf-popup-v">${pos.position_id} — ${pos.station_label||pos.position_id}</span></div>` : '';
    html += `<div class="vf-popup-row"><span class="vf-popup-k">WIP</span><span class="vf-popup-v vf-mono">${wipId}</span></div>`;
    if (pos?.wip_type) html += `<div class="vf-popup-row"><span class="vf-popup-k">Product</span><span class="vf-popup-v">${pos.wip_type}</span></div>`;
    if (pos?.carrier_id) html += `<div class="vf-popup-row"><span class="vf-popup-k">Carrier</span><span class="vf-popup-v vf-mono">${pos.carrier_id}</span></div>`;
    html += `<div class="vf-popup-row"><span class="vf-popup-k">Line status</span><span class="vf-popup-v">${pos?.manufacturing_status || (onLine ? 'active' : 'historical')}</span></div>`;
    html += `<div class="vf-popup-row"><span class="vf-popup-k">Quality</span><span class="vf-popup-v" style="color:${qColor}">${q}${pos?.attempt_number>1?' #'+pos.attempt_number:''}</span></div>`;
    if (pos?.is_quality_hold) html += `<div class="vf-popup-row"><span class="vf-popup-k">Hold</span><span class="vf-popup-v" style="color:var(--vf-state-fail)">${pos.held_reason||'Active'}</span></div>`;
    if (!onLine) html += `<div class="vf-context-tag">Historical record — this WIP is not currently on the line.</div>`;
    html += `<div class="vf-popup-row"><span class="vf-popup-k">Quality records</span><span class="vf-popup-v">${recs.length}</span></div>`;
    return html;
  },

  _popupQualityHtml(recs) {
    if (!recs.length) return '<div class="vf-popup-empty">No quality records for this WIP.</div>';
    return `<h3 class="vf-popup-section-title">Quality records</h3>${recs.map(r => `<div class="vf-popup-event"><div class="vf-popup-event-head"><span>${r.station_id} · ${r.disposition}</span><span>#${r.attempt_number||1}</span></div><small>${r.check_type||'Inspection'}${r.reason_code?' · '+r.reason_code:''} · t=${(r.simulation_time_s||0).toFixed(0)}s</small></div>`).join('')}`;
  },

  _popupHistoryHtml(wipId, pos, snap, recs) {
    const onLine = (snap.positions||[]).some(p => p.wip_id === wipId);
    let html = `<h3 class="vf-popup-section-title">Trace</h3><div class="vf-popup-row"><span class="vf-popup-k">Current</span><span class="vf-popup-v">${onLine ? (pos?.position_id || 'On line') : 'Exited line'}</span></div>`;
    html += `<div class="vf-popup-row"><span class="vf-popup-k">Events</span><span class="vf-popup-v">${recs.length}</span></div>`;
    return html + (recs.length ? `<div class="vf-popup-sep"></div>${recs.map(r => `<div class="vf-popup-event"><div class="vf-popup-event-head"><span>${r.station_id}</span><span>${r.disposition}</span></div><small>${r.check_type||'Inspection'} · t=${(r.simulation_time_s||0).toFixed(0)}s</small></div>`).join('')}` : '<div class="vf-popup-empty">No history has been published for this WIP.</div>');
  },

  _popupGenealogyHtml(wipId, snap) {
    const links = (snap.genealogy||[]).filter(g => g.child_wip_id === wipId || (g.parent_wip_ids||[]).includes(wipId));
    if (!links.length) return '<div class="vf-popup-empty">No AP04 genealogy is recorded for this WIP.</div>';
    return `<h3 class="vf-popup-section-title">AP04 genealogy</h3>${links.map(g => `<div class="vf-popup-event"><div class="vf-popup-event-head"><span class="vf-mono">${g.child_wip_id}</span><span>${g.join_station||'AP04'}</span></div><small>Created from ${(g.parent_wip_ids||[]).map(p=>`<span class="vf-insp-link" onclick="ctrlB.selectWip('${p}')">${p}</span>`).join(' + ')} · t=${(g.join_time_s||0).toFixed(0)}s</small></div>`).join('')}`;
  },

  /* ── Inspector Render (legacy data integration) ── */
  _renderInspector(snap) {
    const insp = document.getElementById('vf-inspector');
    if (!insp) return;

    if (!this._inspectorOpen || !snap) {
      insp.classList.remove('open');
      return;
    }
    insp.classList.add('open');

    const stId = this._selectedStation;
    const wipId = this._selectedWipId;
    const posMap = {};
    for (const p of (snap.positions||[])) posMap[p.position_id] = p;
    const pos = stId ? (posMap[stId] || null) : null;

    const ctxTitle = this._contextType === 'sso2' ? 'SSO2 INPUT'
      : this._contextType === 'rso2' ? 'RSO2 ROTOR FEED'
      : (this._contextType === 'offline' || this._contextType === 'proposed') ? 'PROPOSED FLOW'
      : null;
    document.getElementById('vf-inspector-title').textContent =
      ctxTitle || (stId ? `${stId}${pos&&pos.station_label?': '+pos.station_label:''}` : (wipId||'Inspector'));

    this._renderSummary(pos, wipId, snap);
    this._renderQualityHistory(wipId, snap);
    this._renderMeasurements(wipId, snap);
    this._renderChecklist(wipId, snap);
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
    if (this._contextType) {
      // I09-P04: context selection — show semantic context in legacy inspector too
      if (this._contextType === 'sso2') {
        el.innerHTML = `<div class="vf-insp-row"><span class="vf-insp-k">Context</span><span class="vf-insp-v">SSO2 INPUT — upstream stator + shield source feeding ASSY start / PRE-ASSY.</span></div><div class="vf-insp-empty">Context source — upstream line not simulated</div>`;
      } else if (this._contextType === 'rso2') {
        el.innerHTML = `<div class="vf-insp-row"><span class="vf-insp-k">Context</span><span class="vf-insp-v">RSO2 ROTOR FEED — rotor source feeding AP04 JOIN.</span></div><div class="vf-insp-empty">Feeds AP04 JOIN — upstream line not simulated</div>`;
      } else {
        el.innerHTML = `<div class="vf-insp-row"><span class="vf-insp-k">Context</span><span class="vf-insp-v">LINE-OUT / OFF-LINE — representative items are context-only, not live WIP.</span></div>`;
      }
      return;
    }
    if (pos && pos.is_occupied && pos.wip_id) {
      const qColor = pos.latest_quality_result === 'PASS' ? 'var(--vf-state-pass)' : pos.latest_quality_result ? 'var(--vf-state-fail)' : 'var(--vf-text-muted)';
      let html = `<div class="vf-insp-row"><span class="vf-insp-k">Station</span><span class="vf-insp-v">${pos.position_id} — ${pos.station_label||pos.position_id}</span></div>`;
      html += `<div class="vf-insp-row"><span class="vf-insp-k">WIP</span><span class="vf-insp-v" style="font-weight:600">${pos.wip_id}</span></div>`;
      html += `<div class="vf-insp-row"><span class="vf-insp-k">Type</span><span class="vf-insp-v">${pos.wip_type||'—'}</span></div>`;
      if (pos.carrier_id) html += `<div class="vf-insp-row"><span class="vf-insp-k">Carrier</span><span class="vf-insp-v">${pos.carrier_id}</span></div>`;
      html += `<div class="vf-insp-row"><span class="vf-insp-k">Mfg Status</span><span class="vf-insp-v">${pos.manufacturing_status||'active'}</span></div>`;
      html += `<div class="vf-insp-row"><span class="vf-insp-k">Quality</span><span class="vf-insp-v" style="color:${qColor}">${pos.latest_quality_result||'clear'}${pos.attempt_number>1?' #'+pos.attempt_number:''}</span></div>`;
      if (pos.is_quality_hold) html += `<div class="vf-insp-row"><span class="vf-insp-k">HOLD</span><span class="vf-insp-v" style="color:var(--vf-state-fail);font-weight:600">${pos.held_reason||'Active'}</span></div>`;
      el.innerHTML = html;
    } else if (pos && !pos.is_occupied) {
      el.innerHTML = `<div class="vf-insp-row"><span class="vf-insp-k">Station</span><span class="vf-insp-v">${pos.position_id}</span></div><div class="vf-insp-empty">EMPTY — no WIP at this station</div>`;
    } else if (wipId) {
      const histRecs = (snap.quality_records||[]).filter(qr => qr.wip_id === wipId);
      const onLine = (snap.positions||[]).some(p => p.wip_id === wipId);
      el.innerHTML = `<div class="vf-insp-row"><span class="vf-insp-k">WIP</span><span class="vf-insp-v" style="font-weight:600">${wipId}</span></div>${!onLine?'<div class="vf-insp-historical">HISTORICAL — NOT CURRENTLY ON LINE</div>':''}<div class="vf-insp-row"><span class="vf-insp-k">Records</span><span class="vf-insp-v">${histRecs.length} quality records</span></div>`;
    } else {
      el.innerHTML = '<div class="vf-insp-empty">Select a station or WIP</div>';
    }
  },

  _renderQualityHistory(wipId, snap) {
    const el = document.getElementById('fb-insp-quality-content');
    if (!el) return;
    if (!wipId) { el.innerHTML = '<div class="vf-insp-empty">Select a WIP to see quality history</div>'; return; }
    const recs = (snap.quality_records||[]).filter(qr => qr.wip_id === wipId).sort((a,b) => a.simulation_time_s - b.simulation_time_s);
    if (!recs.length) { el.innerHTML = '<div class="vf-insp-empty">No quality records</div>'; return; }
    let html = '';
    for (const r of recs) {
      const dColor = r.disposition === 'PASS' ? 'var(--vf-state-pass)' : 'var(--vf-state-fail)';
      html += `<div class="vf-insp-qr"><div class="vf-insp-qr-head"><span class="vf-insp-qr-station">${r.station_id}</span><span style="color:${dColor};font-weight:600">${r.disposition}</span><span style="color:var(--vf-text-muted)">#${r.attempt_number}</span><span style="color:var(--vf-text-muted);font-size:10px">t=${(r.simulation_time_s||0).toFixed(0)}s</span></div><div class="vf-insp-qr-type">${r.check_type||'?'}</div>${r.reason_code?`<div class="vf-insp-qr-reason">Reason: ${r.reason_code}</div>`:''}</div>`;
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
      html += `<div class="vf-insp-meas-group"><div class="vf-insp-meas-station">${r.station_id} — ${r.check_type} #${r.attempt_number} <small>t=${(r.simulation_time_s||0).toFixed(0)}s</small></div>`;
      for (const m of (r.measurements||[])) {
        const v=m.value, lo=m.expected_min, hi=m.expected_max;
        let inRange = true;
        if (lo !== undefined && v < lo) inRange = false;
        if (hi !== undefined && v > hi) inRange = false;
        const rc = inRange ? 'var(--vf-state-pass)' : 'var(--vf-state-fail)';
        html += `<div class="vf-insp-meas-row"><span class="vf-insp-meas-name">${m.name}</span><span class="vf-insp-meas-val">${v}${m.unit||''}</span><span class="vf-insp-meas-range">[${lo||'—'},${hi||'—'}]</span><span style="color:${rc};font-size:10px;font-weight:600">${inRange?'IN RANGE':'OUT OF RANGE'}</span></div>`;
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
    const recs = (snap.quality_records||[]).filter(qr => qr.wip_id === wipId && qr.checklist && qr.checklist.length > 0);
    if (!recs.length) { section.style.display = 'none'; return; }
    section.style.display = '';
    let html = '';
    for (const r of recs) {
      html += `<div class="vf-insp-cl-group"><div class="vf-insp-cl-head">${r.station_id} — ${r.check_type} #${r.attempt_number}</div><div class="vf-insp-cl-items">`;
      for (const item of (r.checklist||[])) {
        html += `<div class="vf-insp-cl-item">${item.passed?'✓':'✕'} ${item.name}</div>`;
      }
      html += `</div></div>`;
    }
    el.innerHTML = html;
  },

  _renderInspGenealogy(wipId, snap) {
    const section = document.getElementById('fb-insp-genealogy');
    const el = document.getElementById('fb-insp-genealogy-content');
    if (!section || !el) return;
    if (!wipId) { section.style.display = 'none'; return; }
    const genealogy = snap.genealogy || [];
    const relevant = genealogy.filter(g => g.child_wip_id === wipId || (g.parent_wip_ids||[]).includes(wipId));
    if (!relevant.length) { section.style.display = 'none'; return; }
    section.style.display = '';
    let html = '';
    for (const g of relevant) {
      const parents = (g.parent_wip_ids||[]).map(p =>
        `<span class="vf-insp-link" onclick="ctrlB.selectWip('${p}')" title="Inspect parent">${p}</span>`
      ).join(' + ');
      html += `<div class="vf-insp-gen-row"><b style="color:#C8960E">${g.child_wip_id}</b> ← ${parents}<br><span style="font-size:10px;color:var(--vf-text-muted)">t=${(g.join_time_s||0).toFixed(0)}s @ ${g.join_station||'AP04'}</span></div>`;
    }
    el.innerHTML = html;
  },

  /* ── Event strip ── */
  _renderEventStrip(snap) {
    const strip = document.getElementById('vf-event-strip');
    const list = document.getElementById('fb-event-list');
    const inline = document.getElementById('fb-event-inline');
    if (!strip) return;
    const events = snap.recent_quality_events || [];
    if (!events.length) { strip.classList.remove('visible'); return; }
    strip.classList.add('visible');
    // Compact 1-line inline summary (C01)
    if (inline) {
      const latest = events.slice(-3).map(e =>
        `${e.disposition} ${e.wip_id} @ ${e.station_id}`
      ).join('  ·  ');
      inline.textContent = latest;
    }
    if (list) {
      list.innerHTML = events.slice(-10).map(e => {
        const dc = e.disposition === 'PASS' ? 'var(--vf-state-pass)' : 'var(--vf-state-fail)';
        return `<div class="vf-qe-item" onclick="ctrlB.selectEvent('${e.station_id}','${e.wip_id}')"><span style="color:${dc};font-weight:600">${e.disposition}</span> ${e.wip_id} @ ${e.station_id} #${e.attempt} <small>t=${(e.simulation_time_s||0).toFixed(0)}s</small></div>`;
      }).join('');
    }
  },

  _renderGenealogyContext(snap) {
    const el = document.getElementById('fb-genealogy-text');
    if (!el) return;
    const genealogy = snap.genealogy || [];
    if (!genealogy.length) { el.innerHTML = 'No joins recorded'; return; }
    el.innerHTML = genealogy.slice(-4).map(g =>
      `<div><b style="color:#C8960E">${g.child_wip_id}</b> ← ${(g.parent_wip_ids||[]).map(p=>`<span class="vf-insp-link" onclick="ctrlB.selectWip('${p}')">${p}</span>`).join(' + ')} @ t=${(g.join_time_s||0).toFixed(0)}s</div>`
    ).join('');
  },

  /* ── Zoom/Pan ── */
  _initZoomPan() {
    const svg = document.getElementById('fb-canvas-svg');
    if (!svg || svg._zoomInit) return;
    svg._zoomInit = true;

    svg.addEventListener('wheel', (e) => {
      e.preventDefault();
      const p = this._svgPoint(svg, e.clientX, e.clientY);
      if (!p) return;
      const oldZoom = this._zoomLevel;
      this._zoomLevel = Math.max(0.3, Math.min(2.5, oldZoom - e.deltaY * 0.003));
      if (this._zoomLevel === oldZoom) return;
      this.applyViewBox();
      const q = this._svgPoint(svg, e.clientX, e.clientY);
      if (!q) return;
      this._panX += (p.x - q.x) * FB_CANVAS_W / 1920;
      this._panY += (p.y - q.y) * FB_CANVAS_H / 1080;
      this.applyViewBox();
      const zl = document.getElementById('vf-zoom-label');
      if (zl) zl.textContent = Math.round(this._zoomLevel * 100) + '%';
    }, { passive: false });

    let dragging = false, startX, startY, startPanX, startPanY;
    svg.addEventListener('mousedown', (e) => {
      if (e.target === svg || e.target.classList.contains('vf-grid-bg') || (e.target.tagName === 'rect' && !e.target.closest('.vf-station-group') && !e.target.closest('.vf-wip-group'))) {
        dragging = true; startX = e.clientX; startY = e.clientY;
        startPanX = this._panX; startPanY = this._panY;
        svg.style.cursor = 'grabbing'; e.preventDefault();
      }
    });
    window.addEventListener('mousemove', (e) => {
      if (!dragging) return;
      const dx = (e.clientX - startX) * (FB_CANVAS_W / 1920) / this._zoomLevel;
      const dy = (e.clientY - startY) * (FB_CANVAS_H / 1080) / this._zoomLevel;
      this._panX = startPanX - dx; this._panY = startPanY - dy;
      this.applyViewBox();
    });
    window.addEventListener('mouseup', () => { if (dragging) { dragging = false; svg.style.cursor = 'grab'; } });
  },

  _svgPoint(svg, clientX, clientY) {
    const pt = svg.createSVGPoint();
    pt.x = clientX; pt.y = clientY;
    try {
      const ctm = svg.getScreenCTM();
      if (!ctm) return null;
      const sp = pt.matrixTransform(ctm.inverse());
      return { x: sp.x, y: sp.y };
    } catch (_) { return null; }
  },

  applyViewBox() {
    const svg = document.getElementById('fb-canvas-svg');
    if (!svg) return;
    const vw = FB_CANVAS_W / this._zoomLevel;
    const vh = FB_CANVAS_H / this._zoomLevel;
    svg.setAttribute('viewBox', `${this._panX} ${this._panY} ${vw} ${vh}`);
  },

  zoomIn() { this._zoomLevel = Math.min(2.5, this._zoomLevel * 1.3); this.applyViewBox(); const zl = document.getElementById('vf-zoom-label'); if (zl) zl.textContent = Math.round(this._zoomLevel * 100) + '%'; },
  zoomOut() { this._zoomLevel = Math.max(0.3, this._zoomLevel / 1.3); this.applyViewBox(); const zl = document.getElementById('vf-zoom-label'); if (zl) zl.textContent = Math.round(this._zoomLevel * 100) + '%'; },
  zoomReset() { this._zoomLevel = 1; this._panX = 0; this._panY = 0; this.applyViewBox(); const zl = document.getElementById('vf-zoom-label'); if (zl) zl.textContent = '100%'; }
};

/* ═══════════════════════════════════════
   S04 Fallback Controller (preserved)
   ═══════════════════════════════════════ */
const ctrlS04 = {
  _autoTimer: null, _speed: 100, _scenario: 'HAPPY_PATH',
  async init() { await this.call('reset', { scenario: this._scenario }); this.render(await this.call('snapshot')); },
  async reset() { this.stopAuto(); this._scenario = document.getElementById('scenario-select-s04').value; await this.call('reset', { scenario: this._scenario }); this.render(await this.call('snapshot')); },
  async step() { this.render(await this.call('step')); },
  toggleAuto() { this._autoTimer ? this.stopAuto() : this.startAuto(); },
  startAuto() { document.getElementById('btn-auto-s04').textContent = 'STOP'; document.getElementById('btn-pause-s04').disabled = false; this._autoTimer = setInterval(() => this.step(), Math.round(120000 / this._speed)); },
  stopAuto() { if (this._autoTimer) { clearInterval(this._autoTimer); this._autoTimer = null; } document.getElementById('btn-auto-s04').textContent = 'Run'; document.getElementById('btn-pause-s04').disabled = true; },
  pause() { if (this._autoTimer) this.stopAuto(); },
  setSpeed(val) { const speed = Number(val); this._speed = [1,2,5,10,20,50,100,200].includes(speed) ? speed : 100; if (this._autoTimer) { this.stopAuto(); this.startAuto(); } },
  setScenario(val) { this._scenario = val; this.reset(); },
  async call(action, body) { const opts = body ? { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body) } : { method:'POST' }; const resp = await fetch(`${API}/${action}`, opts); return resp.json(); },
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

/* ═══════════════════════════════════════
   Feature Detection + Boot
   EXH-UI-01-C01: Guarded — only boots when production DOM exists
   ═══════════════════════════════════════ */
async function detectS04B() {
  try { const r = await fetch(`${API}/overview`); return r.ok; } catch (_) { return false; }
}

document.addEventListener('DOMContentLoaded', async () => {
  // EXH-UI-01-C01: Harness isolation guard — do NOT auto-boot in harness context
  if (!document.getElementById('frame-a')) return;
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && _inFrameB()) ctrlB.closeInspector();
  });

  const s04b = await detectS04B();
  if (s04b) {
    document.getElementById('frame-a').style.display = 'flex';
    document.getElementById('frame-a').style.flexDirection = 'column';
    document.getElementById('frame-a').style.height = '100%';
    document.getElementById('frame-s04').style.display = 'none';
    document.getElementById('vf-scenario-label-a').style.display = '';
    document.getElementById('vf-footer').style.display = 'none';
    // Hide Frame B context in top bar
    ['fb-sim-time','fb-dwell','fb-sub-line-id','fb-variant','fb-line-state','fb-scenario','fb-live-status'].forEach(id => {
      const el = document.getElementById(id); if (el) el.style.display = 'none';
    });
    ctrl.init();
  } else {
    document.getElementById('frame-a').style.display = 'none';
    document.getElementById('frame-s04').style.display = 'flex';
    document.getElementById('frame-s04').style.flexDirection = 'column';
    document.getElementById('frame-s04').style.height = '100%';
    ctrlS04.init();
  }
});
