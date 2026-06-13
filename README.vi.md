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
2. Nhà máy phải được nạp từ cấu hình YAML hoặc JSON.
3. Thiết bị tương tác nội bộ qua biến vật lý và port.
4. Sensor chuyển trạng thái vật lý thật thành tín hiệu đo công nghiệp.
5. Controller phải đọc tín hiệu đo, không đọc trực tiếp trạng thái vật lý thật.
6. Protocol gateway chỉ được publish các tín hiệu công nghiệp có thể đo được.
7. Internal truth, biến solver, degradation truth, và giá trị cân bằng khối lượng/năng lượng thật không được publish trong industrial mode.
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

## Trạng thái hiện tại

Repository đang được khởi tạo bằng tài liệu và cấu trúc dự án. Việc triển khai simulation engine nên bắt đầu sau khi kiến trúc và phạm vi MVP được rà soát.
