# Lộ trình

Lộ trình này chia giai đoạn rõ ràng để simulation core luôn theo hướng model-driven ngay từ đầu.

## Giai đoạn 0: Tài liệu và cấu trúc

- Tạo tài liệu phát triển chính bằng tiếng Anh.
- Tạo tài liệu tham khảo bổ sung bằng tiếng Việt.
- Xác định quy trình MVP, quy tắc kiến trúc, chính sách output, graph model, và balance model.
- Không triển khai simulation engine trong giai đoạn này.

## Giai đoạn 1: MVP quy trình liên tục

✅ Hoàn thành — vòng lặp mô phỏng lõi chạy với cấu hình graph-based.

- ✅ Nạp nhà máy từ YAML/JSON (schema Pydantic v2 với validation chéo).
- ✅ Biểu diễn quy trình MVP dạng graph (`PlantGraph` với node và edge có kiểu).
- ✅ Triển khai model tái sử dụng cho source tank, pump, control valve,
  destination tank, level transmitter, PID controller, và valve actuator.
- ✅ Mô phỏng vòng điều khiển mức kín bằng tín hiệu đo.
- ✅ Process dynamics với quadratic pump curve, valve Cv-based flow,
  pipe resistance, và source-tank depletion.
- ✅ Publish output ở industrial mode mà không rò rỉ internal truth.
- ✅ Lưu ground truth nội bộ cho debug và validation.

## Giai đoạn 2: Giao diện telemetry công nghiệp

✅ Gần hoàn thành — protocol gateway, API, và export đã có.

- ✅ Abstraction cho protocol gateway (MQTT JSON publisher với reconnect logic).
- ✅ Đường xuất telemetry real-time (MQTT + WebSocket qua FastAPI).
- ✅ Metadata tín hiệu, quality, engineering unit, và timestamp (`SignalValue`).
- ✅ Output profile cho industrial mode, debug mode, và benchmark mode.
- ✅ CSV và JSONL telemetry export.
- ✅ FastAPI monitoring API với dashboard UI, REST endpoints, và WebSocket stream.
- ✅ Docker / docker-compose deployment với Mosquitto MQTT broker.
- ✅ Alarm manager (high, low, bad-quality, equals, not-equals).
- ✅ Scenario manager (normal operation, valve stuck, pump stop, pump degradation,
  demand change, sensor bias).
- ⬜ OPC UA gateway (tương lai).
- ⬜ Sparkplug B / production-grade MQTT (tương lai).

## Giai đoạn 3: Mở rộng thư viện model

🔄 Đang tiến hành — model registry và các type mới đang được thêm.

- ✅ Model registry nạp type từ YAML (trường `python_class`).
- ✅ `runtime_factory.py` dùng `ModelRegistry` — không còn hard-coded type dicts.
- 🔜 Thêm model tái sử dụng cho nhiều loại thiết bị hơn (pipe, heat exchanger).
- 🔜 Thêm hành vi sensor và actuator phổ biến (done — delay, drift, stuck).
- 🔜 Thêm mô hình suy giảm và lỗi.
- 🔜 Thêm kiểm tra balance và báo cáo validation chi tiết hơn.

## Giai đoạn 4: Công cụ tạo cấu hình

- Thêm schema validation cho cấu hình nhà máy.
- Thêm ví dụ và template.
- Thêm workflow cấu hình low-code/no-code.
- Thêm guardrail để tránh vi phạm output policy.

## Giai đoạn 5: Sinh nhà máy có hỗ trợ AI

- Sinh cấu hình nhà máy ban đầu từ ngôn ngữ tự nhiên, mô tả kiểu P&ID, hoặc danh sách thiết bị dạng bảng.
- Validate model được sinh ra bằng schema và graph rule.
- Yêu cầu con người review trước khi chạy cấu hình được sinh.

## Giai đoạn 6: Hướng digital twin

- Hỗ trợ calibration với dữ liệu nhà máy thật.
- Hỗ trợ replay kịch bản và phân tích what-if.
- Hỗ trợ benchmarking giữa telemetry mô phỏng và telemetry quan sát được.
