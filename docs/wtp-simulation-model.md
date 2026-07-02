# WTP Simulation Model — Equipment, Connections & Signal Taxonomy

> **Designer:** Virtual Factory Team  
> **Date:** 2026-07-02  
> **Scope:** Mô hình mô phỏng nhà máy nước sạch tiêu chuẩn  
> **Principle:** Mỗi thiết bị/cụm thiết bị có đầu vào (Input), đầu ra (Output), tham số điều khiển (Setpoint), và giá trị đo (Measurement). Các giá trị ngẫu nhiên (Disturbance) được mô phỏng trong dải thực tế.

---

## 1. Signal Taxonomy — 5 loại tham số

```
┌──────────────────────────────────────────────────────────────────┐
│                    SIGNAL TAXONOMY                               │
├──────────┬─────────────┬─────────────────────────────────────────┤
│ Ký hiệu  │ Loại        │ Ý nghĩa                                 │
├──────────┼─────────────┼─────────────────────────────────────────┤
│   SP     │ SETPOINT     │ Giá trị đặt — operator/PLC mong muốn    │
│   MV     │ MANIPULATED  │ Giá trị thực tế của cơ cấu chấp hành   │
│   PV     │ PROCESS      │ Giá trị quá trình — kết quả vật lý      │
│   DV     │ DISTURBANCE  │ Nhiễu ngoại cảnh — không kiểm soát được │
│   KPI    │ DERIVED      │ Tính toán từ các biến khác              │
└──────────┴─────────────┴─────────────────────────────────────────┘
```

**Nguyên tắc trong mô phỏng:**
- **SP → MV**: Operator đặt SP, actuator cố gắng đạt MV ≈ SP (có sai số, trễ)
- **MV + DV → PV**: MV và DV cùng quyết định PV thông qua hàm truyền vật lý/hóa học
- **PV → KPI**: Các PV được tổng hợp thành KPI
- **DV**: Dao động ngẫu nhiên trong dải, mô phỏng sự biến đổi tự nhiên

---

## 2. Process Stages & Equipment Connections

### 2.1 Tổng quan 8 Stage

```
STAGE 1          STAGE 2           STAGE 3           STAGE 4
INTAKE           CHEMICAL          CLARIFICATION     FILTRATION
                 DOSING
┌──────────┐    ┌──────────┐      ┌──────────┐      ┌──────────┐
│ SCREEN   │    │ COAGULANT│      │ FLASH    │      │ FILTER   │
│ Bar      │◄───│ Dosing   │─────►│ MIXER    │─────►│ Multi-   │
│ Screen   │    │ Skid     │      │ 101      │      │ media    │
│ 101      │    │ 101      │      │          │      │ 101+102  │
└────┬─────┘    └──────────┘      └────┬─────┘      └────┬─────┘
     │               │                 │                  │
     │          ┌──────────┐      ┌──────────┐      ┌──────────┐
     │          │ pH       │      │FLOCCU-   │      │ BACKWASH │
     │          │Correction│─────►│LATOR     │      │ PUMP     │
     │          │Skid 101  │      │101       │      │ 101      │
     │          └──────────┘      └────┬─────┘      └──────────┘
     │                                │
     │                           ┌──────────┐
     │                           │CLARIFIER │
     ▼                           │101       │───► SLUDGE
┌──────────┐                     └──────────┘
│RAW WATER │
│QUALITY   │
│STATION   │
│101       │
└──────────┘

STAGE 5            STAGE 6           STAGE 7           STAGE 8
DISINFECTION       CLEAR WATER       DISTRIBUTION      KPI & LAB
┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐
│ CHLORINE │      │ CLEAR    │      │ HSP      │      │ QUALITY  │
│ Dosing   │─────►│ WATER    │─────►│ STATION  │─────►│ TRACE-   │
│ Skid 101 │      │ TANK 101 │      │ 101      │      │ ABILITY  │
└──────────┘      └────┬─────┘      └────┬─────┘      └──────────┘
                       │                 │
┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐
│ CONTACT  │      │ CLEAR    │      │ OUTLET   │      │ PLANT    │
│ TANK 101 │─────►│ WATER    │      │ MANIFOLD │─────►│ KPI      │
│          │      │ QUALITY  │      │ 101      │      │ 101      │
└──────────┘      │ STATION  │      └──────────┘      └──────────┘
                  └──────────┘

                  ┌──────────────────────────────┐
                  │  UTILITIES (cross-cutting)   │
                  │  TRANSFORMER-101 │ MCC-101   │
                  │  ENERGY-MONITORING-101        │
                  └──────────────────────────────┘
```

### 2.2 Equipment Connection Matrix

```
SOURCE EQUIPMENT           →  TARGET EQUIPMENT          VIA (medium)
═══════════════════════════════════════════════════════════════════
RIVER (external)            →  SCREEN-101                Raw Water
SCREEN-101                  →  RAW-WATER-QUALITY-101     Raw Water
RIVER                       →  RWP-101, RWP-102          Raw Water (pumped)
RWP-101 + RWP-102           →  RAW-WATER-MANIFOLD-101    Raw Water
RAW-WATER-MANIFOLD-101      →  FLASH-MIXER-101           Raw Water
COAG-PUMP-101               →  FLASH-MIXER-101           Coagulant
PH-PUMP-101                 →  FLASH-MIXER-101           pH Corrector
FLASH-MIXER-101             →  FLOCCULATOR-101           Mixed Water
FLOCCULATOR-101             →  CLARIFIER-101             Flocculated Water
CLARIFIER-101               →  FILTER-101, FILTER-102    Settled Water
CLARIFIER-101               →  SLUDGE-PUMP-101           Sludge
FILTER-101 + FILTER-102     →  CONTACT-TANK-101          Filtered Water
CHLORINE-PUMP-101           →  CONTACT-TANK-101          Chlorine
CONTACT-TANK-101            →  CLEAR-WATER-TANK-101      Disinfected Water
CLEAR-WATER-TANK-101        →  HSP-101, HSP-102          Clear Water (via TRANSFER-PUMP)
HSP-101 + HSP-102           →  OUTLET-MANIFOLD-101       Pressurized Water
OUTLET-MANIFOLD-101         →  DISTRIBUTION NETWORK      Treated Water
```

