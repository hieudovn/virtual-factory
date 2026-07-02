/* Virtual Factory — Main Application Controller (v2) */
const KPI_SIGNALS=["LT102_LEVEL","FT101_FLOW","PT101_PRESSURE","LIC102_OUT","V101_OPENING_FEEDBACK"];
const ALARM_SIGNALS=["T102_LOW_LEVEL_ALARM","T102_HIGH_LEVEL_ALARM","P101_NO_FLOW_ALARM","V101_POSITION_DEVIATION_ALARM","LT102_BAD_QUALITY_ALARM"];
const APP={telemetry:new Map(),alarms:new Map(),pollingId:null,socket:null,zoomLevel:1,sidebarCollapsed:false};

document.addEventListener("DOMContentLoaded",()=>{
  safeOn("start-loop","click",()=>postStatus("/start"));
  safeOn("stop-loop","click",()=>postStatus("/stop"));
  safeOn("step-once","click",()=>postAndRender("/step"));
  safeOn("run-ten","click",()=>postAndRender("/run-steps?n=10"));
  safeOn("refresh","click",()=>refreshAll());
  safeOn("reset-engine","click",()=>postReset());
  safeOn("ai-generate-btn","click",()=>aiGenerate());
  safeOn("pid-parse-btn","click",()=>pidParse());
  safeOn("sidebar-toggle","click",()=>toggleSidebar());
  safeOn("nav-wtp","click",()=>{window.open("http://localhost:8100","_blank");});

  // Sidebar nav
  document.querySelectorAll(".nav-item[data-pane]").forEach(item=>{item.addEventListener("click",()=>{
    document.querySelectorAll(".nav-item[data-pane]").forEach(i=>i.classList.remove("active"));
    item.classList.add("active");const t=item.dataset.pane;
    switchRightPane(t);
    if(t==="pane-builder")toggleBuilder(true);else toggleBuilder(false);
  })});

  // Right panel tabs
  document.querySelectorAll(".right-tab").forEach(t=>{t.addEventListener("click",()=>switchRightPane(t.dataset.pane))});

  // Inspector close
  safeOn("close-inspector","click",()=>{const b=document.getElementById("property-body");if(b)b.innerHTML='<div class="empty-state"><p>Select an equipment node<br>to inspect its properties.</p></div>';});

  // Zoom controls
  safeOn("tool-zoom-in","click",()=>{if(typeof EDITOR!=="undefined")EDITOR.zoomIn()});
  safeOn("tool-zoom-out","click",()=>{if(typeof EDITOR!=="undefined")EDITOR.zoomOut()});
  safeOn("tool-fit","click",()=>{if(typeof EDITOR!=="undefined")EDITOR.fit()});
  safeOn("tool-builder-toggle","click",()=>{document.getElementById("builder-palette")?.classList.toggle("visible");});

  initAll();refreshAll();connectSocket();
  safeOn("theme-toggle","click",()=>{document.body.classList.toggle("dark");const t=document.getElementById("theme-toggle");if(t)t.textContent=document.body.classList.contains("dark")?"☀️":"🌙"});
  setTimeout(()=>{if(typeof SETTINGS!=="undefined")SETTINGS.init();if(typeof TRENDS!=="undefined")TRENDS.init();},800);
});

function toggleSidebar(){
  APP.sidebarCollapsed=!APP.sidebarCollapsed;
  document.getElementById("sidebar")?.classList.toggle("collapsed",APP.sidebarCollapsed);
  document.getElementById("main-content")?.classList.toggle("expanded",APP.sidebarCollapsed);
}

