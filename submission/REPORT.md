# Báo cáo cá nhân — K4-L3B Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Lâm Quang Anh Quân
- **MSSV:** 2A202602467
- **Lớp:** K4-L3B
- **Repository URL:** https://github.com/awun0105/K4-L3-DAY13-LamQuangAnhQuan-2A202602467-Monitoring-LLMOps.git
- **Commit SHA cuối:** ff0a5bd83c3364d109e0e4c077257b3cfa60843b
- **Challenge ID:** day13-k4-l3b-monitoring-llmops-v1
- **Tên project Langfuse cá nhân:** `day13-k4-l3b-2A202602467`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.png` |
| Log validator | `evidence/02-log-validator.png` |
| Dashboard validator | `evidence/03-dashboard-validator.png` |
| Structured log | `evidence/04-structured-log.png` |
| PII redaction | `evidence/05-pii-redaction.png` |
| Trace list | `evidence/06-trace-list.png` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | `evidence/08-trace-metadata.png` |
| Prompt versions | `evidence/09-prompt-versions.png` |
| Prompt rollback | `evidence/10-prompt-rollback.png` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.png` |
| Incident log | `evidence/13-incident-log.png` |
| Incident trace | `evidence/14-incident-trace.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 30/100 | 100/100 | Đạt toàn bộ tiêu chí PII, correlation ID và log enrichment |
| `validate_dashboard.py` | 6/6 hợp lệ | 6/6 hợp lệ | Đủ 6 panel theo dashboard contract |
| `pytest` | 22 passed | 22 passed | Toàn bộ unit tests đều pass |
| Số traces hợp lệ | 0 | 15 | Tạo thành công trên project Langfuse cá nhân |
| Số PII leak | 0 | 0 | Không rò rỉ email, số điện thoại, CCCD hay thẻ |
| Latency P95 / TTFT P95 | ~1500ms / N/A | ~380ms / ~50ms | Độ trễ ổn định ở điều kiện bình thường |
| Retrieval success rate | N/A | 100% | RAG truy xuất tài liệu thành công |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Trong `CorrelationIdMiddleware`, request trước tiên được xóa sạch context cũ bằng `clear_contextvars()`. Sau đó trích xuất header `x-request-id`; nếu không có hoặc là "MISSING" thì sinh mới dạng `req-<8-hex>`. Mã này được nạp vào structlog qua `bind_contextvars(correlation_id=...)` và gán vào Response Headers `x-request-id`.
- **Các metadata được ghi vào structured log:** Gồm `ts` (ISO UTC), `level`, `service`, `event`, `correlation_id`, `user_id_hash` (băm SHA-256), `session_id`, `feature`, `model`, `env`, `latency_ms`, `ttft_ms`, `tokens_in`, `tokens_out`, `cost_usd`, `quality_score`.
- **Cách bảo đảm PII được scrub trước khi ghi:** Đăng ký processor `scrub_event` trong chuỗi pipeline structlog ngay trước `JsonlFileProcessor` và `JSONRenderer`. Mọi text khớp regex email, SĐT, CCCD, thẻ ngân hàng, hộ chiếu đều bị thay thế bằng nhãn `[REDACTED_<TYPE>]` trước khi ghi ra đĩa.
- **Cách kiểm chứng kết quả:** Chạy `uv run python scripts/validate_logs.py` kiểm định toàn diện file log đạt 100/100, đồng thời chạy unit test `uv run pytest tests/test_pii.py` và `tests/test_validate_logs.py`.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** Khởi tạo project `day13-k4-l3b-2A202602467` trên Langfuse Cloud, cấu hình API Key riêng trong `.env`. Mọi traces đều mang metadata tương ứng với request chạy từ máy local.
- **Cấu trúc root/retrieval/generation observations:** Root trace `day13-agent-request` chứa Agent observation `lab-agent-run`, bên trong bóc tách thành 2 child observations: `retrieval` (retriever span đo query và doc count) và `generation` (generation span đo prompt, token usage và cost).
- **Cách nối trace với log:** Gán `correlation_id` từ middleware vào metadata của Root trace qua `propagate_attributes(metadata={"correlation_id": correlation_id})`. Nhờ đó, từ mã trong log có thể tìm thấy trace tương ứng ngay lập tức.
- **Prompt name:** `day13-chat`
- **Version/label baseline:** Version 1 (label: `baseline`, `production`).
- **Version/label candidate:** Version 2 (label: `candidate`).
- **Trace ID của mỗi version:**
  - testing v2 (candidate - production): `3a377234c69296b07f3c7fcef0c22a4d`
  - testing v1 (prod - baseline): `0b8fad3211455f7a4a0b82cb8c8c3185`
- **Cách promote và rollback `production`:** Trên Langfuse Prompts UI, chuyển nhãn `production` sang Version 2 để promote; khi phát hiện sự cố, chuyển nhãn `production` quay lại Version 1 trên giao diện mà không cần chỉnh sửa code hay restart server.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** 6 panel định nghĩa trong `config/dashboard.yaml` gồm: Latency (P50/P95/P99/TTFT), Traffic (req/min), Errors & Retrieval Success Rate, Tokens & Cost (USD), Quality Proxy, Prompt Versions Distribution.
- **SLO và lý do chọn:** Latency P95 <= 3000ms và Tỷ lệ thành công >= 99.5% trong cửa sổ 28 ngày. Lý do: Giữ trải nghiệm phản hồi mượt mà cho ứng dụng chat tương tác thời gian thực.
- **Cách tính error budget:** Với SLO 99.5%, ngân sách lỗi là 0.5%. Nếu hệ thống phục vụ 10,000 request thì tối đa 50 request được phép thất bại hoặc chậm hơn 3000ms.
- **Ba alert và runbook tương ứng:**
  1. `HighLatencyP95`: P95 latency > 3000ms kéo dài 5 phút (Runbook tại `docs/alerts.md#alert-1`).
  2. `HighErrorRate`: Error rate > 2.0% kéo dài 5 phút (Runbook tại `docs/alerts.md#alert-2`).
  3. `LowRetrievalSuccessRate`: RAG success rate < 90.0% kéo dài 5 phút (Runbook tại `docs/alerts.md#alert-3`).

