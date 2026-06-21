# Virtual Factory

Virtual Factory là một phòng thí nghiệm nhà máy ảo và điều khiển, có định hướng vật lý, dùng để tạo dữ liệu telemetry công nghiệp thực tế, kiểm thử nền tảng IIoT, và phát triển dần thành mô phỏng digital twin.

Dự án bắt đầu bằng một MVP quy trình liên tục rất nhỏ, sau đó mở rộng sang cấu hình nhà máy theo mô hình, logic điều khiển, gateway giao thức, hành vi thiết bị suy giảm, và sinh cấu hình nhà máy có hỗ trợ AI.

## Chính sách tài liệu

Tài liệu tiếng Anh là tài liệu phát triển chính. Tài liệu tiếng Việt là tài liệu tham khảo bổ sung cho mục đích kinh doanh và kỹ thuật.

Khi hai phiên bản có khác biệt, tài liệu tiếng Anh là nguồn tham chiếu chính cho triển khai.

## MVP đầu tiên

MVP đầu tiên mô phỏng một quy trình chuyển chất lỏng đơn giản:

```text
T101 Source Tank -> P101 Pump -> V101 Control Valve -> T102 Destination Tank
```

Vòng điều khiển mức kín:

```text
T102.level_true
  -> LT102 Level Transmitter
  -> LT102_LEVEL measured signal
  -> LIC102 PID Controller
  -> LIC102_OUT
  -> VA101 Valve Actuator
  -> V101.opening_actual
  -> process flow
  -> T102.level_true
```

## Quy tắc kiến trúc cốt lõi

1. Simulation engine không được hard-code nhà máy.
2. Nhà máy phải được nạp từ cấu hình YAML/JSON.
3. Thiết bị tương tác nội bộ qua biến vật lý và port.
4. Sensor chuyển trạng thái vật lý thật thành tín hiệu đo công nghiệp.
5. Controller phải đọc tín hiệu đo, không đọc trực tiếp trạng thái vật lý thật.
6. Protocol gateway chỉ được publish các tín hiệu công nghiệp có thể đo được.
7. Internal truth, biến solver, degradation truth, và giá trị cân bằng khối lượng/năng lượng thật không được publish tới IIoT Platform trong industrial mode.
8. Ground truth có thể được lưu nội bộ để debug, validation, và benchmarking.
9. Cấu hình nhà máy phải theo hướng model-driven và graph-based.
10. Cấu hình low-code/no-code và sinh nhà máy có hỗ trợ AI được để cho các giai đoạn sau.

## Cấu trúc tài liệu

- `ARCHITECTURE.md`: ranh giới hệ thống, thành phần chính, và luồng runtime.
- `ROADMAP.md`: kế hoạch phát triển theo giai đoạn.
- `docs/design-principles.md`: nguyên tắc thiết kế và quy tắc mô hình hóa.
- `docs/data-model.md`: khái niệm dữ liệu cấu hình và runtime.
- `docs/output-policy.md`: quy tắc cho telemetry công nghiệp và ground truth nội bộ.
- `docs/mvp-01-continuous-process.md`: phạm vi MVP đầu tiên.
- `docs/balance-model.md`: chính sách cân bằng khối lượng, thể tích, và năng lượng.
- `docs/graph-model.md`: mô hình nhà máy dạng graph.

## Trạng thái phát triển hiện tại

**Giai đoạn 0 (Tài liệu):** ✅ Hoàn thành
**Giai đoạn 1 (MVP Quy trình liên tục):** ✅ Hoàn thành — mô phỏng vòng kín chạy với
cấu hình graph-based, pump curve, valve Cv, pipe resistance, và source-tank depletion.
**Giai đoạn 2 (Telemetry công nghiệp):** ✅ Gần hoàn thành — MQTT gateway, FastAPI
monitoring API, CSV/JSONL export, alarm manager, scenario manager, Docker deployment
đều đã có.
**Giai đoạn 3 (Mở rộng thư viện model):** 🔜 Tiếp theo — nền tảng đã sẵn sàng cho
thêm loại thiết bị, balance check, và degradation model.

Điểm nổi bật hiện tại:

- Schema cấu hình Pydantic v2 với validation chéo (controller không được đọc truth;
  internal truth không được publish trong industrial mode).
- `PlantGraph` xây dựng hoàn toàn từ cấu hình — không hard-code equipment ID.
- Process dynamics: quadratic pump curve, Cv-based valve flow, pipe resistance,
  source-tank depletion, destination-tank fill với outlet demand.
- PID (PI) controller, valve actuator với rate limit và stuck-fault.
- Sensor với noise, bias, resolution, và quality propagation.
- 5 loại scenario: normal operation, valve stuck, pump stop, pump degradation,
  demand change, sensor bias.
- 5 loại alarm: high, low, bad-quality, equals, not-equals.
- MQTT JSON publisher với auto-reconnect; FastAPI dashboard với WebSocket stream.
- Docker Compose với Mosquitto MQTT broker và API runtime.
