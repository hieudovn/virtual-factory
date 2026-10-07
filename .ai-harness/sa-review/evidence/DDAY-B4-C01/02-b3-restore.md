# DDAY-B4-C01 — 02. Accepted B3 evidence restore

**Defect (SA-verified on PR #101):** B4 mutated two accepted B3 evidence files:

- `.ai-harness/sa-review/evidence/DDAY-B3/generate_evidence.py`
- `.ai-harness/sa-review/evidence/DDAY-B3/smoke_bottled_water_ui.py`

Issue #105 authorized B4 evidence under `evidence/DDAY-B4/`, not mutation of
closed B3 evidence.

## Restore

Both files were checked out from the accepted B3 head
`23b6208266751a8c508b0d96fd7a736dffc5676c`.

| File | blob at 23b6208 | blob at C01 HEAD |
|---|---|---|
| `generate_evidence.py` | `e3c7de398b7a755d9b5e5deb51be7dbbc1b4ed94` | `e3c7de398b7a755d9b5e5deb51be7dbbc1b4ed94` |
| `smoke_bottled_water_ui.py` | `69ce6c62f238bf6faf4d08288f91d7bba61d37b2` | `69ce6c62f238bf6faf4d08288f91d7bba61d37b2` |

`git diff 23b6208 -- <the two files>` is empty.

Test `test_c01_accepted_b3_evidence_files_match_b3_baseline` asserts the same
equality against HEAD and the worktree.

## B4-owned compatibility

The B3 smoke starts `create_app()` without `factory_autorun=False`. After B4
the default server clock races the `/advance` seam that the B3 contract uses.

That compatibility logic now lives only at:

`.ai-harness/sa-review/evidence/DDAY-B4/smoke_bottled_water_ui.py`

It is a B4-owned copy, not an edit of the restored B3 file. Live result:
`SMOKE-BW-UI` exit 0 (45 claims).
