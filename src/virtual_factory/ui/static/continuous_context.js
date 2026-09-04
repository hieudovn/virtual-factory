/* G6 — additive continuous integration of the shared structural context.
 *
 * The continuous runtime has NO authoritative multi-level G1 hierarchy; the
 * shared primitives therefore render ONLY the truthful root-only context from
 * /api/ui/context/continuous (workspace id, no invented scopes). Existing
 * process/telemetry/alarm behavior is untouched (the existing dashboard
 * controller is not modified).
 */
(function () {
  'use strict';

  function boot() {
    const crumbMount = document.getElementById('vf-context-crumbs');
    const navMount = document.getElementById('vf-context-nav');
    const section = document.getElementById('vf-context-section');
    if (!crumbMount || !navMount || !section) return;
    if (typeof window.HIERARCHY === 'undefined') return;

    fetch('/api/ui/context/continuous')
      .then(function (res) {
        if (!res.ok) throw new Error('continuous context unavailable');
        return res.json();
      })
      .then(function (ctx) {
        section.hidden = false;
        window.HIERARCHY.renderBreadcrumb(crumbMount, ctx.selection.path, {});
        // Root-only navigator: workspace root, no nested scopes (truthful).
        window.HIERARCHY.renderNavigator(navMount, {
          workspace: ctx.workspace,
          hierarchy: ctx.hierarchy,
          selection: ctx.selection
        }, {});
      })
      .catch(function () { /* leave hidden; feature unavailable */ });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
