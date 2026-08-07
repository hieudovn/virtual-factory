# Repository Agent Instructions

Before executing any task in this repository:

1. Read `.ai-harness/PM-EXECUTION-CONTRACT.md`.
2. Require a task contract under `.ai-harness/tasks/`.
3. Run harness preflight before modifying files.
4. Stop on preflight failure, baseline mismatch, task ambiguity or required tool failure.
5. Do not silently broaden task scope.
6. Do not push directly to `main`.
7. Do not merge without explicit SA authorization for the exact PR head SHA.
8. Run the full task gate before final reporting.
9. Use only the machine-derived status.
10. Do not report COMPLETE, CLOSED, SA APPROVED or NEXT SLICE AUTHORIZED unless explicitly issued by the SA.
