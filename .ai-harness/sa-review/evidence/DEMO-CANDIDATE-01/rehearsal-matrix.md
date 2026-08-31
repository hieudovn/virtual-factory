# DEMO-CANDIDATE-01 — Rehearsal matrix

## R1 — HAPPY_PATH (ASSY-SL01)

- motor: MTR-0001
- release time: 1680.0 s
- AP04 parent IDs: ['SSO2-0001', 'RSO2-0001']
- MES observation count: 64
- second poll new deliveries: 0
- final released count: 1

## R2 — AP06 FAIL → RETEST → PASS

- target sub-line: ASSY-SL03
- released: True
- AP06 authoritative quality history (MTR-0002): [('FAIL', 1), ('PASS', 2)]
- MES quality observations: 2 (record ids ['QR-0002', 'QR-0003'])
- second poll new deliveries: 0

## R3 — AP08 NG → REINSPECT → PASS

- target sub-line: ASSY-SL02
- released: True
- AP08 authoritative quality history (MTR-0002): [('NG', 1), ('PASS', 2)]
- MES quality observations: 2 (record ids ['QR-0006', 'QR-0007'])

## R4 — FAILED_FINAL

- target sub-line: ASSY-SL03
- WIP released: False
- quality status: failed_final
- AP06 attempts: [('FAIL', 1), ('FAIL', 2)]
- AP11 RELEASE observations for failed WIP: 0

## R5 — MANUAL sanity

- operations awaiting action after dwell: True
- auto-completed without command: False
- MANUAL timing stays legacy fixed (op.timing is None): True
- resolved decision: ('AP06', 'PASS')
- outbound quality observations after completion: 1
