# Lộ trình

Lộ trình này chia giai đoạn rõ ràng để simulation core luôn theo hướng model-driven ngay từ đầu.

## Giai đoạn 0: Tài liệu và cấu trúc

- Tạo tài liệu phát triển chính bằng tiếng Anh.
- Tạo tài liệu tham khảo bổ sung bằng tiếng Việt.
- Xác định quy trình MVP, quy tắc kiến trúc, chính sách output, graph model, và balance model.
- Không triển khai simulation engine trong giai đoạn này.

## Giai đoạn 1: MVP quy trình liên tục

- Nạp nhà máy từ YAML hoặc JSON.
- Biểu diễn quy trình MVP dạng graph:
  `T101 -> P101 -> V101 -> T102`.
- Triển khai model tái sử dụng cho source tank, pump, control valve, destination tank, level transmitter, PID controller, và valve actuator.
- Mô phỏng vòng điều khiển mức kín bằng tín hiệu đo.
- Publish output ở industrial mode mà không rò rỉ internal truth.
- Lưu ground truth nội bộ cho debug và validation.

## Giai đoạn 2: Giao diện telemetry công nghiệp

- Thêm abstraction cho protocol gateway.
- Thêm ít nhất một đường xuất telemetry real-time.
- Thêm metadata tín hiệu, quality, engineering unit, và timestamp.
- Thêm output profile cho industrial mode, debug mode, và benchmark mode.

## Giai đoạn 3: Mở rộng thư viện model

- Thêm model tái sử dụng cho nhiều loại thiết bị hơn.
- Thêm hành vi sensor và actuator phổ biến.
- Thêm mô hình suy giảm và lỗi.
- Thêm kiểm tra balance và báo cáo validation chi tiết hơn.

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
