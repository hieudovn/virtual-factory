# MES-INT-02 — Virtual Factory Consumer Adapter

## Trạng thái: **STOPPED — ngoài phạm vi repo VF (theo quyết định SA)**

## 1. Gate & mục tiêu

PM Prompt: `MES-INT-02_VirtualFactory_Consumer_Adapter_PM_Prompt.md`

- **Mục tiêu:** cài đặt **MES consumer boundary** — nhận `ProjectedMessage` từ VF qua REST, ánh xạ 4 loại message (`mes.execution_event`, `mes.genealogy_relationship`, `mes.quality_result`, `mes.release`) thành evidence MES (`mes.production.event` + quality + genealogy + release), với idempotency, context binding, vocabulary mapping và security.
- **2 repository liên quan:**
  - VF producer: `hieudovn/virtual-factory`
  - **MES consumer: `hieudovn/MES-dev-and-demo-project`** ← nơi chứa deliverable

## 2. Quyết định SA (lý do dừng)

> Chỉ được thực hiện trong repo VF này. Mọi thay đổi ở dự án khác phải giao cho PM dự án đó thực hiện.

Toàn bộ deliverable của MES-INT-02 nằm ở **repo MES** → **ngoài phạm vi được phép**. Vì vậy gate bị **STOPPED** và đề xuất giao lại cho **PM dự án MES**.

## 3. Đã thực hiện (chỉ khảo sát — không commit)

Trong repo MES, **chỉ đọc** để lập bản đồ tích hợp (không thay đổi gì còn lại):

- Docs: `00-constitution.md`, `03-architecture.md`, `05-mes-iot-integration-contract.md`, `11-canonical-data-model-and-knowledge-graph.md`.
- Models: `mes.production.event`, `mes.event.service`, `mes.quality.result`, `mes.wip.unit`, `mes.plantos.adapter` (mẫu adapter hiện có), `canonical.identity.map`, `plantos_context_resolver`.
- Security: `mes_core/security/` (groups + `ir.model.access`), controller patterns (`mes_shopfloor/controllers/`).
- Tests: `mes_core/tests/common.py` + suite characterization.
- Đã xác nhận baseline MES `9b54ec0e8852f9c08fc9b35704745d2f2c32f2c1`.

Đã thực hiện **1 edit thử nghiệm** vào `mes_production_event.py` rồi **revert hoàn toàn** (`git checkout`). Repo MES hiện **ở baseline `9b54ec0`, không còn thay đổi nào của tôi** (chỉ còn các file `.pyc` `__pycache__` khác biệt từ trước khi tôi vào — không phải do tôi).

## 4. Phạm vi chỉnh sửa repo MES **KHÔNG được thực hiện** (bàn giao cho PM MES)

### 4.1 Model changes
| File | Thay đổi đề xuất |
|---|---|
| `mes_core/models/mes_production_event.py` | Thêm `("virtual_factory", "Virtual Factory")` vào selection `source_system`; thêm 3 event type `operation_completed` / `genealogy_relationship` / `wip_released` vào `event_type` selection + `ALL_MES_EVENT_TYPES` + `MES_TO_CANONICAL_EVENT_MAP`; thêm field `simulation_time_s` (Float) |
| `mes_core/models/mes_quality.py` | Thêm `attempt_number` (Integer), `simulation_time_s` (Float), `external_event_id` (Char, idempotency) |
| `mes_core/models/mes_wip_genealogy.py` (MỚI) | Model generic `mes.wip.genealogy.relation` hỗ trợ **multi-parent** (SSO2→MTR, RSO2→MTR): parent/child (wip_unit_id + external_code), relationship_type, workstation/operation, occurred_at, simulation_time_s, source_system, external_event_id (idempotency) |

### 4.2 Adapter + transport
| File | Thay đổi đề xuất |
|---|---|
| `mes_core/services/virtual_factory_adapter.py` (MỚI) | `mes.virtual_factory.adapter.process_message(message)` theo mẫu `mes.plantos.adapter`: validate envelope → dedup (`external_event_id` + `source_system=virtual_factory`) → resolve context qua `canonical.identity.map`/code → map 4 message type → trả `processed/duplicate/waiting_for_mapping/rejected/failed` |
| `mes_core/controllers/virtual_factory_controller.py` (MỚI) | REST `type="json"` route hẹp `/mes/virtual_factory/events`, auth API token qua `ir.config_parameter`, delegate ngay sang adapter (không domain logic trong controller) |