> Ví dụ cách viết error budget: "SLO 99.5% trong 28 ngày nghĩa là error budget 0.5%. Nếu workload có 10,000 request thì tối đa 50 request được phép lỗi hoặc chậm hơn ngưỡng SLO."

## 7. Điều tra challenge

- **Challenge ID:** day13-k4-l3b-monitoring-llmops-v1
- **Khoảng thời gian điều tra:** 15:39:00Z – 15:40:00Z ngày 2026-09-30 (trong quá trình chạy load test challenge).
- **Triệu chứng từ metrics:** Panel Latency trên Dashboard ghi nhận P95 tăng vọt từ ~160ms lên hơn 2650ms cho feature `monitoring` (vượt ngưỡng cảnh báo 2000ms), tổng thời gian phản hồi client load test lên tới 7970ms – 13280ms.
- **Log line và correlation ID liên quan:** Log line: `{"event": "response_sent", "correlation_id": "req-82a2ac2b", "session_id": "k4-l3b-challenge-s02", "feature": "monitoring", "latency_ms": 2651, "level": "info", "ts": "2026-09-30T15:39:27.682362Z"}` (Correlation ID: `req-82a2ac2b`).
- **Trace ID và span gây ảnh hưởng:** Trace của request `req-82a2ac2b` trên Langfuse ghi nhận span `retrieval` chiếm ~2500ms / 2651ms tổng độ trễ.
- **Root cause:** Kịch bản sự cố `rag_slow` kích hoạt làm nghẽn bước truy xuất tài liệu vector store của feature `monitoring` thêm 2.5 giây.
- **Fix action:** Tắt sự cố bằng lệnh `uv run python scripts/inject_incident.py --disable`.
- **Preventive measure:** Thêm timeout 1s cho hàm retrieve, cấu hình Circuit Breaker với fallback context và bật cảnh báo `HighLatencyP95`.

> Gợi ý cách viết ngắn, không thay cho evidence thực tế: "Metric cho thấy `[latency/error/cost/quality]` bất thường trong `[khoảng thời gian]`. Log line `[event]` có `correlation_id=[...]` đại diện cho request bị ảnh hưởng. Trace cùng `correlation_id` cho thấy span `[retrieval/generation/prompt/tool]` có dấu hiệu `[chậm/lỗi/token tăng]`. Root cause là `[nguyên nhân suy ra từ evidence]`. Fix action là `[hành động khôi phục]`; preventive measure là `[alert/runbook/test/guardrail để ngăn tái diễn]`."

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** Đặt processor `scrub_event` trong chuỗi pipeline structlog ngay trước khi ghi file (`JsonlFileProcessor`) và render JSON. Lý do: Bảo vệ quyền riêng tư ngay tại tầng in-memory pipeline, triệt tiêu nguy cơ rò rỉ PII xuống ổ cứng.
- **Một lỗi/blocker đã gặp:** Cổng 8000 bị chiếm dụng bởi container Docker cũ từ trước (`[Errno 98] Address already in use`).
- **Cách tìm nguyên nhân và xử lý:** Kiểm tra cổng bằng `ss -tulpn | grep 8000`, nhận diện container chiếm cổng qua `docker ps` và dừng lại bằng `docker stop`.
- **Cách hiểu luồng Metrics → Logs → Traces:** Metrics cung cấp cái nhìn vĩ mô (triệu chứng gì, xảy ra khi nào); Logs giúp khoanh vùng vi mô (request cụ thể nào bị ảnh hưởng qua `correlation_id`); Traces mổ xẻ chi tiết nội tại request (span nào là thủ phạm gây nghẽn/lỗi).
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:** Đảm bảo hệ thống AI có khả năng triển khai liên tục an toàn (CI/CD), kiểm soát chi phí token minh bạch và phục hồi dịch vụ tức thì khi có biến cố.
- **Điều quan trọng nhất đã học:** Nắm vững tư duy vận hành hệ thống dựa trên bằng chứng kỹ thuật (evidence-based debugging) thay vì phỏng đoán.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:** Mô hình LLM trong lab là FakeLLM giả lập; nếu trên production cần gắn thêm streaming TTFT tracker và semantic evaluation.

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc commit SHA cuối.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [x] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
