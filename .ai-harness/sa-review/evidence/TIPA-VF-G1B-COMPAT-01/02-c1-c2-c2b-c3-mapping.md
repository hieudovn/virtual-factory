# 02 — C1 / C2 / C2b / C3 field mapping

File/line evidence is from the MES head
`2c4d01d437bf25b44adffd610350e9df6773a853`.

## C1 — raw TIPA IoT topic/packet

| Source field | Authoritative producer | Destination | Supported? | Transform | Identity / idempotency | Provenance | Verdict |
|---|---|---|---|---|---|---|---|
| topic `enterprise/site/area/zone/line_segment` | TIPA IoT source | MES accepted topic/profile | Yes, profile-scoped | area alias (`Factory-1`/`Factory_1`), profile line check | `source_entity_key` = line key or line/machine | `source_system=iiot`, `source_profile` | `EXISTING_MAPPED` |
| topic/payload `machine_name` | TIPA IoT source | `source_machine_ref` | Yes | validated against profile machine | composite line/machine | `source_profile` | `EXISTING_MAPPED` |
| `source_timestamp` / `timestamp` / `publish_timestamp` | TIPA IoT source | `times.source_time/platform_time/received_time/event_time` | Yes | UTC normalization; source clock preferred; publish never substituted for source | event time participates in `delivery_key` | `event_time_source` retained | `EXISTING_MAPPED` |
| `status`, `mode`, `stop_error`, `employee` | TIPA PLC/state packet | `data.source_state_code/canonical_state/status_detail/operating_mode/stop_error/line_employee_ref` | Yes | `status_map` (`0 STOPPED`, `2/3 RUNNING`, `4 FAULT`, ...); no inverse fabrication | `semantic_fingerprint`, `delivery_key` | raw packet preserved by C2b, not C2 | `EXISTING_MAPPED` |
| `so`, `wo`, `item`, `motor_no`, `order_qty`, `cycle_time` | TIPA order packet | `data.so_ref/wo_ref/item_ref/motor_no_ref/external_unit_ref/planned_qty/target_cycle_time_s` | Yes | field rename; no computed order truth | source entity + event time + fingerprint | `source_system=iiot` | `EXISTING_MAPPED` |
| process `status/speed_1/speed_2/program_name/program_no/uptime_1/uptime_2` | TIPA process packet | `data.*` | Yes | numeric conversion; status copy mismatch does not change line state | fingerprint excludes uptime | `quality.state=PARTIAL` on mismatch | `EXISTING_MAPPED` |
| condition fields (`machine_temp_1..7`, `ambient_temp`, `pressure_1..7`, `vibration_1..6`, `liquid_level`, `noise`, `humidity`) | TIPA condition packet | `data.*` | Yes, listed fields only | numeric conversion | fingerprint | `source_profile` | `EXISTING_MAPPED` |
| energy fields (`voltage_1..4`, `current_1..4`, `power`, `frequency`, `energy_1/2`, `harmonic`) | TIPA energy packet | `data.*` | Yes, listed fields only | numeric conversion; energy excludes cumulative keys from fingerprint | fingerprint | `source_profile` | `EXISTING_MAPPED` |
| Unlisted raw fields | TIPA | none | **No** | dropped / not mapped | none | none | `UNAVAILABLE_PENDING_TIPA` |

Code: `ingest/tipa_iot/validator.py` (approval/profile checks),
`ingest/tipa_iot/normalizer.py:96-186` (domain mapping and hashes).

## C2 — `tipa-mes-semantic-v1`

| Source field | Destination | Supported? | Transform | Identity / idempotency | Verdict |
|---|---|---|---|---|---|
| `contract_version` | current observation contract | Yes | constant | — | `EXISTING_MAPPED` |
| `delivery_key` | current observation | Yes | SHA-256 over profile/entity/domain/event-time/fingerprint/payload hash | authoritative delivery key | `EXISTING_MAPPED` |
| `source_system`, `source_profile`, `domain`, `source_entity_key`, `source_line_ref`, `source_machine_ref`, `source_topic`, `payload_sha256` | current observation | Yes | direct | source scope | `EXISTING_MAPPED` |
| `times.*` | current observation | Yes | ISO UTC; source/platform/received retained separately | event time + fingerprint | `EXISTING_MAPPED` |
| `quality.state/errors` | current observation | Yes | `OK` / `UNMAPPED` / `PARTIAL` / `INVALID` / `SOURCE_CONFLICT` | fail closed | `EXISTING_MAPPED` |
| `semantic_fingerprint`, `data.*` | current observation | Yes | domain-specific rename only | fingerprint excludes cumulative counters | `EXISTING_MAPPED` |

C2 is a **normalized current observation**, not a reconstruction of raw C1
packets. Exact raw evidence lives in C2b.

## C2b — `tipa-cycle-evidence-v1`

| Source field | Destination | Supported? | Transform | Identity | Verdict |
|---|---|---|---|---|---|
| `packet_b64` | cycle evidence ledger | Yes | exact original bytes, base64 | payload SHA-256 | `EXISTING_MAPPED` |
| `contract_version` | cycle evidence | Yes | constant | — | `EXISTING_MAPPED` |
| `cycle_evidence_only` | cycle evidence routing | Yes | additive flag; old consumers reject missing-data envelope without changing current | delivery key | `EXISTING_MAPPED` |
| `semantic_fingerprint`, `delivery_key` | cycle evidence | Yes | independent hash over evidence contract/profile/entity/clock/context | immutable evidence | `EXISTING_MAPPED` |

Code: `ingest/tipa_iot/cycle_evidence.py:11-49`. C2b does not reverse-transform
C2; it preserves the original packet.

## C3 — `tipa-mes-finished-v1`

| Source field | Destination | Supported? | Transform | Identity / idempotency | Verdict |
|---|---|---|---|---|---|
| `finished_product.identity_key` | `mes.line.out` evidence | Yes | validated, not invented | `external_event_id`/idempotency | `EXISTING_MAPPED` |
| `finished_product.lot_serial` | `serial_text` | Yes | required non-empty; not equal to WO | identity | `EXISTING_MAPPED` |
| `finished_product.qty` | finished unit count | Yes, only `qty == 1` | non-unit qty rejected | identity | `EXISTING_MAPPED` |
| `line_external_code` | `mes.production.line` via identity map | Yes | mapping lookup; unmapped creates no output | line scope | `EXISTING_MAPPED` |
| `source_timestamp` | event time | Yes | Odoo naive UTC | time scope | `EXISTING_MAPPED` |
| `publish_timestamp` | publish evidence | Yes | retained separately | provenance | `EXISTING_MAPPED` |
| `so`, `wo`, `topic`, `payload` | source refs | Yes | retained; WO may differ from current order | source identity | `EXISTING_MAPPED` |
| quality/good/reject | **none** | **No** | — | — | `UNAVAILABLE_PENDING_TIPA`; Finished != Good != QualityRelease |

Code: `odoo/custom_addons/mes_iot_integration/services/finished_product_service.py:8,52-105`;
`odoo/custom_addons/mes_iot_integration/models/finished_product.py:21-89`
(`quality_asserted: False`).
