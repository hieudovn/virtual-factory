/* G6 — shared hierarchical UI primitives (plain JS, no framework).

 * Domain-agnostic: no plant/workspace/line/variant/depth assumptions are made.
 * The tree is a generic, read-only structural hierarchy of scopes:
 *   node = { scope_id, path, mode, container_only, executable_capable,
 *            archetype, display_name, objects: [...], children: [node...] }
 *
 * Rules (Issue #51):
 *   - ordering follows the JSON/G1 hierarchy order (already deterministic);
 *   - selection is PATH-QUALIFIED (canonical path string);
 *   - container vs executable is rendered from the G1 capability booleans;
 *   - container selection is allowed for context but never implies execution;
 *   - no runtime state mutation; no fabricated identity.
 */
(function (global) {
  'use strict';

  function h(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = String(text);
    return node;
  }

  function collectScopes(roots, out) {
    (roots || []).forEach(function (s) {
      out.push(s);
      collectScopes(s.children, out);
    });
    return out;
  }

  const HIERARCHY = {};

  /** Render a breadcrumb from a canonical structural path string. */
  HIERARCHY.renderBreadcrumb = function (mount, pathString, opts) {
    opts = opts || {};
    mount.textContent = '';
    const segments = String(pathString || '').split('/').filter(Boolean);
    const ol = h('ol', 'vf-hierarchy-crumbs');
    segments.forEach(function (seg, i) {
      const li = h('li', 'vf-hierarchy-crumb');
      const fullPath = segments.slice(0, i + 1).join('/');
      if (i === segments.length - 1) {
        li.appendChild(h('span', 'vf-hierarchy-crumb-current', seg));
      } else {
        const btn = h('button', 'vf-hierarchy-crumb-btn', seg);
        btn.type = 'button';
        btn.dataset.path = fullPath;
        btn.addEventListener('click', function () {
          if (typeof opts.onSelect === 'function') opts.onSelect(fullPath, 'scope');
        });
        li.appendChild(btn);
      }
      ol.appendChild(li);
    });
    mount.appendChild(ol);
  };

  function scopeRowNode(scope, selectedPath, opts) {
    const liEl = h('li', 'vf-hierarchy-node');
    const isContainer = scope.container_only === true;
    const isExecutable = scope.executable_capable === true;
    const kind = isContainer ? 'container' : (isExecutable ? 'executable' : 'scope');
    liEl.classList.add('vf-hierarchy-node-' + kind);
    if (scope.path === selectedPath) liEl.classList.add('vf-hierarchy-selected');

    const row = h('div', 'vf-hierarchy-row');
    const hasChildren = Array.isArray(scope.children) && scope.children.length > 0;
    if (hasChildren) {
      const caret = h('button', 'vf-hierarchy-caret', '▾');
      caret.type = 'button';
      caret.title = 'Expand / collapse';
      caret.addEventListener('click', function (ev) {
        ev.stopPropagation();
        liEl.classList.toggle('vf-hierarchy-collapsed');
      });
      row.appendChild(caret);
    } else {
      row.appendChild(h('span', 'vf-hierarchy-caret-spacer', ''));
    }

    const label = h('button', 'vf-hierarchy-label', scope.display_name || scope.scope_id);
    label.type = 'button';
    label.dataset.path = scope.path;         // canonical path-qualified selection
    label.dataset.scopeId = scope.scope_id;  // display label only
    label.dataset.kind = kind;
    if (isContainer) label.dataset.containerOnly = 'true';
    if (isExecutable) label.dataset.executableCapable = 'true';
    label.addEventListener('click', function () {
      if (typeof opts.onSelect === 'function') opts.onSelect(scope.path, kind, label.dataset, scope);
    });
    row.appendChild(label);
    row.appendChild(h('span', 'vf-hierarchy-badge', isContainer ? 'container' : (isExecutable ? 'executable' : 'scope')));
    liEl.appendChild(row);

    if (hasChildren) {
      const childUl = h('ul', 'vf-hierarchy-children');
      scope.children.forEach(function (child) {
        childUl.appendChild(scopeRowNode(child, selectedPath, opts));
      });
      liEl.appendChild(childUl);
    }
    return liEl;
  }

  /** Render a nested hierarchy navigator (workspace root + recursive scopes).
   *  Accepts either workspace_to_dict JSON or structural context JSON.
   */
  HIERARCHY.renderNavigator = function (mount, data, opts) {
    opts = opts || {};
    mount.textContent = '';
    const workspace = (data && data.workspace) ? data.workspace : (data || {});
    const roots = (data && data.hierarchy) ? data.hierarchy
      : ((data && data.scopes) ? data.scopes : []);
    const selectedPath = (data && data.selection && data.selection.path) || null;

    const ul = h('ul', 'vf-hierarchy-tree');

    const rootLi = h('li', 'vf-hierarchy-node vf-hierarchy-node-workspace');
    if ((workspace.path || workspace.workspace_id || '') === selectedPath) {
      rootLi.classList.add('vf-hierarchy-selected');
    }
    const rootRow = h('div', 'vf-hierarchy-row');
    if (roots.length > 0) {
      const caret = h('button', 'vf-hierarchy-caret', '▾');
      caret.type = 'button';
      caret.title = 'Expand / collapse';
      caret.addEventListener('click', function (ev) {
        ev.stopPropagation();
        rootLi.classList.toggle('vf-hierarchy-collapsed');
      });
      rootRow.appendChild(caret);
    } else {
      rootRow.appendChild(h('span', 'vf-hierarchy-caret-spacer', ''));
    }
    const rootLabel = h('button', 'vf-hierarchy-label', workspace.display_name || workspace.workspace_id || workspace.path);
    rootLabel.type = 'button';
    rootLabel.dataset.path = workspace.path || workspace.workspace_id || '';
    rootLabel.dataset.kind = 'workspace';
    rootLabel.addEventListener('click', function () {
      if (typeof opts.onSelect === 'function') {
        opts.onSelect(rootLabel.dataset.path, 'workspace', rootLabel.dataset, null);
      }
    });
    rootRow.appendChild(rootLabel);
    rootRow.appendChild(h('span', 'vf-hierarchy-badge', 'workspace'));
    rootLi.appendChild(rootRow);

    if (roots.length > 0) {
      const childUl = h('ul', 'vf-hierarchy-children');
      roots.forEach(function (scope) {
        childUl.appendChild(scopeRowNode(scope, selectedPath, opts));
      });
      rootLi.appendChild(childUl);
    }
    ul.appendChild(rootLi);
    mount.appendChild(ul);
  };

  /** Flat, path-qualified list of executable scope paths in a hierarchy. */
  HIERARCHY.executableScopePaths = function (data) {
    const roots = (data && data.hierarchy) ? data.hierarchy
      : ((data && data.scopes) ? data.scopes : []);
    const all = [];
    collectScopes(roots, all);
    return all
      .filter(function (s) { return s.executable_capable === true; })
      .map(function (s) { return s.path; });
  };

  global.HIERARCHY = HIERARCHY;
})(window);
