# Kiến trúc

Virtual Factory là một hệ thống mô phỏng theo hướng model-driven. Runtime engine thực thi mô hình nhà máy được nạp từ cấu hình, thay vì nhúng logic riêng của từng nhà máy vào code.

## Mục tiêu

- Tạo telemetry công nghiệp thực tế để kiểm thử IIoT và hệ thống điều khiển.
- Mô tả hành vi vật lý của quy trình với độ chi tiết đủ để có dynamics hợp lý.
- Lưu giữ ground truth nội bộ cho validation nhưng không publish như telemetry công nghiệp.
- Hỗ trợ các bước phát triển sau: digital twin, cấu hình low-code, và sinh mô hình nhà máy có hỗ trợ AI.

## Quy tắc kiến trúc cốt lõi

1. Simulation engine không được hard-code nhà máy.
2. Cấu hình plant phải được nạp từ YAML/JSON.
3. Tương tác nội bộ giữa thiết bị dùng biến vật lý và port.
4. Sensor chuyển physical truth thành measured industrial signal.
5. Controller chỉ đọc measured signal, không đọc true physical state.
6. Industrial protocol output chỉ publish measurable signal.
7. Internal ground truth được ẩn khỏi IIoT Platform trong industrial mode.
8. Ground truth có thể được lưu nội bộ cho debug, validation, và benchmarking.
9. Plant model là graph-based.
10. Low-code/no-code configuration và AI-assisted generation là hạng mục roadmap tương lai.

## Thành phần chính

### Cấu hình nhà máy

Nhà máy được định nghĩa bằng YAML/JSON. Cấu hình mô tả thiết bị, port, kết nối, tham số vật lý, sensor, actuator, controller, tag, và chính sách output.

Simulation engine phải xem cấu hình là mô hình nhà máy. Engine không được hard-code MVP hoặc bất kỳ quy trình tương lai nào.

### Graph model

Thiết bị và thành phần điều khiển là node. Quan hệ vật lý, tín hiệu, và lệnh điều khiển là edge.

Graph model cho phép cùng một engine chạy nhiều nhà máy khác nhau bằng cách nạp các cấu hình khác nhau.

### Equipment model

Equipment model sở hữu trạng thái vật lý nội bộ và expose các port có kiểu rõ ràng. Ví dụ gồm tank, pump, valve, pipe, transmitter, actuator, và controller.

Thiết bị tương tác qua port và biến vật lý, không truy cập trực tiếp nội bộ của thiết bị khác.

### Sensor

Sensor chuyển physical truth thành tín hiệu đo công nghiệp. Sensor có thể áp dụng range, unit, calibration, noise, lag, drift, quantization, lỗi, và quality status.

Controller và protocol gateway phải dùng output của sensor, không dùng true physical state.

### Controller

Controller đọc tín hiệu đo và tạo tín hiệu command hoặc output. MVP đầu tiên dùng `LIC102` là PID controller đọc `LT102_LEVEL` và tạo `LIC102_OUT`.

Controller không được đọc trực tiếp `T102.level_true`.

### Actuator

Actuator chuyển output của controller thành hành động trên thiết bị. Trong MVP đầu tiên, `VA101` chuyển `LIC102_OUT` thành trạng thái vật lý `V101.opening_actual`.

### Solver

Solver cập nhật trạng thái vật lý theo thời gian. Solver có thể tính internal truth như flow thật, level thật, pressure, mass, energy, và trạng thái suy giảm.

Nội bộ solver không phải telemetry công nghiệp. Các giá trị này có thể được lưu cho debug, validation, và benchmarking.

### Protocol gateway

Protocol gateway expose tín hiệu công nghiệp ra hệ thống bên ngoài như MQTT, OPC UA, REST, WebSocket, hoặc file export.

Trong industrial mode, gateway chỉ publish các tín hiệu công nghiệp có thể đo được. Internal truth và biến solver phải được giữ riêng và ẩn khỏi IIoT Platform.

## Luồng runtime MVP

```text
configuration
  -> graph loader
  -> model registry
  -> simulation runtime
  -> equipment and solver update
  -> sensors
  -> controllers
  -> actuators
  -> measurable industrial signals
  -> protocol gateways
```

## Quy tắc ranh giới

Engine sở hữu cơ chế thực thi. Cấu hình sở hữu cấu trúc nhà máy. Equipment model sở hữu hành vi tái sử dụng. Gateway sở hữu việc publish ra bên ngoài.

Không phần nào của engine được giả định rằng nhà máy luôn có `T101`, `P101`, `V101`, `T102`, `LT102`, `LIC102`, hoặc `VA101`.