---

## 3. Stage-by-Stage Simulation Model

### STAGE 1 — INTAKE (Nước thô đầu vào)

```
┌─────────────────────────────────────────────────────────────┐
│ STAGE 1: RAW WATER INTAKE                                   │
│                                                             │
│ DV (ngoại cảnh)           MV (điều khiển)                    │
│ ─────────────             ──────────────                    │
│ raw_turbidity   30-60 NTU  RWP-101.flow    SP: 450 m³/h     │
│ raw_ph          6.8-7.5    RWP-102.flow    SP: 440 m³/h     │
│ raw_conductivity 300-400   SCREEN.running  SP: ON            │
│ raw_temperature  25-32°C                                    │
│ raw_ammonia      0.1-1.0                                    │
│ raw_algae_index  1-5                                        │
│ raw_water_level  3.0-4.0m                                   │
│                                                             │
│ PV (kết quả đo)                                             │
│ ──────────────                                              │
│ screen_dp          = 10 + 5*(raw_turbidity/45) + noise(0,1) │
│ manifold_pressure  = 200 + 50*(total_flow/900)              │
│ RWP motor_current  = 95*(flow/450) + noise(0,1)             │
│ RWP motor_power    = 45*(flow/450)*(press/250) + noise(0,1) │
│ RWP vibration_de   = baseline + degradation(t)              │
└─────────────────────────────────────────────────────────────┘
```

### STAGE 2 — CHEMICAL DOSING (Định lượng hóa chất)

```
┌─────────────────────────────────────────────────────────────┐
│ STAGE 2: CHEMICAL DOSING                                    │
│                                                             │
│ MV (điều khiển — operator set qua API)                       │
│ ───────────────────────────────────                         │
│ COAG-PUMP-101.flow_rate    SP: 12 L/min  [5-25]            │
│   → coagulant_dose_rate = flow * 2.08 (mg/L)                │
│ CHLORINE-PUMP-101.flow_rate SP: 8 L/min   [2-18]            │
│   → chlorine_dose_rate  = flow * 0.375 (mg/L)               │
│ PH-PUMP-101.flow_rate       SP: 5 L/min   [1-12]            │
│                                                             │
│ PV (kết quả đo)                                             │
│ ──────────────                                              │
│ coagulant_dose_rate = COAG-PUMP.flow * 2.08 + noise(0,0.5) │
│ chlorine_dose_rate  = CL-PUMP.flow * 0.375 + noise(0,0.1)  │
│ streaming_current   = -5 + 0.3*(coag_dose-25) + noise(0,0.2)│
│ COAG-TANK.level     = 60 - 0.5*(COAG-PUMP.flow-12)         │
│ CL-TANK.level       = 55 - 0.5*(CL-PUMP.flow-8)            │
│                                                             │
│ KPI                                                        │
│ ───                                                        │
│ chemical_cost_per_m3 = coag_dose_rate*30 + cl_dose_rate*50  │
└─────────────────────────────────────────────────────────────┘
```

### STAGE 3 — CLARIFICATION (Keo tụ - Tạo bông - Lắng)

```
┌─────────────────────────────────────────────────────────────┐
│ STAGE 3: COAGULATION / FLOCCULATION / SEDIMENTATION         │
│                                                             │
│ Đây là stage quan trọng nhất — quyết định 80% chất lượng    │
│                                                             │
│ MV (điều khiển)                                              │
│ ──────────────                                              │
│ FLASH-MIXER-101.mixer_speed      SP: 300 RPM  [150-500]    │
│ FLOCCULATOR-101.flocculator_speed SP: 40 RPM   [10-80]     │
│ CLARIFIER-SCRAPER-101.running     SP: ON                    │
│ SLUDGE-PUMP-101.running           SP: Intermittent          │
│                                                             │
│ ═══════════ VẬT LÝ KEO TỤ ═══════════                      │
│                                                             │
│ Công thức Jar Test (tiêu chuẩn ngành nước):                 │
│                                                             │
│ coag_efficiency = f(coag_dose, mixing_energy, raw_turb)     │
│                                                             │
│ coag_dose_norm  = coag_dose_rate / 25     (25 mg/L = opt)   │
│ mixing_norm     = mixer_speed / 300                        │
│ floc_norm       = flocculator_speed / 40                   │
│                                                             │
│ efficiency_max  = 0.85  (tối đa 85% giảm độ đục)           │
│ efficiency = efficiency_max * coag_dose_norm                │
│            * mixing_norm * floc_norm                        │
│            * min(1.0, 50/raw_turbidity)  (khó hơn khi đục cao)│
│                                                             │
│ PV (kết quả)                                                │
│ ────────────                                                │
│ settled_turbidity = raw_turbidity * (1 - efficiency)        │
│                   + noise(0, 0.3)                           │
│                   + setpoint_error(COAG-PUMP)               │
│                                                             │
│ settled_ph = raw_ph                                         │
│            - 0.15*(coag_dose_norm)  (coagulant hạ nhẹ pH)  │
│            + 0.05*(PH-PUMP.flow/5)  (pH corrector nâng pH)  │
│            + noise(0, 0.02)                                 │
│                                                             │
│ floc_size_index = 3.5 * coag_dose_norm * floc_norm          │
│                 + noise(0, 0.1)                             │
│                                                             │
│ clarifier_efficiency = efficiency / 0.85                     │
│   (1.0 = optimal, < 0.7 = problem)                          │
└─────────────────────────────────────────────────────────────┘
```

