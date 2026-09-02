# 06 — Open Gaps & Next Gates

## 6.1 Open-gap handling (contract rule)

If PIM lacks a required parameter, state mapping, or canonical id that the SH
WTP model needs, VF must mark it explicitly:

```text
status: missing | unknown | review_required
```

VF **must not fabricate canonical semantics** to keep the simulation running.
The affected object/signal/dimension is either excluded from the run, or the run
fails closed per §04 (mode: required).

## 6.2 Known open gaps (as of ALIGN-01)

| Gap | Owner | Handling |
|---|---|---|
| PIM export artifacts for SH WTP are not yet defined/implemented | PIM (future export gate) | VF references are conceptual until PIM ships them; `compatibility.status = review_required` in the meantime |
| No canonical id scheme is instantiated for SH WTP yet | PIM | frozen: PIM owns it; VF never invents one (no new scheme chosen here) |
| Signal → state-dimension mapping may be partially unknown | PIM | mark `unknown`/`review_required`; do not infer |
| Known/missing model parameters (e.g. process coefficients) | PIM | mark `missing`; fidelity ceiling `logical_only` until supplied |

## 6.3 Next gates (NOT started in ALIGN-01)

1. **PIM export gate** (PIM side) — produce the pinned semantic artifacts.
2. **VF workspace loader + semantic-binding validation** (workspace gate) —
   implement fail-closed binding/mapping per §04 (contract already frozen).
3. **Dedicated CORE provenance gate** — thread workspace identity/provenance
   across shared runtime-output infrastructure (B8; NOT folded into PH01).
4. **SHW-VF-PH01** — SH WTP runtime/config only after the above dependencies.

## 6.4 Compliance

- Production code changed: NO.
- PIM export / workspace loader / binding validation / provenance threading
  implemented: NO.
- PH01 / CORE provenance gate started: NO.
- No canonical id or site-verified semantic invented here: NO.