// ---- Helpers ----
function safeOn(id,ev,fn){const el=document.getElementById(id);if(el)el.addEventListener(ev,fn);}
function switchRightPane(id){
  if (id === "pane-process-flow") {
    document.querySelectorAll(".tab-pane").forEach(e => e.classList.remove("active"));
    document.querySelectorAll(".right-tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".nav-item[data-pane]").forEach(n => n.classList.toggle("active", n.dataset.pane === id));
    return;
  }
  const content=document.getElementById("monitoring-content");
  if(content){content.querySelectorAll(".tab-pane").forEach(e=>e.classList.remove("active"));const p=document.getElementById(id);if(p)p.classList.add("active")}
  document.querySelectorAll(".right-tab").forEach(t=>{t.classList.toggle("active",t.dataset.pane===id)});
  document.querySelectorAll(".nav-item[data-pane]").forEach(n=>{n.classList.toggle("active",n.dataset.pane===id)});
}
function toggleBuilder(on){const b=document.getElementById("tool-builder-toggle");if(on){b?.classList.add("active");document.getElementById("builder-palette")?.classList.add("visible");if(typeof BUILDER!=="undefined")BUILDER.enable();}else{b?.classList.remove("active");document.getElementById("builder-palette")?.classList.remove("visible");if(typeof BUILDER!=="undefined")BUILDER.disable();}}

function zoomSVG(factor){const svg=document.getElementById("process-svg");if(!svg)return;APP.zoomLevel*=factor;const vw=900/APP.zoomLevel,vh=520/APP.zoomLevel,cx=450,cy=260;svg.setAttribute("viewBox",`${cx-vw/2} ${cy-vh/2} ${vw} ${vh}`);}

// ---- Init ----
function initAll(){renderTelemetryTable();renderAlarms();initEditor();}

// ---- Data ----
async function refreshAll(){await Promise.all([loadStatus(),loadTelemetry(),loadAlarms()]);if(typeof EDITOR!=="undefined"&&EDITOR.loadGraph)await EDITOR.loadGraph();}
async function postAndRender(p){const f=await(await fetch(p,{method:"POST"})).json();updateTelemetry(f);await Promise.all([loadStatus(),loadAlarms()]);}
async function postReset(){stopPoll();if(APP.socket){APP.socket.close();APP.socket=null}await fetch("/reset",{method:"POST"});APP.telemetry.clear();APP.alarms.clear();APP.zoomLevel=1;renderTelemetryTable();renderAlarms();if(typeof EDITOR!=="undefined")EDITOR.resetView();await refreshAll();connectSocket();}
async function postStatus(p){renderStatus(await(await fetch(p,{method:"POST"})).json());}
async function loadStatus(){try{renderStatus(await(await fetch("/status")).json())}catch(e){console.warn(e)}}
function renderStatus(p){setText("plant-name",p.plant_name||p.plant_id||"Unknown");setText("simulation-time",fmtSec(p.time_s));setText("runtime-state",p.running?"▶ Running":"■ Stopped");}
async function loadTelemetry(){try{const f=await(await fetch("/telemetry/latest")).json();updateTelemetry(f);updateAlarms(f)}catch(e){console.warn(e)}}
async function loadAlarms(){try{updateAlarms(await(await fetch("/alarms")).json())}catch(e){console.warn(e)}}

// ---- WebSocket ----
function connectSocket(){const p=window.location.protocol==="https:"?"wss":"ws";if(APP.socket)APP.socket.close();const s=new WebSocket(`${p}://${window.location.host}/ws/telemetry`);APP.socket=s;s.addEventListener("open",()=>{setConn("Live");stopPoll()});s.addEventListener("message",(e)=>{try{const f=JSON.parse(e.data);updateTelemetry(f);updateAlarms(f);updateTime(f);if(typeof TRENDS!=="undefined")TRENDS.pushFrame(f)}catch(ex){}});s.addEventListener("error",()=>{setConn("Polling");startPoll()});s.addEventListener("close",()=>{setConn("Polling");startPoll()})}
function startPoll(){if(!APP.pollingId)APP.pollingId=setInterval(loadTelemetry,1000)}
function stopPoll(){if(APP.pollingId){clearInterval(APP.pollingId);APP.pollingId=null}}
function setConn(v){const d=document.getElementById("sidebar-status-dot");const connected=v==="Live"||v==="WTP Live";if(d)d.className="status-dot"+(connected?"":" disconnected");const t=document.getElementById("sidebar-status-text");if(t)t.textContent=v==="Live"?"Connected · Live":v;}

// ---- Telemetry ----
function updateTelemetry(frame){for(const s of filterPub(frame))APP.telemetry.set(s.name,s);renderTelemetryTable();updateTime(filterPub(frame));if(typeof EDITOR!=="undefined")EDITOR.updateTelemetry(frame)}
function updateAlarms(frame){for(const s of filterPub(frame).filter(s=>s.category==="industrial_event"))APP.alarms.set(s.name,s);renderAlarms();updateAlarmBadge()}
function updateTime(frame){if(!frame.length)return;setText("simulation-time",fmtSec(frame.reduce((m,s)=>Math.max(m,Number(s.timestamp_s)||0),0)))}
function filterPub(f){return Array.isArray(f)?f.filter(s=>s&&s.category!=="internal_truth"):[]}
function updateAlarmBadge(){const b=document.getElementById("alarm-count");if(!b)return;let c=0;APP.alarms.forEach(a=>{if(a.value===true)c++});if(c>0){b.textContent=c;b.style.display=""}else b.style.display="none"}

// ---- Render ----
function renderTelemetryTable(){
  const tbody=document.getElementById("telemetry-tbody");
  if(!tbody)return;
  const signals=[...APP.telemetry.values()].filter(s=>s&&s.category!=="industrial_event");
  if(!signals.length){tbody.innerHTML='<tr><td colspan="5" class="telemetry-empty">Waiting for data…</td></tr>';return}
  // Sort by category then name
  const order={measured:1,controller_output:2,actuator_feedback:3,calculated:4};
  signals.sort((a,b)=>(order[a.category]||9)-(order[b.category]||9)||(a.name||"").localeCompare(b.name||""));
  tbody.innerHTML=signals.map(s=>{
    const q=s.quality||"UNKNOWN";
    return `<tr>
      <td class="sig-name">${s.role?`<span style="display:inline-block;min-width:26px;margin-right:6px;padding:1px 4px;border-radius:3px;background:var(--bg-hover);color:var(--accent);font-size:9px;font-weight:800;text-align:center">${s.role}</span>`:""}${s.name||"--"}</td>
      <td class="sig-value">${fmtVal(s.value)}</td>
      <td style="color:var(--ink-muted);font-size:10px">${s.unit||""}</td>
      <td class="quality-${q}">● ${q}</td>
      <td style="color:var(--ink-muted);font-size:10px">${fmtSec(s.timestamp_s)}</td>
    </tr>`;
  }).join("");
}
function renderAlarms(){
  const tbody=document.getElementById("alarm-tbody");
  if(!tbody)return;
  const alarms=[];
  APP.alarms.forEach((s,name)=>{alarms.push({name,value:!!s.value,quality:s.quality||"UNKNOWN",ts:s.timestamp_s||0})});
  if(!alarms.length){tbody.innerHTML='<tr><td colspan="4" class="telemetry-empty">No alarms</td></tr>';return}
  alarms.sort((a,b)=>a.name.localeCompare(b.name));
  tbody.innerHTML=alarms.map(a=>{
    const active=a.value;
    return `<tr class="${active?'alarm-active':''}">
      <td class="sig-name">${a.name}</td>
      <td class="alarm-status ${active?'active':'clear'}">${active?'● ACTIVE':'○ CLEAR'}</td>
      <td class="quality-${a.quality}">${a.quality}</td>
      <td style="color:var(--ink-muted);font-size:10px">${fmtSec(a.ts)}</td>
    </tr>`;
  }).join("");
}

function alarmRow(name,signal){const a=Boolean(signal?.value),r=document.createElement("article");r.className=`alarm-row${a?" active":""}`;r.innerHTML=`<span class="alarm-icon"></span><div class="alarm-info"><h3>${name}</h3><span class="alarm-detail">${signal?.quality||"UNKNOWN"} · ${signal?fmtSec(signal.timestamp_s):"--"}</span></div><span class="alarm-state">${a?"ACTIVE":"CLEAR"}</span>`;return r}

function fmtVal(v){if(typeof v==="number")return v.toFixed(Math.abs(v)>=100?1:4);if(v===null||v===undefined)return"--";return String(v)}
function fmtSec(v){const n=Number(v);return Number.isFinite(n)?`${n.toFixed(1)} s`:"--"}
function setText(id,t){const e=document.getElementById(id);if(e)e.textContent=t}

// ---- Editor ----
function initEditor(){const s=document.getElementById("process-svg");if(s&&typeof EDITOR!=="undefined"){EDITOR.init(s);EDITOR.loadGraph().catch(()=>setTimeout(()=>EDITOR.loadGraph(),1500))}}
updateTelemetry=(function(orig){return function(f){orig(f);if(typeof EDITOR!=="undefined")EDITOR.updateTelemetry(f)}})(updateTelemetry);

// ---- Trends (multi-chart, max 3, selectable signals) ----
const TRENDS=(()=>{
  const MAX_TRENDS=3;
  const COLORS=["#2563eb","#059669","#ea580c","#7c3aed","#db2777","#d97706","#0891b2","#4f46e5"];
  let charts=[], timeIdx=0, initDone=false;

  function init(){
    if(initDone)return;
    const c=document.getElementById("trends-container");
    if(!c)return;
    // Add first default trend chart
    addTrend();
    // Wire Add Trend button
    const addBtn=document.getElementById("trend-add-btn");
    if(addBtn)addBtn.addEventListener("click",()=>addTrend());
    initDone=true;
  }

  function addTrend(){
    if(charts.length>=MAX_TRENDS)return;
    const container=document.getElementById("trends-container");
    const addBtn=document.getElementById("trend-add-btn");
    if(!container)return;

    const idx=charts.length;
    const card=document.createElement("div");
    card.className="trend-chart-card";
    card.id="trend-card-"+idx;

    // Build signal checkboxes from telemetry
    const signals=getAvailableSignals();
    const checkboxes=signals.map((s,i)=>{
      const checked=i===0?"checked":"";
      const color=COLORS[i%COLORS.length];
      return `<label title="${s.name}"><span class="trend-color-dot" style="background:${color}"></span><input type="checkbox" value="${s.name}" ${checked} onchange="TRENDS.updateTrend(${idx})">${s.name.replace(/_/g," ")}</label>`;
    }).join("");

    card.innerHTML=`
      <div class="trend-chart-header">
        <div class="trend-signal-select" id="trend-select-${idx}">${checkboxes}</div>
        <button class="trend-remove-btn" onclick="TRENDS.removeTrend(${idx})" title="Remove trend">✕</button>
      </div>
      <div class="trend-chart-body" id="trend-body-${idx}"></div>`;

    container.appendChild(card);

    // Create chart
    const body=document.getElementById("trend-body-"+idx);
    const ch=new WIDGETS.TrendChart(body,{width:600,height:140});
    // Add checked series
    updateTrendSeries(idx,ch);

    charts.push({el:card,chart:ch,idx:idx});
    updateAddButton();
    // Replay existing data
    replayData(ch,idx);
  }

  function removeTrend(idx){
    if(charts.length<=0)return;
    const found=charts.findIndex(c=>c.idx===idx);
    if(found<0)return;
    charts[found].el.remove();
    charts.splice(found,1);
    // Re-index remaining
    charts.forEach((c,i)=>{c.idx=i;c.el.id="trend-card-"+i});
    updateAddButton();
  }

  function updateTrend(idx){
    const found=charts.find(c=>c.idx===idx);
    if(!found)return;
    updateTrendSeries(idx,found.chart);
    replayData(found.chart,idx);
  }

  function updateTrendSeries(idx,chart){
    const sel=document.getElementById("trend-select-"+idx);
    if(!sel||!chart)return;
    // Clear and rebuild series
    chart.series=[];
    const checks=sel.querySelectorAll("input[type=checkbox]:checked");
    checks.forEach((cb,i)=>{
      chart.addSeries(cb.value,COLORS[i%COLORS.length]);
    });
  }

  function getAvailableSignals(){
    const sigs=[];
    APP.telemetry.forEach((s,name)=>{
      if(s&&s.category!=="industrial_event")sigs.push({name,value:s.value});
    });
    sigs.sort((a,b)=>a.name.localeCompare(b.name));
    return sigs;
  }

  function replayData(chart,idx){
    // Chart is new, replay existing timeIdx data from APP.telemetry
    if(!chart||!chart.series.length||timeIdx<2)return;
    // We can't replay since we don't store history. Charts will fill as data arrives.
  }

  function pushFrame(f){
    timeIdx++;
    for(const c of charts){
      if(!c.chart||!c.chart.series.length)continue;
      for(let i=0;i<c.chart.series.length;i++){
        const sn=c.chart.series[i].label;
        const sig=APP.telemetry.get(sn);
        if(sig)c.chart.pushData(i,timeIdx,Number(sig.value)||0);
      }
    }
  }

  function updateAddButton(){
    const btn=document.getElementById("trend-add-btn");
    if(btn){btn.disabled=charts.length>=MAX_TRENDS;btn.textContent=charts.length>=MAX_TRENDS?`Max ${MAX_TRENDS} Trends`:"+ Add Trend";}
  }

  return{init,addTrend,removeTrend,updateTrend,pushFrame};
})();

// ---- AI Generation ----
async function aiGenerate(){const p=document.getElementById("ai-prompt"),r=document.getElementById("ai-result");if(!p||!r)return;const t=p.value.trim();if(!t){r.textContent="Please enter a description";return}r.textContent="Generating...";try{const resp=await fetch("/api/ai/generate",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({description:t})});const d=await resp.json();r.textContent=d.yaml||d.error||"No output"}catch(e){r.textContent="Error: "+e.message}}
async function pidParse(){const p=document.getElementById("pid-input"),r=document.getElementById("pid-result");if(!p||!r)return;const t=p.value.trim();if(!t){r.textContent="Please enter P&ID shorthand";return}r.textContent="Parsing...";try{const resp=await fetch("/api/ai/parse",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({text:t})});const d=await resp.json();r.textContent=d.yaml||d.error||"No output"}catch(e){r.textContent="Error: "+e.message}}
