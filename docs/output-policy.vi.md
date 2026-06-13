# Chính sách output

Output policy bảo vệ ranh giới giữa telemetry công nghiệp thực tế và internal simulation truth.

## Industrial mode

Industrial mode là chế độ mặc định cho hệ thống bên ngoài. Chế độ này chỉ được publish các tín hiệu công nghiệp có thể đo được.

Ví dụ được phép:

- giá trị transmitter đo được
- output của controller
- command hoặc feedback của actuator nếu được cấu hình là tín hiệu công nghiệp
- tín hiệu trạng thái thiết bị có thật trong hệ thống điều khiển
- timestamp, quality code, unit, và tag metadata

Ví dụ bị cấm:

- level thật như `T102.level_true`
- flow, pressure, mass, hoặc energy thật nếu chưa được instrument cấu hình đo
- biến solver
- trạng thái numerical integration
- degradation truth
- fault truth trước khi lỗi thể hiện qua triệu chứng đo được
- balance residual ẩn

## Debug mode

Debug mode có thể expose giá trị nội bộ cho phát triển local. Debug output phải được label rõ ràng và không được dùng chung namespace với industrial tag.

## Benchmark mode

Benchmark mode có thể ghi ground truth cho validation model, đánh giá controller, chấm điểm dataset, và kiểm tra chất lượng telemetry.

Benchmark output không phải telemetry công nghiệp.

## Trách nhiệm gateway

Protocol gateway phải enforce output profile. Gateway chỉ nên publish các signal được chọn bởi profile đang hoạt động.

Nếu một signal không được cho phép rõ ràng, signal đó không được publish.

## Ranh giới sensor

Một giá trị physical truth chỉ trở thành telemetry công nghiệp có thể publish sau khi một sensor được cấu hình chuyển nó thành measured signal.

Với MVP đầu tiên:

- `LT102_LEVEL` có thể được publish.
- `LIC102_OUT` có thể được publish.
- `T102.level_true` không được publish trong industrial mode.
- `V101.opening_actual` nên được xem là internal truth trừ khi được cấu hình là tín hiệu feedback có thể đo.

## Gợi ý đặt tên

Industrial tag nên dùng tên kiểu nhà máy như `LT102_LEVEL` hoặc `LIC102_OUT`.

Giá trị nội bộ nên dùng namespace rõ ràng như `truth.T102.level`, `solver.flow.V101`, hoặc `diagnostic.balance.T102` để không bị nhầm với industrial tag.