### STAGE 4 — FILTRATION (Lọc đa phương tiện)

```
┌─────────────────────────────────────────────────────────────┐
│ STAGE 4: MULTIMEDIA FILTRATION                              │
│                                                             │
│ MV (điều khiển)                                              │
│ ──────────────                                              │
│ FILTER-101.effluent_flow     SP: 200 m³/h  [100-250]       │
│ FILTER-102.effluent_flow     SP: 195 m³/h  [100-250]       │
│ BACKWASH-PUMP-101.running     SP: OFF (ON khi DP > 80 kPa) │
│                                                             │
│ ═══════════ VẬT LÝ LỌC ═══════════                         │
│                                                             │
│ filter_efficiency_base = 0.96  (96% giảm độ đục khi sạch)  │
│                                                             │
│ filter_loading = (filter_dp - 20) / 60  (0→1 khi DP tăng)  │
│ filter_efficiency = filter_efficiency_base                  │
│                   - 0.06 * filter_loading                  │
│                   + noise(0, 0.005)                         │
│                                                             │
│ PV (kết quả)                                                │
│ ────────────                                                │
│ filtered_turbidity = settled_turbidity                      │
│                    * (1 - filter_efficiency)                │
│                    + noise(0, 0.02)                         │
│                                                             │
│ filtered_ph = settled_ph + noise(0, 0.05)                  │
│                                                             │
│ filter_dp = 25 + 35 * filter_loading                       │
│           + noise(0, 1)                                    │
│           + 0.05 * raw_turbidity/45  (turb cao → tắc nhanh)│
│                                                             │
│ filter_level = 1.5 - 0.3*(effluent_flow/200)               │
│                                                             │
│ filter_dp TĂNG DẦN theo thời gian (filter ripening):        │
│   d(DP)/dt = 0.02 kPa/s (base)                             │
│            + 0.01 * (settled_turbidity/8)  (nước đục→nhanh)│
│            + 0.01 * (algae_index/3)        (tảo→tắc nhanh) │
│                                                             │
│ BACKWASH: Khi DP > 80 kPa → reset DP = 20 kPa sau 300s      │
│                                                             │
│ particle_count_proxy = filtered_turbidity * 80 + noise(0,5)│
│ filter_run_quality  = 1.0 - filter_loading                 │
└─────────────────────────────────────────────────────────────┘
```

### STAGE 5 — DISINFECTION (Khử trùng bằng Clo)

```
┌─────────────────────────────────────────────────────────────┐
│ STAGE 5: CHLORINE DISINFECTION                              │
│                                                             │
│ MV (điều khiển)                                              │
│ ──────────────                                              │
│ (CHLORINE-PUMP-101.flow_rate — đã set ở Stage 2)            │
│                                                             │
│ ═══════════ HÓA HỌC KHỬ TRÙNG ═══════════                  │
│                                                             │
│ Clo phản ứng với NH3 tạo chloramine (clo kết hợp):          │
│                                                             │
│ cl_dose  = chlorine_pump_flow * 0.375  (L/min→mg/L)         │
│ cl_demand_nh3 = raw_ammonia * 5.0    (NH3 tiêu thụ clo)    │
│ cl_demand_org = raw_algae_index * 0.3 (chất hữu cơ tiêu thụ)│
│                                                             │
│ total_chlorine = cl_dose + noise(0, 0.05)                   │
│ combined_cl    = min(cl_demand_nh3 + cl_demand_org, total_cl)│
│ free_chlorine  = total_chlorine - combined_cl               │
│                                                             │
│ CT_value = free_chlorine * contact_time  (mg·min/L)         │
│                                                             │
│ PV (kết quả)                                                │
│ ────────────                                                │
│ contact_time = 30 * (CONTACT-TANK.level/65)                 │
│              * (CONTACT-TANK.inflow/design_flow)            │
│              + noise(0, 1)                                  │
│                                                             │
│ orp = 450 + 250*(free_chlorine/0.8) + noise(0, 5)          │
│                                                             │
│ KPI                                                        │
│ ───                                                        │
│ disinfection_ok = free_chlorine >= 0.5 AND CT_value >= 15   │
└─────────────────────────────────────────────────────────────┘
```

### STAGE 6 — CLEAR WATER (Nước sạch)

```
┌─────────────────────────────────────────────────────────────┐
│ STAGE 6: CLEAR WATER STORAGE                                │
│                                                             │
│ PV (kết quả)                                                │
│ ────────────                                                │
│ clear_water_turbidity = filtered_turbidity * 0.95           │
│                       + noise(0, 0.01)                      │
│                                                             │
│ CLEAR-WATER-TANK.level = 70                                 │
│   + 0.5*(total_inflow - total_outflow)/100                  │
│   + noise(0, 1)                                            │
│                                                             │
│ KPI                                                        │
│ ───                                                        │
│ quality_index = 0.4*(1 - clear_turbidity/1.0)              │
│               + 0.3*(free_chlorine/0.8)                    │
│               + 0.3*(ph_in_range(clear_ph))                │
│   (1.0 = hoàn hảo, < 0.6 = vấn đề)                         │
└─────────────────────────────────────────────────────────────┘
```

### STAGE 7 — DISTRIBUTION (Phân phối)

