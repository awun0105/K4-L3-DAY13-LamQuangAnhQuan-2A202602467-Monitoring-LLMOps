# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert mẫu để tham khảo

Ví dụ dưới đây minh họa mức độ cụ thể cần có. Học viên không cần copy nguyên, nhưng ba alert trong bài nộp nên rõ ràng tương tự: điều kiện là gì, kéo dài bao lâu, ảnh hưởng tới user ra sao và người trực cần kiểm tra gì trước.

- Tên: `HighLatencyP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: latency P95 của `response_sent.latency_ms`
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000ms` trong 5 phút
- Ảnh hưởng tới người dùng: người dùng phải chờ lâu hơn trước khi nhận câu trả lời
- Ba bước kiểm tra đầu tiên:
  1. Mở dashboard latency để xác nhận P95/P99 và khoảng thời gian tăng.
  2. Lọc `data/logs.jsonl` trong khoảng đó, lấy một `correlation_id` có `latency_ms` cao.
  3. Mở trace cùng `correlation_id` trên Langfuse, so sánh các span chính để xác định bước nào bất thường.
- Mitigation tạm thời: dựa trên evidence thực tế để rollback prompt, khôi phục cấu hình liên quan, tắt practice scenario hoặc giảm tải khi demo.
- Owner: `student-<MSSV>`

## Alert 1

- Tên: HighLatencyP95
- Severity: warning
- Duration: 5m
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: Latency P95 của `response_sent.latency_ms` <= 3000ms
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000ms` trong 5 phút
- Ảnh hưởng tới người dùng: Người dùng phải chờ lâu hơn trước khi nhận câu trả lời.
- Ba bước kiểm tra đầu tiên:
  1. Mở dashboard latency để xác nhận P95/P99 và khoảng thời gian tăng.
  2. Lọc `data/logs.jsonl` trong khoảng đó, lấy một `correlation_id` có `latency_ms` cao.
  3. Mở trace cùng `correlation_id` trên Langfuse, so sánh các span chính (retrieval vs generation) để xác định bước nào bất thường.
- Mitigation tạm thời: Dựa trên evidence thực tế để rollback prompt, khôi phục cấu hình liên quan, hoặc tắt practice scenario bằng `python scripts/inject_incident.py --disable`.
- Owner: student-2A202602467

## Alert 2

- Tên: HighErrorRate
- Severity: critical
- Duration: 5m
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: Error Rate <= 2.0%
- Điều kiện và thời gian duy trì: `error_rate_pct > 2.0%` trong 5 phút
- Ảnh hưởng tới người dùng: Người dùng nhận mã lỗi HTTP 500 khi gửi yêu cầu chat.
- Ba bước kiểm tra đầu tiên:
  1. Mở dashboard kiểm tra panel Errors xem tỷ lệ request lỗi tăng đột biến từ lúc nào.
  2. Lọc file `data/logs.jsonl` tìm các event `request_failed` để đọc `error_type` và thông điệp lỗi.
  3. Mở trace có correlation_id tương ứng trên Langfuse để xem exception phát sinh tại observation nào.
- Mitigation tạm thời: Kiểm tra kết nối dịch vụ phụ trợ, rollback bản build gần nhất hoặc kích hoạt fallback mode.
- Owner: student-2A202602467

## Alert 3

- Tên: LowRetrievalSuccessRate
- Severity: critical
- Duration: 5m
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: Retrieval Success Rate >= 90.0%
- Điều kiện và thời gian duy trì: `retrieval_success_rate_pct < 90.0%` trong 5 phút
- Ảnh hưởng tới người dùng: AI trả lời không có tài liệu tham khảo chính xác hoặc rơi vào câu trả lời chung chung, gây giảm chất lượng.
- Ba bước kiểm tra đầu tiên:
  1. Mở panel Errors trên dashboard để xác định tỷ lệ thành công của tool `retrieval`.
  2. Lọc file `data/logs.jsonl` theo `tool_name == "retrieval"` và `tool_success == False`.
  3. Mở Langfuse Trace xem span `retrieval` có bị timeout hoặc trả về lỗi kết nối không.
- Mitigation tạm thời: Kiểm tra trạng thái cơ sở dữ liệu tri thức / vector store hoặc cấu hình timeout an toàn.