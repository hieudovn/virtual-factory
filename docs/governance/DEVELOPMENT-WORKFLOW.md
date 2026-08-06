# Development Workflow — Virtual Factory

## Branch Strategy

- `main` — protected, requires PR + CI
- `feature/*` — feature branches, merge into `main` via PR
- `chore/*` — governance, tooling, CAPA branches
- `docs/*` — documentation-only branches

## PR Requirements

1. All changes MUST go through a Pull Request targeting `main`
2. PR MUST pass VF-DM CI (`vf-dm-ci.yml`) before merge
3. At least one approving review required
4. Direct push to `main` is BLOCKED
5. Force push to `main` is BLOCKED
6. Branch deletion on `main` is BLOCKED

## Commit Standards

- Each commit message MUST reference the milestone slice (e.g., `M2-S04-C02:`)
- Commit messages MUST describe WHAT changed and WHY
- No "wip", "tmp", or "fix" commit messages without context

## Review Standards

- SA review required for all M2 milestone slices
- PM must provide concrete evidence (GitHub SHA, CI link, test count) before declaring READY
- Status like "IMPLEMENTED — READY FOR SA REVIEW" is only valid when:
  - Code is committed AND pushed to GitHub
  - CI has run and passed on the exact commit SHA
  - Evidence fields are concrete (not "TODO" or "TBD")

## Pre-Push Hook

Install with: `bash scripts/install-git-hooks.sh`

The pre-push hook:
- Rejects pushes directly to `main`
- Warns on force pushes to any branch
- Runs `python -m pytest -q --tb=short` before push

## Incident Response

When a governance violation is discovered:
1. Document in `docs/governance/incidents/`
2. Create a CAPA branch (`chore/*`)
3. Implement corrective actions
4. Merge CAPA PR through normal PR process
5. Verify protection is active post-merge