```
┌─────────────────────────────────────────────────────────────┐
│ STAGE 7: HIGH-SERVICE PUMPING & DISTRIBUTION                │
│                                                             │
│ MV (điều khiển)                                              │
│ ──────────────                                              │
│ HSP-101.flow_rate  SP: 320 m³/h  [100-400]                 │
│ HSP-102.flow_rate  SP: 320 m³/h  [0-450]                   │
│                                                             │
│ PV (kết quả)                                                │
│ ────────────                                                │
│ HSP discharge_press = 350 + 0.5*total_HSP_flow             │
│                     + noise(0, 5)                           │
│                                                             │
│ outlet_manifold_press = discharge_press                     │
│   - 0.02 * total_HSP_flow²  (head loss)                    │
│   + noise(0, 3)                                            │
│                                                             │
│ outlet_manifold_flow = HSP-101.flow + HSP-102.flow          │
│                      + noise(0, 3)                         │
│                                                             │
│ outlet_turbidity = clear_water_turbidity + noise(0, 0.01)  │
│ outlet_free_cl   = free_chlorine * 0.9 + noise(0, 0.02)   │
│ outlet_ph        = settled_ph + noise(0, 0.03)             │
│                                                             │
│ HSP motor_current = 180*(flow/320)*(press/400) + noise(0,2)│
│ HSP motor_power   = 110*(flow/320)*(press/400) + noise(0,1)│
│ HSP winding_temp  = 75 + 20*(motor_current-180)/30          │
│                   + noise(0, 0.5)                           │
│                                                             │
│ TRANSFER-PUMP-101.running: ON khi CWT.level > 20%           │
│                                                             │
│ KPI                                                        │
│ ───                                                        │
│ outlet_compliance = (outlet_turbidity <= 1.0)               │
│                    AND (outlet_free_cl >= 0.2)              │
│                    AND (outlet_ph between 6.5-8.5)          │
└─────────────────────────────────────────────────────────────┘
```

### STAGE 8 — KPI & TRACEABILITY (Chỉ số hiệu suất)

