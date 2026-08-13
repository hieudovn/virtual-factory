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
  'PRE-ASSY':'Prep','AP01':'Stator Assy','AP02':'Term. Box','AP03':'Mech. Check',
  'AP04':'JOIN','AP05':'Mech. Assy','AP06':'EOL Test','AP07':'Finish',
  'AP08':'Vision','AP09':'Boxing','AP10':'Pack / Label','AP11':'Final QC'
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
  // ── Wooden pallet — EXH-UI-01: 100×80 ──
  pallet(x, y) {
    const w=100, h=80;
    return `<rect x="${x-w/2}" y="${y-h/2}" width="${w}" height="${h}" rx="4" fill="var(--vf-pallet-wood)" stroke="#8B7355" stroke-width="1.5"/>
      <rect x="${x-w/2-2}" y="${y-h/2+2}" width="${w+4}" height="6" rx="3" fill="var(--vf-pallet-dark)" opacity="0.15"/>
      <line x1="${x-w/2+7}" y1="${y-16}" x2="${x+w/2-7}" y2="${y-16}" stroke="var(--vf-pallet-dark)" stroke-width="1.8" opacity="0.3"/>
      <line x1="${x-w/2+7}" y1="${y}" x2="${x+w/2-7}" y2="${y}" stroke="var(--vf-pallet-dark)" stroke-width="1.8" opacity="0.3"/>
      <line x1="${x-w/2+7}" y1="${y+16}" x2="${x+w/2-7}" y2="${y+16}" stroke="var(--vf-pallet-dark)" stroke-width="1.8" opacity="0.3"/>
      <rect x="${x-24}" y="${y-h/2-4}" width="48" height="5" rx="2" fill="rgba(0,0,0,0.04)"/>`;
  },

  // ── STATOR ASSY — metallic ring (C02-C01: 1.5x for wider conveyor) ──
  statorAssy(x, y) {
    const r=28;
    return `<circle cx="${x}" cy="${y}" r="${r}" fill="var(--vf-obj-stator)" stroke="#1E8090" stroke-width="1.8"/>
      <circle cx="${x}" cy="${y}" r="14" fill="var(--vf-bg-canvas)" opacity="0.5"/>
      <circle cx="${x}" cy="${y}" r="8" fill="none" stroke="#1E8090" stroke-width="0.9" opacity="0.4"/>
      <circle cx="${x-15}" cy="${y-11}" r="3" fill="#1E8090" opacity="0.5"/>
      <circle cx="${x+15}" cy="${y-11}" r="3" fill="#1E8090" opacity="0.5"/>
      <circle cx="${x-15}" cy="${y+11}" r="3" fill="#1E8090" opacity="0.5"/>
      <circle cx="${x+15}" cy="${y+11}" r="3" fill="#1E8090" opacity="0.5"/>`;
  },

  // ── ROTOR — shaft (C02-C01: 1.5x for wider conveyor) ──
  rotor(x, y) {
    return `<rect x="${x-32}" y="${y-8}" width="64" height="16" rx="8" fill="var(--vf-obj-rotor)" stroke="#C88020" stroke-width="1.5"/>
      <rect x="${x-5}" y="${y-10}" width="10" height="20" rx="5" fill="#D09030"/>
      <rect x="${x-26}" y="${y-4}" width="52" height="8" rx="4" fill="#D09030" opacity="0.4"/>
      <line x1="${x-26}" y1="${y}" x2="${x+26}" y2="${y}" stroke="#C08028" stroke-width="0.9" opacity="0.4"/>`;
  },

  // ── MTR JOINED — assembled motor (C02-C01: 1.5x for wider conveyor) ──
  motorJoined(x, y) {
    return `<rect x="${x-28}" y="${y-16}" width="56" height="32" rx="10" fill="var(--vf-obj-joined)" stroke="#308A72" stroke-width="1.6"/>
      <rect x="${x-10}" y="${y-20}" width="20" height="6" rx="3" fill="#308A72" opacity="0.5"/>
      <circle cx="${x}" cy="${y}" r="7" fill="#308A72" opacity="0.5"/>
      <circle cx="${x}" cy="${y}" r="3" fill="#fff" opacity="0.3"/>
      <rect x="${x-30}" y="${y+6}" width="8" height="7" rx="2" fill="var(--vf-obj-joined)" stroke="#308A72" stroke-width="1"/>
      <rect x="${x+22}" y="${y+6}" width="8" height="7" rx="2" fill="var(--vf-obj-joined)" stroke="#308A72" stroke-width="1"/>`;
  },

  // ── MTR PRE-TEST — complete motor (C02-C01: 1.5x for wider conveyor) ──
  motorPreTest(x, y) {
    return `<rect x="${x-30}" y="${y-16}" width="60" height="32" rx="10" fill="var(--vf-obj-pretest)" stroke="#2E7098" stroke-width="1.6"/>
      <circle cx="${x}" cy="${y}" r="7" fill="#2E7098" opacity="0.4"/>
      <circle cx="${x}" cy="${y}" r="3" fill="#fff" opacity="0.2"/>
      <rect x="${x-32}" y="${y-10}" width="6" height="20" rx="3" fill="var(--vf-obj-pretest)" stroke="#2E7098" stroke-width="1"/>
      <rect x="${x+26}" y="${y-10}" width="6" height="20" rx="3" fill="var(--vf-obj-pretest)" stroke="#2E7098" stroke-width="1"/>
      <rect x="${x-26}" y="${y+8}" width="9" height="7" rx="2.5" fill="var(--vf-obj-pretest)" stroke="#2E7098" stroke-width="0.8"/>
      <rect x="${x+17}" y="${y+8}" width="9" height="7" rx="2.5" fill="var(--vf-obj-pretest)" stroke="#2E7098" stroke-width="0.8"/>`;
  },

  // ── TESTED MTR — blue T marker (C02-C01: 1.5x for wider conveyor) ──
  motorTested(x, y) {
    return `<rect x="${x-30}" y="${y-16}" width="60" height="32" rx="10" fill="var(--vf-obj-pretest)" stroke="#2E7098" stroke-width="1.6"/>
      <circle cx="${x}" cy="${y}" r="7" fill="#2E7098" opacity="0.4"/>
      <rect x="${x-32}" y="${y-10}" width="6" height="20" rx="3" fill="var(--vf-obj-pretest)" stroke="#2E7098" stroke-width="1"/>
      <rect x="${x+26}" y="${y-10}" width="6" height="20" rx="3" fill="var(--vf-obj-pretest)" stroke="#2E7098" stroke-width="1"/>
      <rect x="${x-26}" y="${y+8}" width="9" height="7" rx="2.5" fill="var(--vf-obj-pretest)" stroke="#2E7098" stroke-width="0.8"/>
      <rect x="${x+17}" y="${y+8}" width="9" height="7" rx="2.5" fill="var(--vf-obj-pretest)" stroke="#2E7098" stroke-width="0.8"/>
      <circle cx="${x+24}" cy="${y-14}" r="8" fill="none" stroke="var(--vf-accent)" stroke-width="1.5"/>
      <text x="${x+24}" y="${y-9}" fill="var(--vf-accent)" font-size="10" text-anchor="middle" font-weight="bold">T</text>`;
  },

  // ── PACKED GOODS — carton (C02-C01: 1.5x for wider conveyor) ──
  packedGoods(x, y) {
    return `<rect x="${x-30}" y="${y-18}" width="60" height="36" rx="6" fill="var(--vf-obj-packed)" stroke="#9A6838" stroke-width="1.6"/>
      <line x1="${x}" y1="${y-18}" x2="${x}" y2="${y+18}" stroke="#9A6838" stroke-width="1.2" opacity="0.35"/>
      <line x1="${x-30}" y1="${y}" x2="${x+30}" y2="${y}" stroke="#9A6838" stroke-width="1.2" opacity="0.35"/>
      <rect x="${x-16}" y="${y-19}" width="10" height="4" rx="2" fill="#9A6838" opacity="0.5"/>
      <rect x="${x+6}" y="${y-19}" width="10" height="4" rx="2" fill="#9A6838" opacity="0.5"/>`;
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

  // ── Station machine body (C01: stronger silhouette, 96×68px) ──
  stationBody(x, y, archetype, stId) {
    const cx = x, cy = y;
    let body = '';
    const bw = 96, bh = 68;

    // Base machine footprint with shadow
    body += `<rect x="${cx-bw/2+1}" y="${cy-bh/2+1}" width="${bw}" height="${bh}" rx="6" fill="rgba(0,0,0,0.05)"/>`;
    body += `<rect x="${cx-bw/2}" y="${cy-bh/2}" width="${bw}" height="${bh}" rx="6" fill="#F5F6F8" stroke="var(--vf-border)" stroke-width="1.2"/>`;

    if (archetype === 'INPUT') {
      body += `<rect x="${cx-30}" y="${cy-18}" width="60" height="36" rx="4" fill="#E9ECF2" stroke="#D0D5E0" stroke-width="1"/>`;
      body += `<circle cx="${cx-15}" cy="${cy}" r="7" fill="none" stroke="#A0AAB6" stroke-width="1.2"/>`;
      body += `<circle cx="${cx+15}" cy="${cy}" r="7" fill="none" stroke="#A0AAB6" stroke-width="1.2"/>`;
    } else if (archetype === 'JOIN') {
      body += `<rect x="${cx-36}" y="${cy-22}" width="72" height="44" rx="5" fill="#FFFDF5" stroke="#C8960E" stroke-width="1.5"/>`;
      body += `<circle cx="${cx-14}" cy="${cy}" r="8" fill="none" stroke="#C8960E" stroke-width="1.3"/>`;
      body += `<circle cx="${cx+14}" cy="${cy}" r="8" fill="none" stroke="#C8960E" stroke-width="1.3"/>`;
      body += `<line x1="${cx-6}" y1="${cy}" x2="${cx+6}" y2="${cy}" stroke="#C8960E" stroke-width="2"/>`;
      // Arrow indicators for two inputs
      body += `<line x1="${cx-28}" y1="${cy-18}" x2="${cx-18}" y2="${cy-8}" stroke="#C8960E" stroke-width="1.2" marker-end="url(#arrowJoin)"/>`;
      body += `<line x1="${cx+28}" y1="${cy-18}" x2="${cx+18}" y2="${cy-8}" stroke="#C8960E" stroke-width="1.2" marker-end="url(#arrowJoin)"/>`;
    } else if (archetype === 'TEST') {
      body += `<rect x="${cx-30}" y="${cy-16}" width="60" height="32" rx="4" fill="#EAF2FF" stroke="var(--vf-accent)" stroke-width="1.2"/>`;
      body += `<rect x="${cx+8}" y="${cy-22}" width="22" height="13" rx="3" fill="#fff" stroke="var(--vf-accent)" stroke-width="0.8"/>`;
      body += `<text x="${cx+19}" y="${cy-13}" fill="var(--vf-accent)" font-size="8" text-anchor="middle" font-weight="700">T</text>`;
      body += `<rect x="${cx-26}" y="${cy+6}" width="52" height="3" rx="1" fill="var(--vf-accent)" opacity="0.15"/>`;
    } else if (archetype === 'VISION') {
      body += `<rect x="${cx-28}" y="${cy-14}" width="56" height="28" rx="4" fill="#F0F4FF" stroke="var(--vf-accent)" stroke-width="1.2"/>`;
      body += `<circle cx="${cx-4}" cy="${cy}" r="9" fill="none" stroke="var(--vf-accent)" stroke-width="1"/>`;
      body += `<circle cx="${cx-4}" cy="${cy}" r="3" fill="var(--vf-accent)" opacity="0.6"/>`;
      body += `<rect x="${cx+10}" y="${cy-7}" width="14" height="8" rx="2" fill="#fff" stroke="var(--vf-accent)" stroke-width="0.7"/>`;
      body += `<circle cx="${cx+17}" cy="${cy-3}" r="1.5" fill="var(--vf-accent)"/>`;
    } else if (archetype === 'PACK') {
      if (stId === 'AP09') {
        body += `<rect x="${cx-30}" y="${cy-16}" width="60" height="32" rx="4" fill="#FDF8F2" stroke="#B68B57" stroke-width="1.2"/>`;
        body += `<rect x="${cx-22}" y="${cy-8}" width="44" height="16" rx="3" fill="none" stroke="#B68B57" stroke-width="0.8" stroke-dasharray="4,3"/>`;
        body += `<rect x="${cx-14}" y="${cy-10}" width="8" height="12" rx="1" fill="none" stroke="#B68B57" stroke-width="0.7"/>`;
        body += `<rect x="${cx+6}" y="${cy-10}" width="8" height="12" rx="1" fill="none" stroke="#B68B57" stroke-width="0.7"/>`;
      } else {
        body += `<rect x="${cx-30}" y="${cy-16}" width="60" height="32" rx="4" fill="#FDF8F2" stroke="#9A6838" stroke-width="1.2"/>`;
        body += `<rect x="${cx-22}" y="${cy-10}" width="44" height="20" rx="3" fill="none" stroke="#9A6838" stroke-width="0.8"/>`;
        body += `<line x1="${cx-16}" y1="${cy-10}" x2="${cx+16}" y2="${cy+10}" stroke="#9A6838" stroke-width="0.6" opacity="0.4"/>`;
        body += `<rect x="${cx-20}" y="${cy-12}" width="40" height="3" rx="1" fill="#9A6838" opacity="0.5"/>`;
        body += `<rect x="${cx-20}" y="${cy+9}" width="40" height="3" rx="1" fill="#9A6838" opacity="0.5"/>`;
      }
    } else if (archetype === 'FINAL') {
      body += `<rect x="${cx-30}" y="${cy-14}" width="60" height="28" rx="4" fill="#F0F5FF" stroke="var(--vf-accent)" stroke-width="1.2"/>`;
      body += `<polyline points="${cx-12},${cy} ${cx-4},${cy+6} ${cx+14},${cy-8}" fill="none" stroke="var(--vf-state-pass)" stroke-width="2"/>`;
      body += `<rect x="${cx-22}" y="${cy+4}" width="44" height="3" rx="1.5" fill="var(--vf-state-pass)" opacity="0.15"/>`;
    } else if (archetype === 'CHECK') {
      body += `<rect x="${cx-26}" y="${cy-12}" width="52" height="24" rx="4" fill="#F8F9FB" stroke="var(--vf-text-muted)" stroke-width="1"/>`;
      body += `<rect x="${cx-16}" y="${cy-6}" width="32" height="4" rx="2" fill="var(--vf-text-muted)" opacity="0.25"/>`;
      body += `<rect x="${cx-16}" y="${cy+2}" width="32" height="4" rx="2" fill="var(--vf-text-muted)" opacity="0.25"/>`;
    } else {
      body += `<rect x="${cx-28}" y="${cy-14}" width="56" height="28" rx="4" fill="#F4F6F8" stroke="var(--vf-border)" stroke-width="1"/>`;
    }

    return body;
  },

  // ── AP badge (larger for readability) ──
  apBadge(x, y, stId) {
    const cy = y - 46;
    return `<rect x="${x-24}" y="${cy-11}" width="48" height="22" rx="5" fill="var(--vf-bg-surface)" stroke="var(--vf-accent)" stroke-width="1.4"/>
      <text x="${x}" y="${cy+6}" fill="var(--vf-accent)" font-size="14" font-weight="700" text-anchor="middle" font-family="Consolas,monospace">${stId}</text>`;
  },

  opName(x, y, stId) {
    const cy = y - 24;
    const name = STATION_OPS[stId] || stId;
    return `<text x="${x}" y="${cy}" fill="var(--vf-text)" font-size="13" font-weight="600" text-anchor="middle">${name}</text>`;
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
    html += `<g class="vf-station-group" data-station="${stId}" style="cursor:pointer;">`;
    html += VF.stationBody(x, cy, archetype, stId);
    html += VF.conveyorRoller(x, y);
    html += VF.apBadge(x, y, stId);
    html += VF.opName(x, y, stId);
    if (isLandmark) {
      const lmName = LANDMARK_LABELS[stId];
      if (lmName) {
        const lc = archetype==='JOIN'?'#C8960E':'var(--vf-accent)';
        html += `<text x="${x}" y="${y+64}" fill="${lc}" font-size="12" font-weight="700" text-anchor="middle">${lmName}</text>`;
      }
    }
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
    document.getElementById('btn-auto').textContent = '⏹ STOP';
    document.getElementById('btn-auto').className = 'vf-btn primary';
    document.getElementById('btn-pause').disabled = false;
    this._autoTimer = setInterval(() => this.step(), Math.round(1000 / this._speed));
  },

  stopAuto() {
    if (this._autoTimer) { clearInterval(this._autoTimer); this._autoTimer = null; }
    document.getElementById('btn-auto').textContent = '▶▶ AUTO';
    document.getElementById('btn-auto').className = 'vf-btn accent-outline';
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
    if (this._liveStatus === 'LIVE') { el.textContent = '● LIVE'; el.style.color = 'var(--vf-state-pass)'; el.className = 'vf-status-item live'; }
    else if (this._liveStatus === 'STALE') { el.textContent = '○ STALE'; el.style.color = 'var(--vf-state-hold)'; el.className = 'vf-status-item'; }
    else { el.textContent = '✕ BACKEND UNAVAILABLE'; el.style.color = 'var(--vf-state-fail)'; el.className = 'vf-status-item'; }
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

    let stateCls = 'operating', stateLabel = sl.line_state.toUpperCase();
    if (isExc) { stateCls = 'hold'; stateLabel = 'QUALITY HOLD'; }
    else if (sl.line_state === 'stopped') { stateCls = 'stopped'; }
    else if (sl.line_state === 'ready_to_index') { stateCls = 'ready'; }

    // Mini process strip
    let dots = '';
    STATIONS.forEach((stId, si) => {
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

    return `<div class="${cls}" data-sl="${sl.sub_line_id}" data-variant="${sl.variant}">
      <div class="vf-sc-header">
        <span class="vf-sc-id">${sl.sub_line_id}</span>
        <span class="vf-sc-state ${stateCls}">${stateLabel}</span>
      </div>
      <div class="vf-sc-meta">${sl.variant.toUpperCase()}</div>
      <div class="vf-sc-strip">${dots}</div>
      <div class="vf-sc-stats">
        <span>WIP: <b>${sl.wips_on_line}</b></span>
        <span>OUT: <b>${sl.motors_released}</b></span>
        <span>DW: <b>${sl.dwell_number}</b></span>
        <span>t=<b>${sl.simulation_time_s.toFixed(0)}s</b></span>
      </div>
      ${isExc && sl.held_station ? `<div style="font-size:10px;color:var(--vf-state-fail);margin-top:4px;">⏸ ${sl.held_station} / ${sl.held_wip_id}</div>` : ''}
      <span class="vf-sc-detail-hint">↗ Double-click for detail</span>
    </div>`;
  },

  _bindCardClicks() {
    document.querySelectorAll('.vf-subline-card').forEach(card => {
      card.addEventListener('click', () => {
        const slId = card.getAttribute('data-sl');
        if (slId) { this._selectedSubLineId = slId; this._refreshCardStyles(); }
      });
      card.addEventListener('dblclick', () => {
        const slId = card.getAttribute('data-sl');
        if (slId) { this._selectedSubLineId = slId; openFrameB(slId); }
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
  if (ctrl._autoTimer) ctrl.stopAuto();
  document.getElementById('frame-a').style.display = 'none';
  document.getElementById('frame-b').style.display = 'flex';
  document.getElementById('frame-b').style.flexDirection = 'column';
  document.getElementById('frame-b').style.height = '100%';

  // Toggle top bar elements: show Frame B context
  document.getElementById('demo-step').style.display = 'none';
  document.getElementById('global-scenario').style.display = 'none';
  document.getElementById('fb-sim-time').style.display = '';
  document.getElementById('fb-dwell').style.display = '';
  document.getElementById('fb-sub-line-id').style.display = '';
  document.getElementById('fb-variant').style.display = '';
  document.getElementById('fb-line-state').style.display = '';
  document.getElementById('fb-scenario').style.display = '';
  document.getElementById('fb-live-status').style.display = '';

  // Toggle footer: show Frame B scenario/speed
  document.getElementById('vf-scenario-label-a').style.display = 'none';
  document.getElementById('vf-scenario-label-b').style.display = '';
  document.getElementById('speed-select').style.display = 'none';
  document.getElementById('fb-speed-select').style.display = '';
  document.getElementById('vf-zoom-group').style.display = '';
  document.getElementById('vf-zoom-label').style.display = '';

  // Update sidebar with Frame B context
  document.getElementById('vf-sidebar').querySelector('.vf-sb-section h3').textContent = 'Sub-Line Detail';

  ctrlB._initZoomPan();
  ctrlB._speed = ctrl._speed;
  ctrlB._scenario = ctrl._scenario;
  ctrlB.init(subLineId);
}

function closeFrameB() {
  if (ctrlB._autoTimer) ctrlB.stopAuto();
  document.getElementById('frame-b').style.display = 'none';
  document.getElementById('frame-a').style.display = 'flex';
  document.getElementById('frame-a').style.flexDirection = 'column';
  document.getElementById('frame-a').style.height = '100%';

  // Toggle top bar elements: show Frame A context
  document.getElementById('demo-step').style.display = '';
  document.getElementById('global-scenario').style.display = '';
  document.getElementById('fb-sim-time').style.display = 'none';
  document.getElementById('fb-dwell').style.display = 'none';
  document.getElementById('fb-sub-line-id').style.display = 'none';
  document.getElementById('fb-variant').style.display = 'none';
  document.getElementById('fb-line-state').style.display = 'none';
  document.getElementById('fb-scenario').style.display = 'none';
  document.getElementById('fb-live-status').style.display = 'none';

  // Toggle footer: show Frame A scenario/speed
  document.getElementById('vf-scenario-label-a').style.display = '';
  document.getElementById('vf-scenario-label-b').style.display = 'none';
  document.getElementById('speed-select').style.display = '';
  document.getElementById('fb-speed-select').style.display = 'none';
  document.getElementById('vf-zoom-group').style.display = 'none';
  document.getElementById('vf-zoom-label').style.display = 'none';

  document.getElementById('vf-sidebar').querySelector('.vf-sb-section h3').textContent = 'Line Overview';

  ctrl.refreshOverview().then(() => ctrl._refreshCardStyles());
}

/* ═══════════════════════════════════════
   Frame-Aware Top-Bar Control Router
   ═══════════════════════════════════════ */
function _inFrameB() {
  const fb = document.getElementById('frame-b');
  return !!fb && fb.style.display !== 'none';
}

function uiReset() {
  if (_inFrameB()) ctrlB.reset();
  else ctrl.reset();
}

function uiStep() {
  if (_inFrameB()) ctrlB.step();
  else ctrl.step();
}

function uiToggleAuto() {
  if (_inFrameB()) ctrlB.toggleAuto();
  else ctrl.toggleAuto();
}

function uiPause() {
  if (_inFrameB()) ctrlB.pause();
  else ctrl.pause();
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

      // I07-C01: AP04→AP05 is a JOIN identity boundary — new MTR child
      // appears at AP05 with a NEW wip_id; same-ID AP04→AP05 never animates.
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

      for (let i = this._plans.length - 1; i >= 0; i--) {
        const plan = this._plans[i];
        const el = document.getElementById(`wip-${plan.wip_id}`);
        if (!el) { this._plans.splice(i, 1); continue; }

        const t = Math.min(elapsed / plan.duration, 1.0);
        // easeInOutCubic
        const ease = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
        const dx = (plan.fromX - plan.toX) * (1 - ease);
        el.setAttribute('transform', `translate(${dx}, 0)`);

        if (t < 1) allDone = false;
      }

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
  _speed: 1.0,
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

  async init(subLineId) {
    this._subLineId = subLineId;
    this._selectedStation = null;
    this._selectedWipId = null;
    this._contextType = null;
    this._inspectorOpen = false;
    this._zoomLevel = 1; this._panX = 0; this._panY = 0;
    this._stepLocked = false;
    this._snapVersion = 0;
    MotionEngine.clearContext();
    this._lastSnapshot = null;  // I07: no cross-subline motion
    document.getElementById('fb-scenario-select').value = this._scenario || 'HAPPY_PATH';
    document.getElementById('fb-speed-select').value = String(this._speed);
    this._renderGridAndConveyor();
    await this.refresh();
  },

  async reset() {
    this.stopAuto();
    MotionEngine.cancel();
    this._stepLocked = false;
    this._snapVersion = 0;
    this._scenario = document.getElementById('fb-scenario-select').value;
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
    await this.call('reset', { scenario: this._scenario });
    await this.refresh();
  },

  async step() {
    // I07-C01: block STEP during active motion or in-flight step
    if (this._stepLocked || MotionEngine.isAnimating) return;
    this._stepLocked = true;
    try {
      await this.call('step');
      await this.refresh();
    } finally {
      this._stepLocked = false;
    }
  },

  back() { this.stopAuto(); closeFrameB(); },

  toggleAuto() { if (this._autoTimer) { this.stopAuto(); return; } this.startAuto(); },

  startAuto() {
    document.getElementById('btn-auto').textContent = '⏹ STOP';
    document.getElementById('btn-auto').className = 'vf-btn primary';
    document.getElementById('btn-pause').disabled = false;
    // I07: skip step if animation still running (no backlog)
    this._autoTimer = setInterval(() => {
      if (MotionEngine.isAnimating || this._stepLocked) return;
      this.step();
    }, Math.round(1000 / this._speed));
  },

  stopAuto() {
    if (this._autoTimer) { clearInterval(this._autoTimer); this._autoTimer = null; }
    document.getElementById('btn-auto').textContent = '▶▶ AUTO';
    document.getElementById('btn-auto').className = 'vf-btn accent-outline';
    document.getElementById('btn-pause').disabled = true;
  },

  pause() { if (this._autoTimer) this.stopAuto(); },

  setSpeed(val) { this._speed = parseFloat(val); if (this._autoTimer) { this.stopAuto(); this.startAuto(); } },

  setScenario(val) { this._scenario = val; ctrl._scenario = val; const selA = document.getElementById('scenario-select'); if (selA) selA.value = val; this.reset(); },

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
      this._snapVersion++;
      // I07: detect transitions, render, then animate
      const plans = MotionEngine.detect(this._lastSnapshot, snap);
      this._renderStatic(snap);
      this._renderWips(snap);
      if (plans.length > 0) {
        MotionEngine.animate(plans, () => {
          // Re-render WIPs cleanly at final positions after settle
          this._renderWips(snap);
        });
      }
      this._lastSnapshot = snap;
    } catch (_) {
      this._liveStatus = this._lastSnapshot ? 'STALE' : 'UNAVAILABLE';
      this.renderStatus();
    }
  },

  renderStatus() {
    const el = document.getElementById('fb-live-status');
    if (!el) return;
    if (this._liveStatus === 'LIVE') { el.textContent = '● LIVE'; el.style.color = 'var(--vf-state-pass)'; }
    else if (this._liveStatus === 'STALE') { el.textContent = '○ STALE'; el.style.color = 'var(--vf-state-hold)'; }
    else { el.textContent = '✕ BACKEND UNAVAILABLE'; el.style.color = 'var(--vf-state-fail)'; }
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

      <!-- UI-CTX-02: LINE-OUT / OFF-LINE ITEMS conceptual zone -->
      <rect x="${L.offLineX}" y="${L.offLineY}" width="${L.offLineW}" height="${L.offLineH}" rx="6" fill="#FAFBFD" stroke="var(--vf-text-muted)" stroke-width="1.2" stroke-dasharray="8,5" opacity="0.7"/>
      <text x="${L.offLineX+L.offLineW/2}" y="${L.offLineY+18}" fill="var(--vf-text)" font-size="12" text-anchor="middle" font-weight="600">LINE-OUT / OFF-LINE ITEMS</text>
      <text x="${L.offLineX+L.offLineW/2}" y="${L.offLineY+34}" fill="var(--vf-text-secondary)" font-size="10" text-anchor="middle">INSPECT · VERIFY · OPTIONAL REWORK · CONTEXT</text>

      <!-- LINE OUT connector (RIGHT side: main line → off-line zone) -->
      <line x1="${L.lineOutConnX}" y1="${L.conveyorY+L.conveyorH}" x2="${L.lineOutConnX}" y2="${L.offLineY}" stroke="var(--vf-state-hold)" stroke-width="1.5" stroke-dasharray="5,4" opacity="0.55"/>
      <text x="${L.lineOutConnX+8}" y="${L.conveyorY+L.conveyorH+18}" fill="var(--vf-state-hold)" font-size="11" font-weight="700">LINE OUT</text>
      <polygon points="${L.lineOutConnX-4},${L.offLineY} ${L.lineOutConnX+4},${L.offLineY} ${L.lineOutConnX},${L.offLineY+8}" fill="var(--vf-state-hold)" opacity="0.55"/>

      <!-- LINE IN connector (LEFT side: off-line zone → main line) -->
      <line x1="${L.lineInConnX}" y1="${L.offLineY}" x2="${L.lineInConnX}" y2="${L.conveyorY+L.conveyorH}" stroke="var(--vf-state-pass)" stroke-width="1.5" stroke-dasharray="5,4" opacity="0.55"/>
      <text x="${L.lineInConnX+8}" y="${L.offLineY-8}" fill="var(--vf-state-pass)" font-size="11" font-weight="700">LINE IN</text>
      <polygon points="${L.lineInConnX-4},${L.conveyorY+L.conveyorH} ${L.lineInConnX+4},${L.conveyorY+L.conveyorH} ${L.lineInConnX},${L.conveyorY+L.conveyorH-8}" fill="var(--vf-state-pass)" opacity="0.55"/>`;

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
    ch += `<rect x="${L.convStartX}" y="${L.conveyorY+10}" width="${L.convEndX-L.convStartX}" height="130" rx="8" fill="var(--vf-conveyor-body)"/>`;
    ch += `<rect x="${L.convStartX}" y="${L.conveyorY}" width="${L.convEndX-L.convStartX}" height="10" rx="4" fill="var(--vf-conveyor-frame)"/>`;
    ch += `<rect x="${L.convStartX}" y="${L.conveyorY+L.conveyorH-10}" width="${L.convEndX-L.convStartX}" height="10" rx="4" fill="var(--vf-conveyor-frame)"/>`;
    // Rollers (EXH-UI-01: adjusted for 150px conveyor)
    for (let rx = L.convStartX + 30; rx < L.convEndX; rx += 40) {
      ch += `<rect x="${rx}" y="${L.conveyorY+22}" width="16" height="106" rx="4" fill="var(--vf-conveyor-roller)" opacity="0.4"/>`;
    }
    // RSO2 branch into AP04 (light feed connector; queue rendered in context-sources)
    ch += `<line x1="${L.ap04X}" y1="${L.rso2BranchTopY}" x2="${L.ap04X}" y2="${L.conveyorY}" stroke="#C8960E" stroke-width="2" stroke-dasharray="6,3" marker-end="url(#arrowLeft)"/>`;

    convG.innerHTML = ch;

    // UI-CTX-02: render contextual source cues + off-line representative items
    this._renderContextSources();
    this._renderContextOffline();
  },

  /* ── UI-CTX-02: SSO2/RSO2 contextual source cues (static, context-only) ── */
  _renderContextSources() {
    const g = document.getElementById('fb-context-sources');
    if (!g) return;
    const L = VF_LAYOUT;
    let html = '';

    // ── SSO2 INPUT source (near ASSY INPUT / PRE-ASSY, RIGHT side) ──
    const sx = L.rawX + L.rawW / 2;   // zone center (~1810)
    html += `<g data-context="sso2" style="cursor:pointer;">`;
    html += `<text x="${sx}" y="${L.rawY+42}" fill="var(--vf-text)" font-size="11" font-weight="700" text-anchor="middle">SSO2 INPUT</text>`;
    html += `<text x="${sx}" y="${L.rawY+56}" fill="var(--vf-text-muted)" font-size="9" text-anchor="middle">STATOR + SHIELD SOURCE</text>`;
    // 3 stator icons stacked vertically, 58px spacing (r=28 → 56px diameter, no overlap)
    for (let i = 0; i < 3; i++) {
      const sy = L.rawY + 82 + i * 58;
      html += `<g transform="translate(${sx}, ${sy})" opacity="0.5">${VF.statorAssy(0, 0)}</g>`;
    }
    // light connector toward PRE-ASSY (flow RIGHT→LEFT entry)
    const sso2Bottom = L.rawY + 82 + 2 * 58;
    html += `<line x1="${sx - 30}" y1="${sso2Bottom + 22}" x2="${L.preX + 6}" y2="${L.stationY - 26}" stroke="var(--vf-text-muted)" stroke-width="1.4" stroke-dasharray="4,3" opacity="0.5" marker-end="url(#arrowLeft)"/>`;
    html += `</g>`;

    // ── RSO2 ROTOR FEED (above AP04 JOIN, vertical stack) ──
    const ax = L.ap04X;
    html += `<g data-context="rso2" style="cursor:pointer;">`;
    html += `<text x="${ax}" y="${L.rso2BranchTopY - 80}" fill="var(--vf-text)" font-size="11" font-weight="700" text-anchor="middle">RSO2 ROTOR FEED</text>`;
    html += `<text x="${ax}" y="${L.rso2BranchTopY - 68}" fill="var(--vf-text-muted)" font-size="9" text-anchor="middle">TO AP04 JOIN</text>`;
    // 3 rotor icons stacked vertically, 26px spacing (rotor height 16px, no overlap)
    for (let i = 0; i < 3; i++) {
      const ry = L.rso2BranchTopY - 54 + i * 26;
      html += `<g transform="translate(${ax}, ${ry})" opacity="0.5">${VF.rotor(0, 0)}</g>`;
    }
    html += `</g>`;

    g.innerHTML = html;
    this._bindContextClicks();
  },

  /* ── UI-CTX-02: Off-line context tray (representative items, NOT runtime WIP) ── */
  _renderContextOffline() {
    const g = document.getElementById('fb-context-offline');
    if (!g) return;
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
    });
  },

  /* ── I09-P04: Context popup for source/off-line zones ── */
  selectContext(type) {
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
    } else if (this._contextType === 'offline') {
      title.textContent = 'LINE-OUT / OFF-LINE CONTEXT';
      body.innerHTML = `
        <div class="vf-context-note">Items may leave the main line for inspection, diagnosis or verification. Rework is optional; LINE IN represents return routing.</div>
        <div class="vf-popup-row"><span class="vf-popup-k">Active off-line occupancy</span><span class="vf-popup-v">not tracked in current demo</span></div>
        <div class="vf-context-tag">Representative items shown are context-only, not live WIP</div>`;
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
    html += `<text x="${L.fgX+L.fgW/2}" y="${L.fgY+195}" fill="var(--vf-text-secondary)" font-size="11" text-anchor="middle" font-weight="600">PACKED GOODS</text>`;

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
      html += `<g id="wip-${p.wip_id}" class="vf-wip-group${isSelWip?' selected':''}" data-wip="${p.wip_id}" style="cursor:pointer;">`;
      // I09-P05: dedicated selection ring behind WIP (visible on .selected, no text blur)
      html += `<rect class="vf-wip-sel-halo" x="${sx-56}" y="${sy+119}" width="112" height="92" rx="10"/>`;
      html += VF.pallet(sx, sy + 165);
      if (tokenType === 'STATOR') html += VF.statorAssy(sx, sy + 163);
      else if (tokenType === 'JOINED') html += VF.motorJoined(sx, sy + 163);
      else if (tokenType === 'PRETEST') html += VF.motorPreTest(sx, sy + 163);
      else if (tokenType === 'TESTED') html += VF.motorTested(sx, sy + 163);
      else if (tokenType === 'PACKED') html += VF.packedGoods(sx, sy + 163);
      if (isHeld || qResult === 'FAIL' || qResult === 'NG') {
        html += VF.stateOverlay(sx, sy + 165, isHeld ? 'HOLD' : qResult);
      }
      html += `<text x="${sx}" y="${sy+181}" fill="var(--vf-text-secondary)" font-size="11" text-anchor="middle">${p.wip_id}</text>`;
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
      el.addEventListener('click', (e) => {
        if (e.target.closest('.vf-wip-group')) return;
        const stId = el.getAttribute('data-station');
        this.selectStation(stId);
      });
    });
  },

  _bindWipClicks() {
    document.querySelectorAll('#fb-wips .vf-wip-group').forEach(el => {
      el.addEventListener('click', (e) => {
        e.stopPropagation();
        const wipId = el.getAttribute('data-wip');
        if (wipId) this.selectWip(wipId);
      });
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
    this._applyHighlights();
    this._renderInspector(this._lastSnapshot);
    this.closePopup();
  },

  /* ── Popup ── */
  openPopup() { document.getElementById('vf-popup').classList.add('open'); },
  closePopup() { document.getElementById('vf-popup').classList.remove('open'); },

  _renderPopup(snap) {
    if (!this._inspectorOpen || !snap) { this.closePopup(); return; }

    const popup = document.getElementById('vf-popup');
    const title = document.getElementById('vf-popup-title');
    const body = document.getElementById('vf-popup-body');
    const tabs = document.getElementById('vf-popup-tabs');
    if (tabs) tabs.style.display = '';   // restore tabs for station/WIP inspector

    const stId = this._selectedStation;
    const wipId = this._selectedWipId;
    const posMap = {};
    for (const p of (snap.positions||[])) posMap[p.position_id] = p;
    const pos = stId ? (posMap[stId] || null) : null;

    if (pos && pos.is_occupied && pos.wip_id) {
      title.textContent = `${stId} — ${pos.wip_id}`;
      const qColor = pos.latest_quality_result === 'PASS' ? 'var(--vf-state-pass)' : pos.latest_quality_result ? 'var(--vf-state-fail)' : 'var(--vf-text-muted)';
      let html = '';
      html += `<div class="vf-popup-row"><span class="vf-popup-k">Station</span><span class="vf-popup-v">${pos.position_id} — ${pos.station_label||pos.position_id}</span></div>`;
      html += `<div class="vf-popup-row"><span class="vf-popup-k">WIP</span><span class="vf-popup-v">${pos.wip_id}</span></div>`;
      html += `<div class="vf-popup-row"><span class="vf-popup-k">Product</span><span class="vf-popup-v">${pos.wip_type||'MTR'}</span></div>`;
      if (pos.carrier_id) html += `<div class="vf-popup-row"><span class="vf-popup-k">Carrier</span><span class="vf-popup-v">${pos.carrier_id}</span></div>`;
      html += `<div class="vf-popup-row"><span class="vf-popup-k">Status</span><span class="vf-popup-v">${pos.manufacturing_status||'active'}</span></div>`;
      html += `<div class="vf-popup-row"><span class="vf-popup-k">Quality</span><span class="vf-popup-v" style="color:${qColor};font-weight:600">${pos.latest_quality_result||'clear'}${pos.attempt_number>1?' #'+pos.attempt_number:''}</span></div>`;
      if (pos.is_quality_hold) html += `<div class="vf-popup-row"><span class="vf-popup-k">Hold</span><span class="vf-popup-v" style="color:var(--vf-state-fail)">${pos.held_reason||'Active'}</span></div>`;
      // I09-P04: genealogy for MTR children
      const childGenealogy = (snap.genealogy||[]).filter(g => g.child_wip_id === pos.wip_id);
      if (childGenealogy.length) {
        const g = childGenealogy[childGenealogy.length-1];
        html += `<div class="vf-popup-sep"></div><div class="vf-popup-row"><span class="vf-popup-k">Joined</span><span class="vf-popup-v">← ${(g.parent_wip_ids||[]).join(' + ')} @ ${g.join_station||'AP04'}</span></div>`;
      }
      body.innerHTML = html;
    } else if (pos && !pos.is_occupied) {
      title.textContent = `${stId} — Empty`;
      body.innerHTML = `<div class="vf-popup-empty">No WIP at this station</div>`;
    } else if (wipId) {
      title.textContent = `WIP ${wipId}`;
      const onLine = (snap.positions||[]).some(p => p.wip_id === wipId);
      const recs = (snap.quality_records||[]).filter(qr => qr.wip_id === wipId);
      let html = `<div class="vf-popup-row"><span class="vf-popup-k">WIP</span><span class="vf-popup-v">${wipId}</span></div>`;
      // I09-P04: AP04 identity boundary — selected SSO2 consumed → child MTR
      const asParent = (snap.genealogy||[]).filter(g => (g.parent_wip_ids||[]).includes(wipId));
      if (!onLine && asParent.length) {
        const g = asParent[asParent.length-1];
        html += `<div class="vf-context-note">Consumed at ${g.join_station||'AP04'} — this identity is now the parent of a new motor.</div>`;
        html += `<div class="vf-popup-row"><span class="vf-popup-k">Child MTR</span><span class="vf-popup-v" style="cursor:pointer;color:var(--vf-accent);font-weight:600" onclick="ctrlB.selectWip('${g.child_wip_id}')">${g.child_wip_id} ↗</span></div>`;
      } else if (!onLine) {
        html += `<div class="vf-insp-historical">HISTORICAL — Exited line</div>`;
      }
      html += `<div class="vf-popup-row"><span class="vf-popup-k">Records</span><span class="vf-popup-v">${recs.length} quality records</span></div>`;
      body.innerHTML = html;
    } else {
      title.textContent = 'Inspector';
      body.innerHTML = '<div class="vf-popup-empty">Select a station or WIP</div>';
    }

    this.openPopup();
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
      : this._contextType === 'offline' ? 'LINE-OUT / OFF-LINE'
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
  _autoTimer: null, _speed: 1.0, _scenario: 'HAPPY_PATH',
  async init() { await this.call('reset', { scenario: this._scenario }); this.render(await this.call('snapshot')); },
  async reset() { this.stopAuto(); this._scenario = document.getElementById('scenario-select-s04').value; await this.call('reset', { scenario: this._scenario }); this.render(await this.call('snapshot')); },
  async step() { this.render(await this.call('step')); },
  toggleAuto() { this._autoTimer ? this.stopAuto() : this.startAuto(); },
  startAuto() { document.getElementById('btn-auto-s04').textContent = '⏹ STOP'; document.getElementById('btn-pause-s04').disabled = false; this._autoTimer = setInterval(() => this.step(), Math.round(1000 / this._speed)); },
  stopAuto() { if (this._autoTimer) { clearInterval(this._autoTimer); this._autoTimer = null; } document.getElementById('btn-auto-s04').textContent = '▶▶ AUTO'; document.getElementById('btn-pause-s04').disabled = true; },
  pause() { if (this._autoTimer) this.stopAuto(); },
  setSpeed(val) { this._speed = parseFloat(val); if (this._autoTimer) { this.stopAuto(); this.startAuto(); } },
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

  const s04b = await detectS04B();
  if (s04b) {
    document.getElementById('frame-a').style.display = 'flex';
    document.getElementById('frame-a').style.flexDirection = 'column';
    document.getElementById('frame-a').style.height = '100%';
    document.getElementById('frame-s04').style.display = 'none';
    document.getElementById('vf-scenario-label-a').style.display = '';
    document.getElementById('vf-scenario-label-b').style.display = 'none';
    document.getElementById('fb-speed-select').style.display = 'none';
    document.getElementById('vf-zoom-group').style.display = 'none';
    document.getElementById('vf-zoom-label').style.display = 'none';
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