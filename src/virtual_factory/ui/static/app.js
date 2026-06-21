/* Virtual Factory — Main Application Controller (v2) */
const KPI_SIGNALS=["LT102_LEVEL","FT101_FLOW","PT101_PRESSURE","LIC102_OUT","V101_OPENING_FEEDBACK"];
const ALARM_SIGNALS=["T102_LOW_LEVEL_ALARM","T102_HIGH_LEVEL_ALARM","P101_NO_FLOW_ALARM","V101_POSITION_DEVIATION_ALARM","LT102_BAD_QUALITY_ALARM"];
const APP={telemetry:new Map(),alarms:new Map(),pollingId:null,socket:null,zoomLevel:1};

document.addEventListener("DOMContentLoaded",()=>{
  safeOn("start-loop","click",()=>postStatus("/start"));
  safeOn("stop-loop","click",()=>postStatus("/stop"));
  safeOn("step-once","click",()=>postAndRender("/step"));
  safeOn("run-ten","click",()=>postAndRender("/run-steps?n=10"));
  safeOn("refresh","click",()=>refreshAll());
  safeOn("reset-engine","click",()=>postReset());

  // Sidebar nav
  document.querySelectorAll(".nav-item[data-tab]").forEach(item=>{item.addEventListener("click",()=>{
    document.querySelectorAll(".nav-item[data-tab]").forEach(i=>i.classList.remove("active"));
    item.classList.add("active");const t=item.dataset.tab;
    const pm={process:"pane-telemetry",telemetry:"pane-telemetry",alarms:"pane-alarms",trends:"pane-trends",table:"pane-table","settings-control":"pane-settings","settings-faults":"pane-settings","settings-opc":"pane-settings",builder:"pane-telemetry"};
    if(pm[t])switchPane(pm[t]);if(t==="builder")toggleBuilder(true);else toggleBuilder(false);
    if(t==="settings-control")showCard("pid-settings-card");
    if(t==="settings-faults")showCard("fault-settings-card");
    if(t==="settings-opc")showCard("opc-settings-card");
  })});

  // Bottom tabs
  document.querySelectorAll(".bottom-tab").forEach(t=>{t.addEventListener("click",()=>switchPane(t.dataset.pane))});

  // Inspector close
  safeOn("close-inspector","click",()=>{const b=document.getElementById("property-body");if(b)b.innerHTML='<div class="empty-state"><p>Select an equipment node<br>to inspect its properties.</p></div>';});

  // Zoom controls
  safeOn("tool-zoom-in","click",()=>zoomSVG(1.2));
  safeOn("tool-zoom-out","click",()=>zoomSVG(1/1.2));
  safeOn("tool-fit","click",()=>{APP.zoomLevel=1;const s=document.getElementById("process-svg");if(s)s.setAttribute("viewBox","0 0 900 520");});
  safeOn("tool-builder-toggle","click",()=>{document.getElementById("builder-palette")?.classList.toggle("visible");});

  initAll();refreshAll();connectSocket();
  safeOn("theme-toggle","click",()=>{document.body.classList.toggle("dark");const t=document.getElementById("theme-toggle");if(t)t.textContent=document.body.classList.contains("dark")?"☀️":"🌙"});
  setTimeout(()=>{if(typeof SETTINGS!=="undefined")SETTINGS.init();if(typeof TRENDS!=="undefined")TRENDS.init();if(typeof WIDGETS!=="undefined"){const dc=document.getElementById("data-table-container");if(dc&&!dc.children.length)DATATABLE.init(dc);}},800);
});

// ---- Helpers ----
function safeOn(id,ev,fn){const el=document.getElementById(id);if(el)el.addEventListener(ev,fn);}
function switchPane(id){document.querySelectorAll(".bottom-tab,.tab-pane").forEach(e=>e.classList.remove("active"));const p=document.getElementById(id);if(p)p.classList.add("active");const t=document.querySelector(`.bottom-tab[data-pane="${id}"]`);if(t)t.classList.add("active");}
function showCard(id){switchPane("pane-settings");setTimeout(()=>document.getElementById(id)?.scrollIntoView({behavior:"smooth"}),100);}
function toggleBuilder(on){const b=document.getElementById("tool-builder-toggle");if(on){b?.classList.add("active");document.getElementById("builder-palette")?.classList.add("visible");if(typeof BUILDER!=="undefined")BUILDER.enable();}else{b?.classList.remove("active");document.getElementById("builder-palette")?.classList.remove("visible");if(typeof BUILDER!=="undefined")BUILDER.disable();}}

