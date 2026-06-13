# Graph model

Virtual Factory dùng plant model dạng graph để engine có thể thực thi nhiều cấu hình nhà máy mà không hard-code topology.

## Node

Node đại diện cho instance được cấu hình từ model type tái sử dụng.

Nhóm node:

- equipment
- sensor
- actuator
- controller
- gateway

Ví dụ node MVP:

- `T101`: source tank
- `P101`: pump
- `V101`: control valve
- `T102`: destination tank
- `LT102`: level transmitter
- `LIC102`: PID controller
- `VA101`: valve actuator

## Edge

Edge đại diện cho quan hệ giữa các port tương thích.

Nhóm edge:

- physical: di chuyển vật chất hoặc năng lượng
- measurement: physical truth được sensor quan sát
- signal: measured signal được controller hoặc gateway sử dụng
- command: controller output được actuator sử dụng
- publication: signal được phép expose qua gateway

## Physical graph của MVP

```text
T101.out -> P101.in
P101.out -> V101.in
V101.out -> T102.in
```

## Control graph của MVP

```text
T102.level_true -> LT102.input
LT102.output -> LT102_LEVEL
LT102_LEVEL -> LIC102.process_variable
LIC102.output -> LIC102_OUT
LIC102_OUT -> VA101.command
VA101.output -> V101.opening_actual
```

Edge từ `T102.level_true` tới `LT102.input` là nội bộ. Edge này không làm cho `T102.level_true` được phép publish.

## Quy tắc validation

Graph validation nên kiểm tra:

- mọi edge tham chiếu tới node và port tồn tại
- các port được nối phải tương thích
- kết nối vật lý đúng hướng và đúng medium
- controller đọc measured signal
- gateway chỉ publish signal được phép
- output profile không expose internal truth trong industrial mode
- mỗi industrial tag có producer rõ ràng

## Hướng tương lai

Graph model nên hỗ trợ visual editing, cấu hình low-code/no-code, validation report, và sinh plant có hỗ trợ AI trong các giai đoạn sau.
