/* G6-C01 — additive ASSY integration of the shared structural hierarchy,
 * bound to the existing authoritative ASSY selection seam.
 *
 * Rendering: the shared primitives show the canonical structural hierarchy
 * (Workspace -> line -> executable sub-lines).
 *
 * Selection semantics (Issue #51 C01):
 *  - An executable sub-line (ASSY-SLxx) hierarchy selection is forwarded to the
 *    EXISTING backend authority  POST /assy-demo/select  with
 *    { sub_line_id: <leaf> }. That surface only sets the controller's selected
 *    context (used by step/command/detail) — it never resets/reconstructs or
 *    steps the runtime, and no new endpoint / G7 orchestration is introduced.
 *  - The structural breadcrumb and the existing presentation card selection are
 *    updated ONLY AFTER the backend accepts the selection (fail-safe): on a
 *    failed request the UI never claims a selected sub-line the backend does
 *    not hold.
 *  - Workspace / container selection is structural-context-only and never calls
 *    /assy-demo/select (container-only implies no execution).
 *
 * Frame A/B cards and domain rendering remain owned by assy_demo.js; this file
 * only adds structural navigation on top.
 */
(function () {
  'use strict';

  // ── VF-vNEXT-UX01: Structure / Model drawer ───────────────
  // The drawer is a PRESENTATION surface: opening/closing it and selecting a
  // sub-line issue no step/reset/scenario call and create no session,
  // federation or runtime. Selecting a sub-line reuses the existing
  // authoritative /assy-demo/select seam (below), which only sets the
  // monitoring/context selection (same run id, no time advance).
  function wireDrawer() {
    const drawer = document.getElementById('vf-structure-drawer');
    const trigger = document.getElementById('vf-structure-btn');
    const closeBtn = document.getElementById('vf-structure-close');
    if (!drawer || !trigger) return; // no drawer on this page

    function setOpen(open) {
      const isOpen = !!open;
      drawer.classList.toggle('open', isOpen);
      drawer.setAttribute('aria-hidden', isOpen ? 'false' : 'true');
      trigger.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    }

    // Inline top-bar convention on this page: globals called from onclick.
    window.uiToggleStructure = function () {
      setOpen(!drawer.classList.contains('open'));
    };
    window.uiCloseStructure = function () { setOpen(false); };
    if (closeBtn) {
      closeBtn.addEventListener('click', function () { setOpen(false); });
    }
    document.addEventListener('keydown', function (ev) {
      if (ev.key === 'Escape') setOpen(false);
    });
    setOpen(false); // closed by default: nothing structural is pinned on screen
  }

  function boot() {
    wireDrawer();

    const navMount = document.getElementById('vf-hierarchy-nav');
    const crumbMount = document.getElementById('vf-context-crumbs');
    const section = document.getElementById('vf-hierarchy-section');
    if (!navMount || !crumbMount || !section) return; // no mount on this page
    if (typeof window.HIERARCHY === 'undefined') return;

    // Workspace / container selection: structural context only (no runtime
    // selection call, no executability implied).
    function selectStructuralOnly(path) {
      window.HIERARCHY.renderBreadcrumb(crumbMount, path, {});
    }

    // Executable sub-line selection: bind to the existing authoritative
    // /assy-demo/select seam. Fail-safe: never commit a UI selection that the
    // backend did not accept.
    function selectAssySubLine(path, leaf) {
      fetch('/assy-demo/select', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sub_line_id: leaf })
      }).then(function (res) {
        if (!res.ok) {
          throw new Error('assy select rejected: ' + leaf);
        }
        return res.json();
      }).then(function () {
        // Backend accepted -> now update breadcrumb + existing presentation
        // card selection (no reset/reconstruct/step was issued).
        window.HIERARCHY.renderBreadcrumb(crumbMount, path, {});
        if (typeof ctrl !== 'undefined' && ctrl
            && typeof ctrl._refreshCardStyles === 'function') {
          try {
            ctrl._selectedSubLineId = leaf;
            ctrl._refreshCardStyles();
          } catch (e) { /* non-fatal; breadcrumb already reflects selection */ }
        }
      }).catch(function () {
        // Fail safe: keep the previous breadcrumb/card state; do not claim a
        // selection the backend authority did not accept.
      });
    }

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
            const segments = String(path || '').split('/');
            const leaf = segments[segments.length - 1] || '';
            const isExecutableSubLine =
              kind === 'executable' && /^ASSY-SL\d+$/.test(leaf);
            if (isExecutableSubLine) {
              selectAssySubLine(path, leaf);
            } else {
              // workspace / container / non-selectable executable scope.
              selectStructuralOnly(path);
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
