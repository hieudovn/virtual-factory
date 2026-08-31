# 03 — Reconciliation Strategy & Rejected Alternatives

## Selected strategy

**Normal non-force 3-way merge: `main` + `docs/m6-s01-tipa-baseline`.**

- Create branch `feature/vf-repo-lineage-01` from `origin/main` (`fda1db44`).
- `git merge origin/docs/m6-s01-tipa-baseline` (240d8db) — a normal two-parent
  merge commit, no rebase, no squash, no force-push.
- Resolve the 3 mechanical conflicts by union/superset.
- Result: merge commit `43365214144cbf623252158cbbb7ff0dc3ef59ae` with parents
  `fda1db44…` and `240d8db…`.

### Why this is the safe choice
1. **Preserves BOTH lineages verbatim** — `main`'s MES-01 `demo_assy_mes`
   package and the six-sub-line TIPA ASSY + MES v1.1 stack both remain in the
   tree (verified: `git ls-tree` shows `demo_assy_mes/` (9 files) AND the
   six-sub-line modules).
2. **Non-force** — `main` advances by a normal merge commit; no history rewrite.
3. **Single integration point** — the reconciliation is one auditable merge
   commit, exactly matching acceptance criterion A ("normal non-force
   integration").
4. **Semantics orthogonal** — the two ASSY implementations use disjoint package
   names (`demo_assy_mes/` vs `line_runtime/…`), disjoint API prefixes
   (`/demo-assy-mes` vs `/assy-demo`), and disjoint static assets
   (`demo_assy_mes.html` vs `assy_demo.*`), so they coexist without semantic
   overlap.

## Rejected alternatives

| Alternative | Why rejected |
|---|---|
| **Rebase `docs/m6-s01-tipa-baseline` onto `main`** | Rewrites the accepted lineage's history (all SA-accepted merge SHAs would change), violating "do not force-update main" spirit and losing PR #23/#24 merge provenance. |
| **Cherry-pick MES-02/MES-03 onto `main`** | Would require cherry-picking the entire six-sub-line runtime lineage (dozens of accepted commits), fragmenting provenance and risking omission; also leaves `docs/m6-s01-tipa-baseline` and `main` unreconciled. |
| **Merge `main` into `docs/m6-s01-tipa-baseline`** | Reconciles the wrong direction — canonical `main` stays behind; Issue #25 requires bringing the lineage **back to main**. |
| **Delete `demo_assy_mes` (treat six-sub-line as superseding)** | Forbidden by MES-02 non-objective ("No deletion of the single-subline demo_assy_mes runner before SA approves the migration"); would drop an accepted feature (STOP condition). |
| **Force-push `main`** | Explicitly forbidden (Issue #25 governance; AGENTS.md). |
