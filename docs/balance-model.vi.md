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
