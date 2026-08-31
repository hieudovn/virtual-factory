# M6-INT-01-C01 — Per-gateway delivery retry

```text
poll1: gateway A = DELIVERED ×13, gateway B = FAILED ×13
poll2: gateway A = no resend (0 attempts), gateway B = DELIVERED ×13
        gateway A messages = 13 (unchanged), gateway B messages = 13 (caught up)
poll3: 0 new deliveries
```
