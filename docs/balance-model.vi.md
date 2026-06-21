# Balance model

Balance model định nghĩa cách Virtual Factory xử lý mass, volume, và energy truth bên trong mô phỏng.

## Mục đích

Tính toán balance giúp hành vi quy trình thực tế hơn và dễ kiểm thử hơn. Các giá trị này cũng cung cấp dữ liệu validation cho debug và benchmarking.

Giá trị balance là internal truth trừ khi được instrument cấu hình đo.

## Phạm vi MVP

MVP đầu tiên nên tập trung vào cân bằng thể tích hoặc khối lượng chất lỏng quanh destination tank:

```text
change in T102 inventory = inflow from V101 - outflow or loss
```

Nếu MVP không cấu hình outflow từ `T102`, level sẽ tăng theo inflow và hình học tank.

## Trạng thái triển khai

✅ **Mass balance đã được implement và đang hoạt động.**

`MassBalance.evaluate()` chạy mỗi bước simulation bên trong
`SimulationEngine.step()`, ngay sau `update_continuous_process()`.
Kết quả được ghi vào `RuntimeState.diagnostics["mass_balance"]`.

### Các trường báo cáo

| Field | Kiểu | Mô tả |
|---|---|---|
| `mass_in_kg` | float | Khối lượng vào destination tank trong step này |
| `mass_out_kg` | float | Khối lượng ra khỏi destination tank trong step này |
| `mass_stored_before_kg` | float | Tổng khối lượng lưu trữ trong hệ thống đầu step |
| `mass_stored_after_kg` | float | Tổng khối lượng lưu trữ trong hệ thống cuối step |
| `mass_stored_delta_kg` | float | Thay đổi khối lượng lưu trữ trong step này |
| `residual_kg` | float | Mất cân bằng = mass_in - mass_out - delta_stored |
| `residual_pct` | float | Mất cân bằng tương đối so với max throughput (%) |
| `balanced` | bool | True khi \|residual_pct\| ≤ 0.1 % |
| `message` | str | Tóm tắt bằng ngôn ngữ tự nhiên |

### Truy cập kết quả

```python
engine.step()
engine.state.diagnostics["mass_balance"]
# {"mass_in_kg": ..., "balanced": True, "message": "Mass balanced", ...}
```

## Internal truth

Solver có thể tính:

- flow rate thật
- inventory thật của tank
- level thật của tank
- restriction thật của valve
- balance residual
- trạng thái numerical integration

Các giá trị này hữu ích cho validation nhưng không phải telemetry công nghiệp.

## Chuyển đổi qua sensor

Một giá trị truth có nguồn gốc từ balance chỉ được thấy bên ngoài khi đi qua sensor. Ví dụ, `T102.level_true` được `LT102` chuyển thành `LT102_LEVEL`.

Controller đọc `LT102_LEVEL`.

## Balance residual

Balance residual nên có trong debug hoặc benchmark mode để phát hiện lỗi model, vấn đề integration, hoặc cấu hình không hợp lệ.

Balance residual không được publish trong industrial mode.

## Hướng tương lai

Các giai đoạn sau có thể thêm:

- cân bằng áp suất
- cân bằng năng lượng
- hành vi multi-phase
- truyền nhiệt
- thuộc tính vật liệu
- kiểm tra conservation trên các subgraph của plant
