# VF Strategic Memory Seed v1 — Source-linked, non-authoritative index
**Status:** PROPOSED SEED / PAGA-02 DESIGN DRAFT, not approved decisions. **Date:** 2026-11-08.
**Purpose:** Project-wide long-horizon context index for cold-session recovery without manual handoff. Every assertion must be revalidated against its primary source at session time. This index is NEVER higher authority than effective Constitution, ADR, main code or active HOLD.

## L0 — Policy and authority
| ID | Statement | Source | Source state |
| --- | --- | --- | --- |
| VF-POL-001 | SA design cannot change runtime, PM has independent task harness, no direct main push or self-approval | `AGENTS.md` main blob `a47d3865e9aca4b85bede781fac2dcb2ce2c0496` | EFFECTIVE_ON_MAIN |
| VF-POL-002 | First-read Constitution with architecture decision evidence | Issue #156, PR #157 at head `fe4459f7786b2589f25b84cb324b83589796d9cf` | PROPOSED_PR_NOT_MERGED |
| VF-POL-003 | Dedicated Architecture Guardian, long-term strategic memory, no manual handoff | Issue #159 and PR #160 at head `ef9a308ecf937a15504fd8479bad871ca5ff48c7` | PO_DIRECTION_APPROVED; DESIGN_PR_DRAFT; NO_AGENT_RUNNING |

## L1 — Mission and architecture invariants
| ID | Statement | Source | Authority |
| --- | --- | --- | --- |
| VF-STR-001 | Virtual Factory models configurable plants with reusable graph/equipment/ports; sensor measurements are distinct from internal physical ground truth | `ARCHITECTURE.md`, main blob `b38694647a1decfaa0367512a571e5b643090f5e` | MAIN_ARCHITECTURE |
| VF-STR-002 | TIPA P0 target is one reproducible integrated manufacturing factory run for MES + QMS demos with source-tagged synthetic evidence; standalone capability preserved | `docs/plans/TIPA_VF_DIGITAL_TWIN_ROADMAP_V1.md`, main blob `841b46763eb41fc3ea249a77943b08bfa8706b2d`, Issue #123 | PO/SA APPROVED PRODUCT DIRECTION |
| VF-STR-003 | 110 referenced process steps are a coverage register, NOT a commitment to 110 detailed simulators; unverified equipment/routing data cannot be labeled TIPA fact | Same roadmap and Issue #123 | APPROVED SCOPE RULE |
| VF-STR-004 | One VF management/simulation platform; reuse existing vNext federation/runcontrol and main G2A material capabilities; no independent duplicate public runner | Issue #155 | ACTIVE ARCHITECTURE HOLD / SA PREFERRED DESIGN, not accepted implementation |

## L2 — Decision conflicts, pending reconciliation
- **VF-DEC-123:** Issue #123 approves G1A direction and historical `FactoryRunContext` as authoritative simulation event timeline. This was based on `main@04fb9413bd5af3c4f0457047267a60b3ea4e94fe`, not current integration trunk. Detailed schemas and implementation remained gated.
- **VF-HOLD-155:** Later as-built cross-branch reconciliation found overlapping public run/session and scheduler authority between vNext R5 (unmerged) and G2A current main. Issue #155 blocks new independent runtime authority and TIPA #141–#145, prefers vNext Workspace/RuntimeSession/G4 as canonical with G2A as subordinate kernel, **subject to proof and final decision**.
- **Reconciliation required:** Do not treat VF-DEC-123's specific ownership scheme as an unqualified current architecture lock. Preserve approved product objectives while holding disputed runtime implementation. No fake superseding ADR is recorded. **Effective canonical ownership = UNRESOLVED / HOLD**.
- **VF-GOV-156/159:** Current Constitution and Guardian PRs remain DRAFT at seed creation; an approval of direction does not mean merged or CI-enforced.

## L3 — Operational pointers (MUST REFRESH)
As observed 2026-11-08, main=`3c4277a900ec397e746d0f7250a8ecaa85695b53`; PR #157 head=`fe4459f7786b2589f25b84cb324b83589796d9cf`; PR #160 head=`ef9a308ecf937a15504fd8479bad871ca5ff48c7`. Values are snapshots, *never* future-state claims. For active HOLD query #155; roadmap query main document; next permitted step is design/evidence and reconciliation, not factory implementation release.

## L4 — Evidence and known limitations
- #155 provides branch/file provenance for vNext R5 `feature/vf-vnext-r5@7558aaa31132ebeff6ef3c618b6d9198d9078177` (unmerged) versus G2A modules in main at `3c4277a900ec397e746d0f7250a8ecaa85695b53`. These source pointers are from a published SA issue, **not independently re-executed code tests in this seed**.
- #123 and roadmap contain historical claims for program milestones and reusable modules, not proof those modules are present in today's current main. Verify exact code paths and tests before using as a design dependency.
- Not verified here: exact current source-branch SHAs beyond cited issue, branch protection, all active ADRs and every implementation capability. Mark these UNKNOWN until bootstrap verifies them.
- External MES/QMS/PlantOS authority remains in the corresponding repos; this VF seed does not grant rights or assert cross-repo deployment.

## Supersession and maintenance
Changes require a reviewed PR with source/provenance, impact and explicit status. Never overwrite history as last-writer-wins; annotate conflicting source with HOLD and link a future approved ADR. Revalidate before architecture-significant decisions. No credentials or raw conversation transcript.
