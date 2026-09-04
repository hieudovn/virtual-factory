/* G6 — additive ASSY integration of the shared structural hierarchy.
 *
 * Renders the canonical structural hierarchy (Workspace -> line -> sub-lines)
 * through the shared primitives. Selecting an executable sub-line scope binds
 * to the EXISTING Frame A single-click selection seam — it never issues a
 * reset/step/reconstruction call and never touches the ASSY SVG/inspector
 * rendering or variant interpretation.
 *
 * Frame A/B cards and domain rendering remain owned by assy_demo.js; this file
 * only adds structural navigation on top.
 */
(function () {
  'use strict';

  function boot() {
    const navMount = document.getElementById('vf-hierarchy-nav');
    const crumbMount = document.getElementById('vf-context-crumbs');
    const section = document.getElementById('vf-hierarchy-section');
    if (!navMount || !crumbMount || !section) return; // no mount on this page
    if (typeof window.HIERARCHY === 'undefined') return;

    fetch('/api/ui/context')
      .then(function (res) {
        if (!res.ok) throw new Error('structural context unavailable');
        return res.json();
      })
      .then(function (ctx) {
        section.style.display = '';
        window.HIERARCHY.renderBreadcrumb(crumbMount, ctx.workspace.path, {});
        window.HIERARCHY.renderNavigator(navMount, ctx, {
          onSelect: function (path, kind /*, dataset, scope */) {
            window.HIERARCHY.renderBreadcrumb(crumbMount, path, {});
            const segments = String(path || '').split('/');
            const leaf = segments[segments.length - 1] || '';
            const isSubLine = /^ASSY-SL\d+$/.test(leaf);
            if (isSubLine && kind === 'executable') {
              // Path-qualified structural selection -> existing Frame A
              // selection seam (single-click card selection). No runtime
              // reset/reconstruction is ever performed here.
              if (typeof ctrl !== 'undefined' && ctrl
                  && typeof ctrl._refreshCardStyles === 'function') {
                try {
                  ctrl._selectedSubLineId = leaf;
                  ctrl._refreshCardStyles();
                } catch (e) { /* non-fatal; selection still shown */ }
              }
            }
          }
        });
      })
      .catch(function () { /* leave the mount hidden; feature unavailable */ });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
