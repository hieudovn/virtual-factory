# Nguyên tắc thiết kế

## Ưu tiên model-driven

Engine phải thực thi mô hình nhà máy được nạp từ YAML hoặc JSON. Topology nhà máy, instance thiết bị, tên tín hiệu, và vòng điều khiển thuộc về cấu hình.

MVP không được trở thành một trường hợp đặc biệt bị hard-code trong engine.

## Physical truth là dữ liệu nội bộ

Physical truth tồn tại để mô phỏng có hành vi thực tế. Nó bao gồm level thật, flow thật, pressure thật, mass thật, energy thật, trạng thái solver, và trạng thái suy giảm.

Physical truth không tự động là tín hiệu công nghiệp.

## Sensor tạo ra thực tế công nghiệp

Hệ thống công nghiệp quan sát nhà máy qua instrument. Một tín hiệu đo có thể bị delay, noise, clipping, lỗi, bias, hoặc có quality kém.

Controller và gateway phải dùng tín hiệu đo. Chúng không được bỏ qua sensor để đọc truth.

## Component giao tiếp qua port

Thiết bị nên tương tác qua physical port, signal port, và command port có kiểu rõ ràng. Nên tránh đọc trực tiếp state của component khác.

Cách này giúp thiết bị tái sử dụng được và giúp validate graph.

## Cấu hình graph-based

Cấu trúc nhà máy là một graph gồm node và edge. Node đại diện cho equipment, sensor, controller, actuator, và gateway. Edge đại diện cho kết nối vật lý, liên kết đo, và liên kết command.

Graph validation nên phát hiện port thiếu, kết nối không hợp lệ, cycle không được phép, và ownership tín hiệu không rõ ràng.

## Output policy là một phần kiến trúc

Telemetry công nghiệp chỉ được expose các tín hiệu công nghiệp có thể đo được. Debug mode và benchmark mode có thể truy cập ground truth, nhưng các output đó phải tách rõ khỏi industrial-mode output.

## MVP nhỏ, ranh giới đúng

MVP đầu tiên được giữ nhỏ có chủ đích. Mục tiêu chính là chứng minh các ranh giới kiến trúc:

- topology nhà máy có thể cấu hình
- equipment model tái sử dụng
- điều khiển bằng measured signal
- cô lập industrial output
- lưu ground truth nội bộ
