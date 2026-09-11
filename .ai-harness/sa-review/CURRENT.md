# SA REVIEW INBOX

Task: VF-vNEXT-R2
Status: BLOCKED FOR SA (scope/regression-boundary decision required before coding)
Parent: TIPA ASSY recovery sequence R1..R4 (R0 / Issue #78 CLOSED - architecture frozen)
Prerequisite: R1-C01 accepted head 4f86632; Issue #80 (R2) is the only authorized gate

Blocker (summary):
R2 requires /assy-demo to stop using _get_assy_controller()/legacy DemoController
and to defer every legacy capability that cannot be bound to the canonical
session. But the accepted OPS-03/OPS-04 product-path suites drive their semantics
through exactly those legacy endpoints (7 test files, 26 /assy-demo HTTP calls,
~170 tests; test_ops03_interaction.py + test_ops04_c01.py), and
test_demo_overview.py fixes the VF_ENABLE_S04B_OVERVIEW route-registration
contract. Keeping the required canonical-only /assy-demo therefore either keeps a
forbidden legacy authority reachable or requires retiring/migrating ~170 accepted
product-path tests - a governance decision outside the R2 declared change zones.

Binding itself is proven feasible (build_snapshot() accepts a bare
AssyLineRuntime; WorkspaceMonitor already holds the ONE live session; R1 provides
positions[]/genealogy/quality/profile + hold-release).
No product code was modified; no baseline run was required.

Base: technical base (branch point) = 4f866323fc73a1f73f6d513d5c91220d14a997b3
Branch: feature/vf-vnext-r2 (local, not pushed) | contract commit cb8c000
Harness preflight for R2: PRECHECK PASSED

Report:
.ai-harness/sa-review/reports/VF-vNEXT-R2.md

Next gate started: NO (R3 NOT started)