```
┌─────────────────────────────────────────────────────────────┐
│ STAGE 8: PLANT KPI & QUALITY TRACEABILITY                   │
│                                                             │
│ Tất cả KPI đều là DERIVED — tính từ PV của các stage trước  │
│                                                             │
│ ═══════════ ENERGY ═══════════                              │
│ total_active_power  = sum(motor_powers) + 50 (aux)         │
│ total_energy_today  = tích lũy (total_power * dt/3600) kWh │
│ total_water_today   = tích lũy (outlet_flow * dt/3600) m³  │
│ spec_energy_cons    = total_power / outlet_flow (kWh/m³)    │
│ energy_cost_per_m3  = spec_energy * 2500 (VND/kWh→VND/m³)  │
│ peak_demand         = max(total_power trong 15 phút)        │
│                                                             │
│ ═══════════ COST ═══════════                                │
│ cost_per_m3 = energy_cost_per_m3                            │
│             + chemical_cost_per_m3                          │
│             + 1500  (fixed cost: labor, maintenance)        │
│                                                             │
│ ═══════════ QUALITY ═══════════                             │
│ outlet_quality_index = 0.35*(1 - outlet_turbidity/1.0)      │
│                      + 0.30*(outlet_free_cl/0.8)            │
│                      + 0.20*(ph_score)                      │
│                      + 0.15*(1 - abs(cost-3200)/2000)       │
│   (1.0 = xuất sắc, < 0.5 = kém)                            │
│                                                             │
│ ═══════════ TRACEABILITY ═══════════                        │
│ raw_water_impact_score = clamp(0,10, raw_turbidity/8        │
│                         + raw_ammonia*3 + raw_algae_index)  │
│                                                             │
│ chemical_dosing_abnormality = clamp(0,10,                   │
│   abs(coag_dose_rate - optimal_dose)/5                     │
│   + abs(cl_dose_rate - optimal_cl_dose)/2)                 │
│                                                             │
│ energy_abnormality = clamp(0,10,                            │
│   (spec_energy - 0.38)/0.03)                               │
│                                                             │
│ outlet_quality_risk_score = clamp(0,10,                     │
│   0.4*raw_water_impact + 0.3*chemical_abnormality           │
│   + 0.2*energy_abnormality + 0.1*(1-compliance_rate))      │
│                                                             │
│ probable_root_cause_code:                                    │
│   0   = normal                                              │
│   1xx = raw water quality (101=turbidity, 102=ammonia, ...) │
│   2xx = chemical dosing (201=coagulant, 202=chlorine, ...)  │
│   3xx = clarification (301=settled turbidity high)          │
│   4xx = filtration (401=breakthrough, 402=high DP, ...)     │
│   5xx = disinfection (501=low chlorine, 502=low CT, ...)    │
│   6xx = pumping/distribution (601=HSP trip, ...)            │
│                                                             │
│ ═══════════ COMPLIANCE ═══════════                          │
│ compliance_rate_today = (số frame đạt / tổng frame) * 100   │
│ water_production_today = total_water_today                  │
│ treatment_yield = 100 - (waste/total_intake)*100            │
│   (waste = sludge + backwash, ~3-6% tổng)                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Complete Parameter Table — All 92 Signals

### 4.1 DV — DISTURBANCE VARIABLES (7) — Nhiễu ngoại cảnh

| # | Signal ID | Type | Default | Range | Behavior | Ghi chú |
|---|-----------|------|---------|-------|----------|---------|
| DV1 | `RAW-WATER-QUALITY-STATION-101.raw_turbidity` | DV | 45 NTU | 10-120 | random_walk | Nguồn nước thô |
| DV2 | `RAW-WATER-QUALITY-STATION-101.raw_ph` | DV | 7.15 | 6.5-9.0 | random_walk | pH tự nhiên |
| DV3 | `RAW-WATER-QUALITY-STATION-101.raw_conductivity` | DV | 350 µS/cm | 200-600 | random_walk | Độ dẫn điện |
| DV4 | `RAW-WATER-QUALITY-STATION-101.raw_temperature` | DV | 28 °C | 20-35 | sine (mùa) | Nhiệt độ môi trường |
| DV5 | `RAW-WATER-QUALITY-STATION-101.raw_ammonia` | DV | 0.5 mg/L | 0.05-2.0 | random_walk | Ô nhiễm NH3 |
| DV6 | `RAW-WATER-QUALITY-STATION-101.raw_algae_index` | DV | 3.0 | 0.5-10 | random_walk + mùa | Tảo theo mùa |
| DV7 | `INTAKE-STRUCTURE-101.raw_water_level` | DV | 3.5 m | 2.0-5.0 | sine (mùa) | Mực nước sông |

### 4.2 MV — MANIPULATED VARIABLES (12) — Điều khiển được

| # | Signal ID | Type | Default SP | Range | Unit | Ảnh hưởng trực tiếp |
|---|-----------|------|-----------|-------|------|-------------------|
| MV1 | `COAG-PUMP-101.flow_rate` | MV | 12 | 5-25 | L/min | settled_turbidity, floc_size, coag_dose_rate |
| MV2 | `CHLORINE-PUMP-101.flow_rate` | MV | 8 | 2-18 | L/min | free_chlorine, total_chlorine, cl_dose_rate |
| MV3 | `PH-PUMP-101.flow_rate` | MV | 5 | 1-12 | L/min | settled_ph → filtered_ph → outlet_ph |
| MV4 | `RWP-101.flow_rate` | MV | 450 | 200-550 | m³/h | manifold_press, total throughput |
| MV5 | `RWP-102.flow_rate` | MV | 440 | 0-500 | m³/h | manifold_press (bơm dự phòng) |
| MV6 | `HSP-101.flow_rate` | MV | 320 | 100-400 | m³/h | outlet_press, manifold_flow |
| MV7 | `HSP-102.flow_rate` | MV | 320 | 0-450 | m³/h | outlet_press (dự phòng) |
| MV8 | `FLASH-MIXER-101.mixer_speed` | MV | 300 | 150-500 | RPM | coagulation efficiency |
| MV9 | `FLOCCULATOR-101.flocculator_speed` | MV | 40 | 10-80 | RPM | floc size → settled_turbidity |
| MV10 | `SCREEN-101.running_status` | MV | ON | ON/OFF | bool | screen_dp |
| MV11 | `CLARIFIER-SCRAPER-101.running_status` | MV | ON | ON/OFF | bool | sludge accumulation |
| MV12 | `SLUDGE-PUMP-101.running_status` | MV | Intermittent | ON/OFF | bool | clarifier efficiency |

### 4.3 PV — PROCESS VARIABLES (43) — Kết quả quá trình

| # | Signal ID | Type | Derived From | Unit | Normal Range |
|---|-----------|------|-------------|------|-------------|
| PV1 | `INTAKE-STRUCTURE-101.screen_dp` | PV | raw_turbidity | kPa | 10-25 |
| PV2 | `INTAKE-STRUCTURE-101.inlet_valve_position` | PV | raw_water_level | % | 60-100 |
| PV3 | `RAW-WATER-PUMP-STATION-101.discharge_pressure` | PV | RWP flows | kPa | 320-380 |
| PV4 | `RWP-101.running_status` | PV | = ON (MV4 > 0) | bool | ON |
| PV5 | `RWP-101-MOTOR.motor_current` | PV | MV4, PV3 | A | 80-110 |
| PV6 | `RWP-101-MOTOR.power` | PV | MV4, PV3 | kW | 40-50 |
| PV7 | `RWP-101-MOTOR.vibration_de` | PV | degradation(t) | mm/s | 0.5-3.0 |
| PV8 | `RWP-102-MOTOR.motor_current` | PV | MV5 | A | 0-108 |
| PV9 | `RAW-WATER-MANIFOLD-101.manifold_pressure` | PV | MV4+MV5 | kPa | 220-280 |
| PV10 | `COAG-TANK-101.level` | PV | MV1 | % | 45-75 |
| PV11 | `COAG-TANK-101.temperature` | PV | DV4 (ambient) | °C | 20-30 |
| PV12 | `COAGULATION-CONTROL-STATION-101.streaming_current` | PV | MV1, DV1 | mV | -8~-3 |
| PV13 | `COAGULATION-CONTROL-STATION-101.floc_size_index` | PV | MV1, MV8, MV9 | — | 2.5-4.5 |
| PV14 | `CHLORINE-TANK-101.level` | PV | MV2 | % | 45-65 |
| PV15 | `CLARIFIER-101.settled_turbidity` | PV | DV1, MV1, MV8, MV9 | NTU | 4-12 |
| PV16 | `CLARIFIER-101.settled_ph` | PV | DV2, MV1, MV3 | pH | 6.8-7.2 |
| PV17 | `FILTER-101.filter_dp` | PV | PV15, accumulation(t) | kPa | 20-60 |
| PV18 | `FILTER-101.effluent_flow` | PV | ≈ MV4/2 | m³/h | 180-220 |
| PV19 | `FILTER-101.filter_level` | PV | PV18 | m | 1.2-1.8 |
| PV20 | `FILTER-102.filter_dp` | PV | PV15, accumulation(t) | kPa | 15-60 |
| PV21 | `FILTER-102.effluent_flow` | PV | ≈ MV4/2 | m³/h | 175-215 |
| PV22 | `FILTER-102.filter_level` | PV | PV21 | m | 1.1-1.7 |
| PV23 | `BACKWASH-PUMP-101.running_status` | PV | PV17 > 80 | bool | OFF |
| PV24 | `FILTER-QUALITY-STATION-101.filtered_turbidity` | PV | PV15, PV17 | NTU | 0.2-0.5 |
| PV25 | `FILTER-QUALITY-STATION-101.filtered_ph` | PV | PV16 | pH | 6.7-7.2 |
| PV26 | `FILTER-QUALITY-STATION-101.particle_count_proxy` | PV | PV24 | cnt/mL | 5-40 |
| PV27 | `CONTACT-TANK-101.level` | PV | flow balance | % | 55-75 |
| PV28 | `CONTACT-TANK-101.contact_time` | PV | PV27, flow | min | 20-40 |
| PV29 | `DISINFECTION-QUALITY-STATION-101.free_chlorine` | PV | MV2, DV5, DV6, PV28 | mg/L | 0.5-1.0 |
| PV30 | `DISINFECTION-QUALITY-STATION-101.total_chlorine` | PV | MV2 | mg/L | 0.8-1.5 |
| PV31 | `DISINFECTION-QUALITY-STATION-101.orp` | PV | PV29 | mV | 600-700 |
| PV32 | `CLEAR-WATER-TANK-101.level` | PV | flow balance | % | 60-80 |
| PV33 | `CLEAR-WATER-QUALITY-STATION-101.clear_water_turbidity` | PV | PV24 | NTU | 0.1-0.4 |
| PV34 | `TRANSFER-PUMP-101.running_status` | PV | PV32 > 20% | bool | ON |
| PV35 | `HIGH-SERVICE-PUMP-STATION-101.discharge_pressure` | PV | MV6+MV7 | kPa | 350-450 |
| PV36 | `HSP-101-MOTOR.motor_current` | PV | MV6, PV35 | A | 150-210 |
| PV37 | `HSP-101-MOTOR.power` | PV | MV6, PV35 | kW | 100-125 |
| PV38 | `HSP-101-MOTOR.winding_temp` | PV | PV36 | °C | 60-95 |
| PV39 | `HSP-102-MOTOR.motor_current` | PV | MV7 | A | 0-180 |
| PV40 | `HSP-102-MOTOR.power` | PV | MV7 | kW | 0-105 |
| PV41 | `OUTLET-MANIFOLD-101.manifold_pressure` | PV | PV35 | kPa | 350-420 |
| PV42 | `OUTLET-MANIFOLD-101.manifold_flow` | PV | MV6+MV7 | m³/h | 550-800 |
| PV43 | `TRANSFORMER-101.winding_temp` | PV | KPI4 (total_power) | °C | 50-85 |

### 4.4 KPI — DERIVED (30 signals) — Tính toán từ PV

| # | Signal ID | Type | Derived From | Unit | Normal Range |
|---|-----------|------|-------------|------|-------------|
| KPI1 | `CHEMICAL-CONSUMPTION-STATION-101.coagulant_dose_rate` | KPI | MV1 * 2.08 | mg/L | 15-40 |
| KPI2 | `CHEMICAL-CONSUMPTION-STATION-101.chlorine_dose_rate` | KPI | MV2 * 0.375 | mg/L | 3-6 |
| KPI3 | `CHEMICAL-CONSUMPTION-STATION-101.chemical_cost_per_m3` | KPI | KPI1*30 + KPI2*50 | VND/m³ | 50-150 |
| KPI4 | `CLARIFIER-QUALITY-STATION-101.clarifier_efficiency_index` | KPI | (DV1-PV15)/DV1 / 0.85 | — | 0.7-0.95 |
| KPI5 | `FILTER-QUALITY-STATION-101.filter_run_quality_index` | KPI | 1 - (PV17-20)/60 | — | 0.6-0.95 |
| KPI6 | `CLEAR-WATER-TANK-101.quality_index` | KPI | composite(PV33,PV29,PV25) | — | 0.7-1.0 |
| KPI7 | `TRANSFER-OUTLET-QUALITY-STATION-101.outlet_turbidity` | PV | ≈ PV33 | NTU | 0.15-0.35 |
| KPI8 | `TRANSFER-OUTLET-QUALITY-STATION-101.outlet_ph` | KPI | ≈ PV25 | pH | 6.5-8.5 |
| KPI9 | `TRANSFER-OUTLET-QUALITY-STATION-101.outlet_free_chlorine` | KPI | PV29 * 0.9 | mg/L | 0.3-0.8 |
| KPI10 | `TRANSFER-OUTLET-QUALITY-STATION-101.outlet_compliance_status` | KPI | KPI7+KPI9+KPI8 (3 checks) | bool | TRUE |
| KPI11 | `TRANSFORMER-101.load_percent` | KPI | KPI12/tx_capacity | % | 55-75 |
| KPI12 | `TRANSFORMER-101.oil_temp` | KPI | PV43 - 10 | °C | 40-70 |
| KPI13 | `ENERGY-MONITORING-STATION-101.total_active_power` | KPI | Σ(motor_powers)+50 | kW | 500-750 |
| KPI14 | `ENERGY-MONITORING-STATION-101.total_energy_today` | KPI | cumulative(KPI13) | kWh | — |
| KPI15 | `ENERGY-MONITORING-STATION-101.specific_energy_consumption` | KPI | KPI13 / PV42 | kWh/m³ | 0.30-0.50 |
| KPI16 | `ENERGY-MONITORING-STATION-101.energy_cost_per_m3` | KPI | KPI15 * 2500 | VND/m³ | 750-1250 |
| KPI17 | `ENERGY-MONITORING-STATION-101.peak_demand` | KPI | rolling_max(KPI13) | kW | 550-900 |
| KPI18 | `MCC-101.runtime_hours` | KPI | cumulative(1h/h) | h | — |
| KPI19 | `LAB-SAMPLING-STATION-101.cod` | KPI | DV1 * 0.3 | mg/L | 5-25 |
| KPI20 | `LAB-SAMPLING-STATION-101.toc` | KPI | DV1 * 0.06 | mg/L | 1-5 |
| KPI21 | `QUALITY-TRACEABILITY-ENGINE-101.raw_water_impact_score` | KPI | composite(DV1,DV5,DV6) | — | 0-10 |
| KPI22 | `QUALITY-TRACEABILITY-ENGINE-101.chemical_dosing_abnormality_score` | KPI | deviation(KPI1,KPI2 from optimal) | — | 0-10 |
| KPI23 | `QUALITY-TRACEABILITY-ENGINE-101.energy_abnormality_score` | KPI | deviation(KPI15 from 0.38) | — | 0-10 |
| KPI24 | `QUALITY-TRACEABILITY-ENGINE-101.outlet_quality_risk_score` | KPI | weighted(KPI21,KPI22,KPI23) | — | 0-10 |
| KPI25 | `QUALITY-TRACEABILITY-ENGINE-101.probable_root_cause_code` | KPI | argmax(risk contributors) | — | 0 |
| KPI26 | `PLANT-KPI-101.water_production_today` | KPI | cumulative(PV42) | m³ | 0-20000 |
| KPI27 | `PLANT-KPI-101.treatment_yield` | KPI | 100 - waste/total*100 | % | 94-99.5 |
| KPI28 | `PLANT-KPI-101.outlet_quality_index` | KPI | composite(KPI7,KPI9,KPI8,KPI30) | — | 0.7-1.0 |
| KPI29 | `PLANT-KPI-101.compliance_rate_today` | KPI | % frames KPI10=TRUE | % | 95-100 |
| KPI30 | `PLANT-KPI-101.cost_per_m3` | KPI | KPI16+KPI3+1500 | VND/m³ | 2500-4000 |

---

## 5. Noise & Randomness Model

```python
class NoiseModel:
    """
    Mô hình nhiễu cho tất cả các tín hiệu.
    Mỗi loại tín hiệu có đặc trưng nhiễu riêng.
    """
    
    # ---- DV Noise (lớn, chậm) ----
    # raw_turbidity: random_walk(step=0.5, bounds=[10,120])
    #   → thay đổi chậm, vài NTU mỗi giờ
    
    # ---- MV Noise (nhỏ, actuator error) ----
    # COAG-PUMP.flow: setpoint ± 2% 
    #   → actuator không bao giờ đạt chính xác setpoint
    #   flow_actual = flow_setpoint * (1 + noise(0, 0.02))
    
    # ---- PV Noise (sensor measurement noise) ----
    # turbidity sensors: ±0.05 NTU (low-range), ±2% (high-range)
    # pH sensors: ±0.02 pH
    # flow meters: ±1% of reading
    # pressure transmitters: ±2 kPa
    # chlorine analyzers: ±0.03 mg/L
    
    # ---- Degradation Noise (thiết bị xuống cấp) ----
    # Filter DP: +0.02 kPa mỗi giây vận hành (base)
    # Motor vibration: +0.001 mm/s mỗi giờ
    # Motor winding: +0.01°C mỗi giờ vận hành