function zoomSVG(factor){const svg=document.getElementById("process-svg");if(!svg)return;APP.zoomLevel*=factor;const vw=900/APP.zoomLevel,vh=520/APP.zoomLevel,cx=450,cy=260;svg.setAttribute("viewBox",`${cx-vw/2} ${cy-vh/2} ${vw} ${vh}`);}

// ---- Init ----
function initAll(){renderKpis();renderAlarms();initEditor();}

// ---- Data ----
async function refreshAll(){await Promise.all([loadStatus(),loadTelemetry(),loadAlarms()]);if(typeof EDITOR!=="undefined"&&EDITOR.loadGraph)await EDITOR.loadGraph();}
async function postAndRender(p){const f=await(await fetch(p,{method:"POST"})).json();updateTelemetry(f);await Promise.all([loadStatus(),loadAlarms()]);}
async function postReset(){stopPoll();if(APP.socket){APP.socket.close();APP.socket=null}await fetch("/reset",{method:"POST"});APP.telemetry.clear();APP.alarms.clear();APP.zoomLevel=1;renderKpis();renderAlarms();const s=document.getElementById("process-svg");if(s)s.setAttribute("viewBox","0 0 900 520");await refreshAll();connectSocket();}
async function postStatus(p){renderStatus(await(await fetch(p,{method:"POST"})).json());}
async function loadStatus(){try{renderStatus(await(await fetch("/status")).json())}catch(e){console.warn(e)}}
function renderStatus(p){setText("plant-name",p.plant_name||p.plant_id||"Unknown");setText("scenario-name",p.scenario_id||"None");setText("simulation-time",fmtSec(p.time_s));setText("runtime-state",p.running?"Running":"Stopped");}
async function loadTelemetry(){try{const f=await(await fetch("/telemetry/latest")).json();updateTelemetry(f);updateAlarms(f)}catch(e){console.warn(e)}}
async function loadAlarms(){try{updateAlarms(await(await fetch("/alarms")).json())}catch(e){console.warn(e)}}

// ---- WebSocket ----
function connectSocket(){const p=window.location.protocol==="https:"?"wss":"ws";if(APP.socket)APP.socket.close();const s=new WebSocket(`${p}://${window.location.host}/ws/telemetry`);APP.socket=s;s.addEventListener("open",()=>{setConn("Live");stopPoll()});s.addEventListener("message",(e)=>{try{const f=JSON.parse(e.data);updateTelemetry(f);updateAlarms(f);updateTime(f);if(typeof TRENDS!=="undefined")TRENDS.pushFrame(f);if(typeof DATATABLE!=="undefined")DATATABLE.push(f)}catch(ex){}});s.addEventListener("error",()=>{setConn("Polling");startPoll()});s.addEventListener("close",()=>{setConn("Polling");startPoll()})}
function startPoll(){if(!APP.pollingId)APP.pollingId=setInterval(loadTelemetry,1000)}
function stopPoll(){if(APP.pollingId){clearInterval(APP.pollingId);APP.pollingId=null}}
function setConn(v){setText("connection-state",v);const d=document.getElementById("sidebar-status-dot");if(d)d.className="status-dot"+(v==="Live"?"":" disconnected");const t=document.getElementById("sidebar-status-text");if(t)t.textContent=v==="Live"?"Connected · Live":v}

// ---- Telemetry ----
function updateTelemetry(frame){for(const s of filterPub(frame))APP.telemetry.set(s.name,s);renderKpis();updateTime(filterPub(frame));if(typeof EDITOR!=="undefined")EDITOR.updateTelemetry(frame)}
function updateAlarms(frame){for(const s of filterPub(frame).filter(s=>s.category==="industrial_event"))APP.alarms.set(s.name,s);renderAlarms();updateAlarmBadge()}
function updateTime(frame){if(!frame.length)return;setText("simulation-time",fmtSec(frame.reduce((m,s)=>Math.max(m,Number(s.timestamp_s)||0),0)))}
function filterPub(f){return Array.isArray(f)?f.filter(s=>s&&s.category!=="internal_truth"):[]}
function updateAlarmBadge(){const b=document.getElementById("alarm-count");if(!b)return;let c=0;APP.alarms.forEach(a=>{if(a.value===true)c++});if(c>0){b.textContent=c;b.style.display=""}else b.style.display="none"}

// ---- Render ----
function renderKpis(){const g=document.getElementById("kpi-grid");if(!g)return;g.replaceChildren(...KPI_SIGNALS.map(n=>signalCard(n,APP.telemetry.get(n))))}
function renderAlarms(){const g=document.getElementById("alarm-grid");if(!g)return;g.replaceChildren(...ALARM_SIGNALS.map(n=>alarmRow(n,APP.alarms.get(n))))}

