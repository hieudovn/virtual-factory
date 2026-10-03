# DDAY-B3 — 01. Baseline, change set and reuse map

**Task:** `DDAY-B3` — Bottled Water 2D Target-Line Skin
**SA authorization:** `hieudovn/virtual-factory#104` (B3 ONLY)
**PR:** `#101` — base `main`, head `sa/dday-track-b-20261003`
**Machine evidence:** [`machine-evidence.json`](./machine-evidence.json) → `git`,
`static_audit`; patch [`implementation.patch`](./implementation.patch)

## Repository truth

| Field | Value |
|---|---|
| Branch | `sa/dday-track-b-20261003` |
| SA-issued B3 baseline (Issue #104) | `f311edeeda595b3bcbc1a53dece5f9812a6435b1` — branch head at B3 start, **match** |
| `origin/main` | `f5261c8ca18cd4e01779c0274b55270ba028b4e5` — **not advanced** |
| Preflight before first B3 write | `PRECHECK PASSED`, exit 0, clean tree |

## Complete change set (vs the B3 baseline)

```
A  .ai-harness/tasks/DDAY-B3.json
M  src/virtual_factory/ui/api.py
A  src/virtual_factory/ui/static/bottled_water_demo.html
A  src/virtual_factory/ui/static/bottled_water_demo.js
A  src/virtual_factory/ui/static/bottled_water_demo.css
A  tests/test_dday_b3_bottled_water_ui.py
6 files changed, 2650 insertions(+)
```

Nothing else changed. `line_runtime.py` (the B2 runtime), the existing skin assets
(`assy_demo.js/.css/.html`, `index.html`, `app.js`), `ui/runtime_service.py`, all
`core/`/`telemetry/`/`protocols/` paths and `pyproject.toml` are **untouched**.

`demo_controller.py` was allowed by Issue #104 "only if a very small generic
read/control seam is required" — it was **not required** and is **not modified**:
every runtime call the skin needs is already public
(`line_facts()`, `run_state`, `line`, `start/pause/resume/stop/advance/reset`).

## Reuse map

| Existing VF capability | How B3 reuses it |
|---|---|
| SVG viewBox canvas + `preserveAspectRatio` | Same canvas technique; Bottled Water geometry |
| Pan / zoom / zoom-fit mechanics | Same interaction pattern (wheel zoom about the cursor, drag pan, double-click fit), reimplemented for this canvas |
| Animation-clock / polling mechanics | Presentation clock paces engine ticks; the simulation stays step-driven |
| Reduced-motion-aware motion | `prefers-reduced-motion` honoured for unit movement (same convention as the existing motion engine) |
| Selection + floating popup/inspector | Same `selection → popup` interaction pattern, read-only |
| State-highlighting conventions | Same `pass`/`idle`/`fail` semantics, exposed as data attributes |
| Runtime control wiring | START/PAUSE/RESUME/STOP/RESET delegate straight to the B2 runtime controls |
| Design tokens / visual language | Same token *conventions* (surface, border, text, accent, radius, shadow) — **not** imported from the other skin's stylesheet |
| B2 generic line facts | The skin binds to `line_facts()` through a new API projection |

**Deliberately not reused:** the other line's skin assets, its station artwork,
its icons, its layout/flow direction, its labels and its APxx vocabulary. The
Bottled Water skin is self-contained and carries its own eight machine drawings
plus a bottle token.

## Interaction defects found and fixed during browser verification

Verifying the skin in a real browser surfaced two genuine UX bugs in the new
code, both fixed rather than worked around:

1. **Pan swallowed clicks.** The pan gesture called `setPointerCapture` on
   `pointerdown`, which retargets the follow-up `mouseup`/`click` to the canvas.
   Result: machines and bottles were unclickable whenever the line was running.
   Fixed by capturing the pointer only once a real drag starts (>4 px), and by
   ignoring the click that ends a pan.
2. **Station layer rebuilt every poll.** Rebuilding the station layer on each
   state refresh replaced nodes between `pointerdown` and `click`. Fixed by
   building station nodes once per route and thereafter only updating
   attributes. Machines and bottles also gained explicit hit areas so the
   clickable region matches the drawn shape.

A third, smaller issue: the event window default (12) was smaller than one
production cycle (~20–30 events), so the skin could drop a cycle's events between
polls. The default is now 60.