```

---

## 6. Simulation Loop Algorithm

```python
def simulation_step(dt_s: float = 1.0):
    """
    Một bước mô phỏng 1 giây.
    Thứ tự tính toán theo đúng flow vật lý.
    """
    
    # === PHASE 0: UPDATE DISTURBANCES ===
    for dv in DISTURBANCE_VARIABLES:
        dv.update(dt_s)  # random_walk hoặc sine theo thời gian
    
    # === PHASE 1: INTAKE ===
    screen_dp = 10 + 5*(raw_turbidity/45) + noise(0, 1)
    rwp_total_flow = rwp101_flow_actual + rwp102_flow_actual
    manifold_pressure = 200 + 50*(rwp_total_flow/900) + noise(0, 3)
    rwp101_current = 95*(rwp101_flow_actual/450) + noise(0, 1)
    rwp101_power = 45*(rwp101_flow_actual/450)*(manifold_pressure/250) + noise(0, 1)
    rwp101_vibration += 0.001 * dt_s  # degradation
    
    # === PHASE 2: CHEMICAL ===
    coag_dose_rate = coag_pump_flow_actual * 2.08 + noise(0, 0.5)
    cl_dose_rate = cl_pump_flow_actual * 0.375 + noise(0, 0.1)
    chemical_cost = coag_dose_rate*30 + cl_dose_rate*50
    
    # === PHASE 3: CLARIFICATION ===
    coag_eff = compute_coagulation_efficiency(
        coag_dose_rate, mixer_speed, flocculator_speed, raw_turbidity
    )
    settled_turbidity = raw_turbidity * (1 - coag_eff) + noise(0, 0.3)
    settled_ph = raw_ph - 0.15*(coag_dose_rate/25) + 0.05*(ph_pump_flow/5) + noise(0, 0.02)
    
    # === PHASE 4: FILTRATION ===
    filter_dp_101 += (0.02 + 0.01*(settled_turbidity/8) + 0.01*(algae_index/3)) * dt_s
    if filter_dp_101 > 80 and backwash_waiting == 0:
        backwash_waiting = 300  # 5 min backwash
    if backwash_waiting > 0:
        backwash_waiting -= dt_s
        if backwash_waiting <= 0:
            filter_dp_101 = 20  # reset
    
    filter_eff = 0.96 - 0.06*((filter_dp_101-20)/60) + noise(0, 0.005)
    filtered_turbidity = settled_turbidity * (1 - filter_eff) + noise(0, 0.02)
    
    # === PHASE 5: DISINFECTION ===
    cl_demand = raw_ammonia*5.0 + raw_algae_index*0.3
    total_chlorine = cl_dose_rate + noise(0, 0.05)
    free_chlorine = max(0, total_chlorine - cl_demand) + noise(0, 0.02)
    
    # === PHASE 6: CLEAR WATER ===
    clear_water_turbidity = filtered_turbidity * 0.95 + noise(0, 0.01)
    
    # === PHASE 7: DISTRIBUTION ===
    hsp_total_flow = hsp101_flow_actual + hsp102_flow_actual
    outlet_pressure = 350 + 0.5*hsp_total_flow - 0.02*hsp_total_flow**2 + noise(0, 3)
    outlet_turbidity = clear_water_turbidity + noise(0, 0.01)
    outlet_free_cl = free_chlorine * 0.9 + noise(0, 0.02)
    
    outlet_compliance = (
        outlet_turbidity <= 1.0 and
        outlet_free_cl >= 0.2 and
        6.5 <= outlet_ph <= 8.5
    )
    
    # === PHASE 8: KPI ===
    total_power = rwp101_power + rwp102_power + hsp101_power + hsp102_power + 50
    spec_energy = total_power / max(0.1, hsp_total_flow)
    energy_cost = spec_energy * 2500
    
    cost_per_m3 = energy_cost + chemical_cost + 1500
    
    quality_index = (
        0.35*(1-outlet_turbidity/1.0) +
        0.30*(outlet_free_cl/0.8) +
        0.20*(ph_score(outlet_ph)) +
        0.15*(1-abs(cost_per_m3-3200)/2000)
    )
    
    # Update traceability
    raw_impact = clamp(0, 10, raw_turbidity/8 + raw_ammonia*3 + raw_algae_index)
    chem_abnorm = clamp(0, 10, abs(coag_dose_rate-25)/5 + abs(cl_dose_rate-4.5)/2)
    energy_abnorm = clamp(0, 10, (spec_energy-0.38)/0.03)
    risk_score = 0.4*raw_impact + 0.3*chem_abnorm + 0.2*energy_abnorm + 0.1*(1-compliance_rate)
    
    # === BUILD TELEMETRY FRAME ===
    frame = collect_all_92_signals()
    
    # === PUBLISH TO PLANTOS ===
    ingest_client.post_measurements(frame)
