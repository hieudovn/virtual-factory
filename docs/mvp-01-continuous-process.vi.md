# MVP 01: Quy trình liên tục

MVP đầu tiên chứng minh Virtual Factory có thể chạy một quy trình vòng kín có thể cấu hình, đồng thời tách telemetry công nghiệp khỏi internal truth.

## Quy trình

```text
T101 Source Tank -> P101 Pump -> V101 Control Valve -> T102 Destination Tank
```

## Vòng điều khiển

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

## Hành vi bắt buộc

- Plant được nạp từ YAML hoặc JSON.
- Engine không hard-code tên thiết bị của MVP.
- Tank duy trì level hoặc volume thật ở bên trong.
- Pump và valve ảnh hưởng process flow qua physical port.
- `LT102` đọc nội bộ `T102.level_true` và phát ra `LT102_LEVEL`.
- `LIC102` đọc `LT102_LEVEL`, không đọc `T102.level_true`.
- `VA101` chuyển `LIC102_OUT` thành `V101.opening_actual`.
- Protocol gateway chỉ publish tín hiệu công nghiệp đo được và được phép trong industrial mode.
- Ground truth được giữ nội bộ cho debug, validation, và benchmarking.

## Industrial tag tối thiểu

- `LT102_LEVEL`
- `LIC102_OUT`

Có thể thêm industrial tag tùy chọn chỉ khi chúng đại diện cho giá trị có thể đo hoặc thấy được trong hệ thống điều khiển.

## Giá trị nội bộ

Ví dụ giá trị nội bộ:

- `T102.level_true`
- `T101.level_true`
- process flow thật
- valve opening thật trừ khi được cấu hình là measured feedback
- solver state
- balance residual

Các giá trị này không được publish trong industrial mode.

## Tiêu chí thành công

- Plant được cấu hình có thể chạy mà không cần code engine riêng cho plant đó.
- Vòng điều khiển có thể điều chỉnh level `T102` qua measured feedback.
- Output policy ngăn rò rỉ ground truth ở industrial mode.
- Debug hoặc benchmark output có thể so sánh measured signal với truth khi được bật rõ ràng.
