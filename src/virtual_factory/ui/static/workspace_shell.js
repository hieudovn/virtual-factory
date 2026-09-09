/* ===================================================================
   Virtual Factory — Workspace Shell controller (VF-vNEXT-G24)
   Multi-workspace UI switching + monitoring shell.

   Observer/controller only:
   - the workspace selector is fetched from the backend registry
     (GET /vnext/workspaces);
   - selecting a workspace loads its monitor view
     (GET /vnext/workspaces/{id}/view);
   - run controls (STEP/RESET/STOP) act on the SELECTED workspace session
     only (POST /vnext/workspaces/{id}/control);
   - the domain runtime remains the truth owner; SH-WTP assumed/fidelity
     markers are displayed, never presented as site truth.
   =================================================================== */
(function () {
  'use strict';

  const $ = (id) => document.getElementById(id);
  const selectEl = $('ws-workspace-select');
  const runbarTarget = $('ws-runbar-target');
  const runbarMsg = $('ws-runbar-msg');
  const viewBox = $('ws-view');
  const emptyBox = $('ws-empty');

  let workspaces = [];      // registry metadata
  let currentView = null;   // last monitor payload

  function setMsg(text) {
    runbarMsg.textContent = text || '';
  }

  function esc(value) {
    if (value === null || value === undefined) return '';
    return String(value).replace(/[&<>"']/g, (c) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[c]));
  }

  function badgeFor(text) {
    const t = String(text || '');
    const low = t.toLowerCase();
    if (low === 'accepted' || low === 'running' || low === 'completed' || low === 'first_order') {
      return '<span class="badge badge-ok">' + esc(t) + '</span>';
    }
    if (low === 'scenario_assumed' || low === 'assumed' || low === 'logical_only' ||
        low === 'created' || low === 'paused') {
      return '<span class="badge badge-info">' + esc(t) + '</span>';
    }
    if (low.indexOf('fail') !== -1 || low.indexOf('error') !== -1) {
      return '<span class="badge badge-danger">' + esc(t) + '</span>';
    }
    if (low.indexOf('assum') !== -1) {
      return '<span class="badge badge-warn">' + esc(t) + '</span>';
    }
    return '<span class="badge">' + esc(t) + '</span>';
  }

  function kvRow(key, value, monospace) {
    const cls = monospace ? ' class="v"' : ' class="v"';
    return '<span class="k">' + esc(key) + '</span><span' + cls + '>' + esc(value) + '</span>';
  }

  /* ── registry: workspace selector source ─────────────────────── */

  function loadWorkspaces() {
    return fetch('/vnext/workspaces')
      .then(function (res) {
        if (!res.ok) { throw new Error('failed to load workspaces'); }
        return res.json();
      })
      .then(function (meta) {
        workspaces = (meta && meta.workspaces) || [];
        selectEl.innerHTML = '';
        workspaces.forEach(function (info) {
          const opt = document.createElement('option');
          opt.value = info.workspace_id;
          opt.textContent = info.workspace_id + (info.description ? ' — ' + info.description : '');
          selectEl.appendChild(opt);
        });
        // Deterministic default: keep the current selection if still valid.
        const cur = selectEl.value;
        if (!cur && workspaces.length) {
          selectEl.value = workspaces[0].workspace_id;
          select(selectEl.value);
        }
      })
      .catch(function (err) {
        setMsg('Registry error: ' + err.message);
      });
  }

  /* ── monitor view ────────────────────────────────────────────── */

  function fetchView(workspaceId) {
    return fetch('/vnext/workspaces/' + encodeURIComponent(workspaceId) + '/view')
      .then(function (res) {
        if (!res.ok) { return res.json().then(function (j) { throw new Error(j.detail || 'view failed'); }); }
        return res.json();
      })
      .then(function (payload) {
        currentView = payload;
        renderView(payload);
      })
      .catch(function (err) {
        setMsg(err.message);
        viewBox.hidden = true;
        emptyBox.hidden = false;
        emptyBox.textContent = 'View error: ' + err.message;
      });
  }

  function renderView(view) {
    viewBox.hidden = false;
    emptyBox.hidden = true;
    setMsg('');

    // identity
    const ident = view.identity || {};
    $('ws-identity').innerHTML =
      kvRow('workspace_id', ident.workspace_id, true) +
      kvRow('run_id', ident.run_id, true) +
      kvRow('scenario_id', ident.scenario_id, true) +
      kvRow('description', view.description || '');

    const uiPage = view.ui_page;
    $('ws-ui-page').innerHTML = uiPage
      ? '<a href="' + esc(uiPage) + '" target="_blank" rel="noopener">' +
        'Open existing ASSY demo UI (reuse) →</a>'
      : (view.ui_note ? '<span class="badge badge-info">' + esc(view.ui_note) + '</span>' : '');

    // session
    const sess = view.session || {};
    $('ws-session').innerHTML =
      kvRow('state', sess.state, true) +
      kvRow('run_id', sess.run_id, true) +
      kvRow('scenario_id', sess.scenario_id, true) +
      kvRow('step_count', sess.step_count == null ? '—' : sess.step_count, true) +
      kvRow('last_time_s', sess.last_time_s == null ? '—' : sess.last_time_s, true);

    // simulation
    const sim = view.simulation || {};
    $('ws-sim').innerHTML =
      kvRow('time_s', sim.time_s == null ? '—' : sim.time_s, true) +
      kvRow('step', sim.step == null ? '—' : sim.step, true) +
      kvRow('state', sim.state || '—', true);

    // structure
    const structure = view.structure || [];
    $('ws-structure').innerHTML = structureTable(structure);

    // truth note (SH-WTP must never present assumed topology as site truth)
    $('ws-truth-note').textContent = '';
    if (view.ui_note) {
      $('ws-truth-note').textContent = view.ui_note;
    } else if (view.site_truth === false) {
      $('ws-truth-note').textContent = 'Read-only monitor view — not authoritative site data.';
    }

    // values
    $('ws-values').innerHTML = valuesTable(view.values || [], view.workspace_id);

    // trace
    const trace = (view.trace || []).map(function (step) {
      return JSON.stringify(step);
    }).join('\n');
    $('ws-trace').textContent = trace || '(no steps yet)';

    // runbar enablement by state
    const st = String((sess.state || '').toLowerCase());
    $('ws-ctrl-step').disabled = !(st === 'running' || st === 'created');
    $('ws-ctrl-reset').disabled = (st === 'stopped' || st === 'failed');
    $('ws-ctrl-stop').disabled = !(st === 'created' || st === 'running' || st === 'paused');
  }

  function structureTable(structure) {
    if (!structure.length) return '<span class="badge badge-info">no structure</span>';
    const header = '<tr><th>scope</th><th>kind / role</th><th>fidelity</th><th>status</th><th>details</th></tr>';
    const body = structure.map(function (row) {
      const details = [];
      if (row.canonical_id) details.push('canonical: <code>' + esc(row.canonical_id) + '</code>');
      if (row.inbound_link_assumed) details.push('inbound link ASSUMED');
      if (row.time_s != null) details.push('t=' + esc(row.time_s));
      return '<tr>' +
        '<td><code>' + esc(row.vf_path || row.scope || '') + '</code></td>' +
        '<td>' + esc(row.kind || row.role || '') + '</td>' +
        '<td>' + badgeFor(row.fidelity) + '</td>' +
        '<td>' + badgeFor(row.status) + '</td>' +
        '<td>' + details.join(' · ') + '</td>' +
        '</tr>';
    }).join('');
    return '<table class="ws-table"><thead>' + header + '</thead><tbody>' + body + '</tbody></table>';
  }

  function valuesTable(values, workspaceId) {
    if (!values.length) return '<span class="badge badge-info">no values yet</span>';
    const header = '<tr><th>scope</th><th>key</th><th>value</th></tr>';
    const rows = [];
    values.forEach(function (row) {
      const scope = row.scope || row.vf_path || '';
      if (row.role && row.fidelity) {
        // shwtp structure row: show fidelity/status as status values
        rows.push('<tr><td><code>' + esc(scope) + '</code></td>' +
          '<td>fidelity</td><td>' + badgeFor(row.fidelity) + '</td></tr>');
        rows.push('<tr><td><code>' + esc(scope) + '</code></td>' +
          '<td>status</td><td>' + badgeFor(row.status) + '</td></tr>');
        const vals = row.current_values || {};
        Object.keys(vals).forEach(function (k) {
          rows.push('<tr><td><code>' + esc(scope) + '</code></td><td>' + esc(k) + '</td>' +
            '<td>' + esc(vals[k]) + '</td></tr>');
        });
      } else {
        rows.push('<tr><td><code>' + esc(scope) + '</code></td><td>' + esc(row.key) + '</td>' +
          '<td>' + esc(row.value) + '</td></tr>');
      }
    });
    return '<table class="ws-table"><thead>' + header + '</thead><tbody>' + rows.join('') + '</tbody></table>';
  }

  /* ── selection ───────────────────────────────────────────────── */

  function select(workspaceId) {
    if (!workspaceId) return;
    runbarTarget.textContent = workspaceId;
    $('ws-ctrl-step').disabled = true;
    $('ws-ctrl-reset').disabled = true;
    $('ws-ctrl-stop').disabled = true;
    fetch('/vnext/workspaces/select', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ workspace_id: workspaceId }),
    })
      .then(function (res) {
        if (!res.ok) { return res.json().then(function (j) { throw new Error(j.detail || 'select failed'); }); }
        return res.json();
      })
      .then(function (payload) {
        currentView = payload;
        renderView(payload);
      })
      .catch(function (err) {
        setMsg(err.message);
      });
  }

  /* ── run control (selected workspace only) ───────────────────── */

  function control(action) {
    const workspaceId = selectEl.value;
    if (!workspaceId) return;
    setMsg(action + ' → ' + workspaceId + ' …');
    fetch('/vnext/workspaces/' + encodeURIComponent(workspaceId) + '/control', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: action }),
    })
      .then(function (res) {
        if (!res.ok) { return res.json().then(function (j) { throw new Error(j.detail || 'control failed'); }); }
        return res.json();
      })
      .then(function (payload) {
        currentView = payload;
        renderView(payload);
      })
      .catch(function (err) {
        setMsg(err.message);
      });
  }

  /* ── wiring ──────────────────────────────────────────────────── */

  selectEl.addEventListener('change', function () { select(selectEl.value); });
  $('ws-refresh').addEventListener('click', function () {
    if (selectEl.value) { fetchView(selectEl.value); } else { loadWorkspaces(); }
  });
  $('ws-ctrl-step').addEventListener('click', function () { control('step'); });
  $('ws-ctrl-reset').addEventListener('click', function () { control('reset'); });
  $('ws-ctrl-stop').addEventListener('click', function () { control('stop'); });

  function boot() {
    loadWorkspaces();
    // light poll so a running session's monitor refreshes (observer only).
    setInterval(function () {
      if (selectEl.value) { fetchView(selectEl.value); }
    }, 3000);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