```

---

## 7. MV Actuation Model (Setpoint → Actual)

```python
class Actuator:
    """
    Mô phỏng cơ cấu chấp hành: SP → MV thực tế.
    """
    def __init__(self, name, min_val, max_val, slew_rate, accuracy_pct):
        self.name = name
        self.min_val = min_val
        self.max_val = max_val
        self.slew_rate = slew_rate      # max change per second
        self.accuracy_pct = accuracy_pct # steady-state error %
        self.current = 0                # current actual position
        self.setpoint = None
    
    def set(self, sp: float):
        self.setpoint = clamp(self.min_val, self.max_val, sp)
    
    def update(self, dt_s: float) -> float:
        if self.setpoint is None:
            return self.current
        
        # Slew rate limit (không thay đổi tức thời)
        max_delta = self.slew_rate * dt_s
        error = self.setpoint - self.current
        delta = clamp(-max_delta, max_delta, error)
        
        self.current += delta
        
        # Add steady-state error
        actual = self.current * (1 + noise(0, self.accuracy_pct/100))
        return clamp(self.min_val, self.max_val, actual)

# Ví dụ:
coag_pump = Actuator("COAG-PUMP-101", min=5, max=25, slew_rate=2, accuracy_pct=2)
# SP=12 → actual ≈ 11.8-12.2, thay đổi tối đa 2 L/min/s
# Từ 12→18 mất ~3 giây để đạt SP mới

