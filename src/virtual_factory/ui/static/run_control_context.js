/* G7 — additive run-control context binding (read-only display + minimal
 * controls over the vNext run seam). Does NOT repoint legacy /step /start
 * /stop /reset or /assy-demo/* controls; it only drives the additive
 * /vnext/runs/* seam. Hidden when no active run exists. Container/workspace
 * targets are shown as orchestration targets, never as executable.
 */
(function () {
  'use strict';

  function boot() {
    const section = document.getElementById('vf-run-control-section');
    if (!section) return;

    const workspace = (section.getAttribute('data-vf-workspace') || 'TIPA');
    const wsParam = '?workspace=' + encodeURIComponent(workspace);

    const pathEl = document.getElementById('vf-run-control-path');
    const kindEl = document.getElementById('vf-run-control-kind');
    const stateEl = document.getElementById('vf-run-control-state');
    const timeEl = document.getElementById('vf-run-control-time');
    const effEl = document.getElementById('vf-run-control-eff');
    const btnRun = document.getElementById('vf-run-control-run');
    const btnPause = document.getElementById('vf-run-control-pause');
    const btnResume = document.getElementById('vf-run-control-resume');
    const btnStep = document.getElementById('vf-run-control-step');
    const btnStop = document.getElementById('vf-run-control-stop');
    const btnReset = document.getElementById('vf-run-control-reset');

    let runId = null;

    function post(op) {
      if (!runId) return;
      fetch('/vnext/runs/' + encodeURIComponent(runId) + '/' + op + wsParam, { method: 'POST' })
        .then(refresh)
        .catch(function () { /* keep previous state */ });
    }

    function render(rec) {
      section.hidden = false;
      runId = rec.run_id;
      pathEl.textContent = rec.target_path || '';
      pathEl.dataset.targetKind = rec.target_kind || '';
      kindEl.textContent = rec.target_kind || '';
      stateEl.textContent = rec.state || '';
      timeEl.textContent = (rec.last_time_s == null) ? '\u2014' : (rec.last_time_s + ' s');
      effEl.textContent = (rec.effective_scopes || []).join(', ');
      // capability-driven availability (no fake readiness)
      btnRun.disabled = rec.state !== 'created';
      btnPause.disabled = rec.state !== 'running';
      btnResume.disabled = rec.state !== 'paused';
      btnStep.disabled = rec.state !== 'running';
      btnStop.disabled = !(rec.state === 'created' || rec.state === 'running' || rec.state === 'paused');
      btnReset.disabled = (rec.state === 'stopped' || rec.state === 'failed');
    }

    function refresh() {
      fetch('/vnext/runs/current' + wsParam)
        .then(function (res) {
          if (!res.ok) { section.hidden = true; return null; }
          return res.json();
        })
        .then(function (rec) { if (rec) render(rec); })
        .catch(function () { section.hidden = true; });
    }

    btnRun.addEventListener('click', function () { post('start'); });
    btnPause.addEventListener('click', function () { post('pause'); });
    btnResume.addEventListener('click', function () { post('resume'); });
    btnStep.addEventListener('click', function () { post('step'); });
    btnStop.addEventListener('click', function () { post('stop'); });
    btnReset.addEventListener('click', function () { post('reset'); });

    refresh();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
