# Data model

Tài liệu này định nghĩa các khái niệm dữ liệu cấp đầu cho cấu hình và runtime state. Schema chi tiết sẽ được bổ sung trong giai đoạn triển khai.

## Khái niệm cấu hình

### Plant

Cấu hình plant chứa metadata, node, edge, simulation setting, output profile, và tùy chọn scenario.

### Node

Node là một instance được cấu hình từ một model type.

Nhóm node ví dụ:

- equipment
- sensor
- actuator
- controller
- gateway

Mỗi node nên có `id`, `type`, parameters, ports, và tags tùy chọn.

### Edge

Edge kết nối hai port tương thích.

Nhóm edge ví dụ:

- physical connection
- measurement link
- signal link
- command link
- publication link

### Port

Port là interface có kiểu rõ ràng được expose bởi node. Port có thể mang biến vật lý, tín hiệu đo, command, hoặc publication stream.

### Signal

Signal là giá trị công nghiệp kèm metadata. Tín hiệu đo nên có value, unit, timestamp, quality, source, và limit tùy chọn.

### Ground truth

Ground truth là dữ liệu runtime nội bộ dùng cho debug, validation, và benchmarking. Nó không phải tín hiệu công nghiệp trừ khi được sensor chuyển thành tín hiệu đo.

## Node của MVP

MVP đầu tiên nên được biểu diễn bằng các node cấu hình sau:

- `T101`: source tank
- `P101`: pump
- `V101`: control valve
- `T102`: destination tank
- `LT102`: level transmitter
- `LIC102`: PID level controller
- `VA101`: valve actuator

Các tên này thuộc về cấu hình, không thuộc code engine.

## Tín hiệu của MVP

- `LT102_LEVEL`: tín hiệu level đo được từ `LT102`
- `LIC102_OUT`: tín hiệu output của controller `LIC102`
- `V101.opening_actual`: opening vật lý nội bộ của valve, chịu tác động bởi `VA101`
- `T102.level_true`: physical truth nội bộ, không publish trong industrial mode

## Nhóm runtime state

- `truth`: trạng thái vật lý nội bộ và giá trị solver
- `measured`: tín hiệu công nghiệp do sensor tạo ra
- `command`: tín hiệu command từ controller và actuator
- `published`: tín hiệu output được phép bởi output profile
- `diagnostic`: giá trị debug hoặc benchmark rõ ràng

## Hướng schema

Schema tương lai nên validate:

- field bắt buộc của node
- model type tồn tại
- port tương thích
- unit tương thích
- graph connectivity
- quy tắc nguồn input của controller
- tuân thủ output policy