hsp_pump = Actuator("HSP-101", min=100, max=400, slew_rate=50, accuracy_pct=1)
# Từ 320→200 mất ~2.4 giây (120/50)
```

---

## 8. API Điều Khiển

```yaml
GET  /api/v1/control                    # List all 12 MVs + current values
POST /api/v1/control/{signal_id}        # Set new setpoint
Body: {"value": 18.0}

GET  /api/v1/disturbances               # List all 7 DVs + current values
POST /api/v1/disturbances/{signal_id}   # Override DV (for scenario injection)
Body: {"value": 85.0, "override": true} # Force raw_turbidity = 85 NTU

GET  /api/v1/status                     # Full plant status
GET  /api/v1/telemetry/latest           # Latest 92 signal values
```

---

## 9. So sánh: Trước vs Sau

| Khía cạnh | ❌ Contract hiện tại (pattern-based) | ✅ Mô hình mới (MV→PV→KPI) |
|-----------|-------------------------------------|---------------------------|
| Loại tham số | Tất cả là measurement | SP/MV/PV/DV/KPI rõ ràng |
| Quan hệ nhân quả | Không có, mỗi tín hiệu độc lập | Có — theo đúng vật lý WTP |
| Điều khiển được | Không | 12 MV qua API |
| Nhiễu ngoại cảnh | Không phân biệt | 7 DV (random_walk/sine) |
| Scenario | Override params thủ công | Set MV/DV → PV tự phản ứng |
| Realism | ⭐⭐ | ⭐⭐⭐⭐⭐ |