function signalCard(name,signal){const c=document.createElement("article");c.className="kpi-card";const v=signal?fmtVal(signal.value):"--",u=signal?.unit||"",q=signal?.quality||"UNKNOWN",ts=signal?fmtSec(signal.timestamp_s):"--";let bg="#e2e8f0",ih="";if(name.includes("LEVEL")){bg="#dbeafe";ih='<text x="16" y="17" text-anchor="middle" fill="#2563eb" font-size="10" font-weight="700">LT</text>'}else if(name.includes("FLOW")){bg="#d1fae5";ih='<text x="16" y="17" text-anchor="middle" fill="#059669" font-size="10" font-weight="700">FT</text>'}else if(name.includes("PRESSURE")){bg="#ffedd5";ih='<text x="16" y="17" text-anchor="middle" fill="#ea580c" font-size="10" font-weight="700">PT</text>'}else if(name.includes("OUT")){bg="#ede9fe";ih='<text x="16" y="17" text-anchor="middle" fill="#7c3aed" font-size="10" font-weight="700">CO</text>'}else if(name.includes("FEEDBACK")){bg="#fce7f3";ih='<text x="16" y="17" text-anchor="middle" fill="#db2777" font-size="10" font-weight="700">FB</text>'}c.innerHTML=`<div class="kpi-card-header"><div class="kpi-card-icon" style="background:${bg}"><svg width="20" height="20" viewBox="0 0 32 32">${ih}</svg></div><span class="kpi-card-name">${name}</span></div><div class="kpi-card-value">${v}<span class="unit">${u}</span></div><div class="kpi-card-meta"><span class="quality-${q}">● ${q}</span><span>⏱ ${ts}</span></div>`;return c}

function alarmRow(name,signal){const a=Boolean(signal?.value),r=document.createElement("article");r.className=`alarm-row${a?" active":""}`;r.innerHTML=`<span class="alarm-icon"></span><div class="alarm-info"><h3>${name}</h3><span class="alarm-detail">${signal?.quality||"UNKNOWN"} · ${signal?fmtSec(signal.timestamp_s):"--"}</span></div><span class="alarm-state">${a?"ACTIVE":"CLEAR"}</span>`;return r}

function fmtVal(v){if(typeof v==="number")return v.toFixed(Math.abs(v)>=100?1:4);if(v===null||v===undefined)return"--";return String(v)}
function fmtSec(v){const n=Number(v);return Number.isFinite(n)?`${n.toFixed(1)} s`:"--"}
function setText(id,t){const e=document.getElementById(id);if(e)e.textContent=t}

// ---- Editor ----
function initEditor(){const s=document.getElementById("process-svg");if(s&&typeof EDITOR!=="undefined"){EDITOR.init(s);EDITOR.loadGraph().catch(()=>setTimeout(()=>EDITOR.loadGraph(),1500))}}
updateTelemetry=(function(orig){return function(f){orig(f);if(typeof EDITOR!=="undefined")EDITOR.updateTelemetry(f)}})(updateTelemetry);

// ---- Data Table ----
const DATATABLE=(()=>{let tbl=null,initDone=false;function init(c){if(initDone)return;if(typeof WIDGETS==="undefined")return;tbl=new WIDGETS.DataTable(c,{columns:["Time","Signal","Value","Unit","Quality","Source"]});initDone=true}function push(f){if(!tbl)return;for(const s of(Array.isArray(f)?f:[])){if(!s||!s.name)continue;tbl.addRow([fmtSec(s.timestamp_s),s.name,fmtVal(s.value),s.unit||"",s.quality||"",s.source||""])}}return{init,push}})();

// ---- Trends ----
const TRENDS=(()=>{let c=null,d=false,t=0;function i(){if(d)return;const x=document.getElementById("trend-chart-container");if(!x||typeof WIDGETS==="undefined")return;c=new WIDGETS.TrendChart(x,{width:1000,height:260});c.addSeries("LT102_LEVEL","#2563eb");c.addSeries("FT101_FLOW","#059669");c.addSeries("PT101_PRESSURE","#ea580c");c.addSeries("LIC102_OUT","#7c3aed");d=true}function p(f){if(!c)return;for(const s of(Array.isArray(f)?f:[])){if(!s)continue;if(s.name==="LT102_LEVEL")c.pushData(0,t,Number(s.value)||0);if(s.name==="FT101_FLOW")c.pushData(1,t,Number(s.value)||0);if(s.name==="PT101_PRESSURE")c.pushData(2,t,Number(s.value)||0);if(s.name==="LIC102_OUT")c.pushData(3,t,Number(s.value)||0)}t++}return{init:i,pushFrame:p}})();
