# 01 — PIM Handoff Verification

Verification of the authoritative PIM handoff declared in Issue #35 against the
actual PIM repository.

## 1.1 Declared handoff (Issue #35)

```text
repo:                          hieudovn/plant-intelligence-model
canonical PIM main:            ec7f1266d4a19e5201b689874a2a7a75a022fc5c
export package:                SHW-PIM-VF-EXPORT-v0.1
export version:                v0.1
source model version:          SHW-PH03-v0.1
semantic model identity SHA:   f23f3c4614f50a1a2e3805f7e887433feb934915
export artifact hash baseline: ea3361a4aca9d25927a4a76c792f3af184e1aabb
PIM requested status:          candidate_for_review
VF runtime authorization:      NOT_AUTHORIZED
```

## 1.2 Verification (machine-derived)

| Item | Expected | Actual | Result |
|---|---|---|---|
| PIM repo resolves | public repo | `git ls-remote` OK | PASS |
| Canonical main HEAD | `ec7f1266…` | `refs/heads/main = ec7f1266…` | PASS |
| `ec7f1266` exists | commit | `cat-file -t` = commit | PASS |
| `f23f3c46` exists | commit | commit "normalize SHW model version identity to SHW-PH03-v0.1" | PASS |
| `ea3361a4` exists | commit | commit "PIM→VF export manifest/contents/hashes + handoff" | PASS |
| `model.yaml` source_model_version | SHW-PH03-v0.1 | verified | PASS |
| Artifact SHA-256 (sampled 5) | HASHES table | all MATCH | PASS |

## 1.3 SHA lineage (linear, unambiguous)

```text
d241da6  dev: point vite proxy (EXPORT-01 task-start baseline)
   └─ f23f3c4  PIM: normalize SHW model version identity to SHW-PH03-v0.1
         └─ ea3361a  SHW-PIM-EXPORT-FINALIZE-01: PIM→VF export manifest/contents/hashes + handoff
               └─ 797546c  FINALIZE-01 closeout report
                     └─ da33c1e  FINALIZE-01-SHA-FIX: add explicit SHA identity pins (SA clarification)
                           └─ ec7f126  FINALIZE-01-SHA-FIX: record final_pim_main_sha  ← main HEAD
```

## 1.4 Manifest four-pin mapping

| Manifest field | SHA | Role |
|---|---|---|
| `task_start_baseline_sha` | `d241da61…` | EXPORT-01 task-start baseline |
| `semantic_model_identity_sha` | `f23f3c46…` | model identity finalized to SHW-PH03-v0.1 |
| `export_artifact_hash_baseline_sha` | `ea3361a4…` | export manifest/contents/hashes created |
| `final_pim_main_sha` | `da33c1ea…` | export-content finalization marker |

## 1.5 One noted nuance (recorded, not a blocker)

The manifest labels `final_pim_main_sha` as `da33c1ea…`, but the **actual current
PIM `main` tip is `ec7f1266…`** (the very next commit, which only records the
finalization SHA into the manifest). Issue #35's "canonical PIM main" is
`ec7f1266…` and matches `git ls-remote`. Reading convention (constraint): the
canonical main = `ec7f1266…`; the manifest `final_pim_main_sha` is a historical
"finalization commit" marker, not the current main tip.

## 1.6 Conclusion for identity/pinning

- Exact repo/ref/SHA: verified.
- Exact package/version: verified (`SHW-PIM-VF-EXPORT-v0.1`, v0.1).
- Semantic model identity SHA: verified (`f23f3c46…`).
- Export artifact hash baseline: verified (`ea3361a4…`).
- Listed artifact hashes: verified (SHA-256 MATCH).
- Ambiguity between semantic identity / hash baseline / current main: **none** —
  three distinct, real commits with clear roles; the only nuance is the
  manifest's `final_pim_main_sha` label (see §1.5), which is a reading-precision
  constraint, not an identity ambiguity.