### 4.3 Security
| File | Thay đổi đề xuất |
|---|---|
| `mes_core/security/mes_core_service_groups.xml` | Thêm group `group_mes_virtual_factory` |
| `mes_core/security/ir_model_access_service_accounts.xml` | Grant create cho `mes.production.event`/`mes.quality.result`/`mes.wip.genealogy.relation`, read cho `mes.workstation`/`mes.production.line`/`mes.wip.unit`/`canonical.identity.map`/`product.product` cho group mới (mirror `group_mes_bridge`) |

### 4.4 Data / mapping
| File | Thay đổi đề xuất |
|---|---|
| `mes_core/data/virtual_factory_mapping.xml` (MỚI, noupdate) | Static demo mapping: VF `station_id` (AP01…AP11) → `mes.workstation.code`; VF `sub_line_id` (ASSY-SL01…06) → `mes.production.line.code` (qua `canonical.identity.map`) |

### 4.5 Tests & evidence (trong repo MES)
- `mes_core/tests/test_virtual_factory_adapter.py` (~19 test theo §16: duplicate idempotent, unknown type, missing envelope, missing mapping → waiting_for_mapping, source_system=virtual_factory, AP06 FAIL1/PASS2 → 2 quality, AP08 NG1/PASS2 → 2 quality, AP11 QC ≠ RELEASE, AP04 2 parents, no duplicate genealogy, RELEASE once, RELEASE không complete MO/stock, unauthorized denied, six sub-lines không cross-map…).
- `.ai-harness/sa-review/{CURRENT.md, reports/MES-INT-02.md, evidence/MES-INT-02/}` trong **repo MES**.

### 4.6 Nguyên tắc đã xác định (để PM MES tham chiếu)
- `source_system = virtual_factory`; idempotency = VF `message.key` → `external_event_id` + unique `(external_event_id, source_system)`.
- `mes.execution_event` → `operation_completed` (KHÔNG complete WO); `mes.release` → `wip_released` (KHÔNG complete MO, KHÔNG post FG inventory/stock); `mes.quality_result` → `quality_passed`/`quality_failed` (giữ `attempt_number`, `record_id`, station, sim time); `mes.genealogy_relationship` → 2 quan hệ multi-parent.
- Bảo toàn `simulation_time_s` (simulation truth) tách khỏi `event_time` (receipt wall clock).
- `mes.production.event.create()` hiện bắt buộc `workorder_id/line_id/workstation_id` (Layer 6) → cần resolve ít nhất `line_id`/`workstation_id`; nếu thiếu mapping → `waiting_for_mapping` (KHÔNG tạo MO/WO giả).
- PlantOS adapter hiện `Event.create()` trực tiếp (không qua `mes.event.service`); cần quyết định path thống nhất.

## 5. VF contract fixtures (có thể sinh read-only từ repo VF)

Theo §15, fixtures phải là message thật từ baseline VF đã accept (`f72cc95`), không tự bịa. Có thể sinh bằng `AssyObservationBridge` + JSONL gateway trong repo VF (read-only, không sửa code):
1. `mes.execution_event` (operation completion)
2. `mes.genealogy_relationship` (AP04)
3. `mes.quality_result` AP06 PASS
4. AP06 FAIL attempt 1
5. AP06 PASS attempt 2
6. AP08 NG
7. AP08 PASS
8. AP11 final QC PASS
9. AP11 RELEASE

→ Sẵn sàng cung cấp dưới dạng JSONL cho PM MES khi SA yêu cầu (không ghi vào repo MES).

## 6. Khuyến nghị

1. **Giao MES-INT-02 cho PM dự án MES** thực hiện toàn bộ §4 trong repo `MES-dev-and-demo-project` (baseline `9b54ec0`).
2. Repo VF không cần thay đổi gì thêm (producer contract đã đóng băng ở M6-INT-01 + C01).
3. Nếu cần, SA có thể yêu cầu tôi sinh bộ **VF contract fixtures** (read-only) làm tài liệu bàn giao.

## 7. Kết luận

```text
MES-INT-02 — STOPPED (SA boundary: MES-repo changes must be executed by the MES project PM)
```
