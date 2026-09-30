# HƯỚNG DẪN CHI TIẾT TỪNG BƯỚC HOÀN THÀNH BÀI LAB K4-L3B (DAY 13: MONITORING & LLMOPS)

## 📌 1. TỔNG QUAN VÀ TRIẾT LÝ BÀI LAB

### 🎯 Mục tiêu bài lab
Mục tiêu cốt lõi của bài lab là chuyển đổi một ứng dụng AI API dạng **"Hộp đen" (Black-box)** thành một hệ thống có tính quan sát cao **(Observable System)**. Khi vận hành trên Production, ứng dụng LLM có thể gặp các lỗi vô hình (latency tăng đột biến, retrieval thất bại, LLM bị hallucination, chi phí bùng nổ,...). Bài lab giúp bạn thành thạo quy trình điều tra 4 bước chuẩn Observability:

$$\text{Metrics} \xrightarrow{\quad\text{Khoanh vùng thời gian}\quad} \text{Logs} \xrightarrow{\quad\text{Mã hóa request}\quad} \text{Traces} \xrightarrow{\quad\text{Phân tích Spans}\quad} \text{Root Cause}$$

1. **Metrics**: Cho biết hệ thống có triệu chứng gì bất thường (ví dụ: Latency P95 tăng, Error rate tăng, Cost bùng nổ) và khoảng thời gian diễn ra.
2. **Logs**: Giúp tìm chính xác dòng request bị ảnh hưởng bằng mã theo dõi duy nhất (`correlation_id`).
3. **Traces**: Cho biết request đó chậm/lỗi ở bước cụ thể nào trong cây thực thi (Span waterfall: Retrieval hay Generation).
4. **Root Cause**: Kết luận chính xác nguyên nhân gốc rễ dựa trên chuỗi bằng chứng hợp lệ, không đoán mò.

---

### 🔑 Các thuật ngữ quan trọng cần ghi nhớ

| Thuật ngữ | Ý nghĩa & Mục đích trong vận hành LLMOps |
|---|---|
| `correlation_id` | Mã định danh duy nhất cho 1 HTTP request (dạng `req-xxxxxxxx`). Giúp liên kết giữa Log hệ thống và Trace trên Langfuse. |
| **Structured Log (JSON)** | Ghi log dưới dạng JSON có cấu trúc thay vì plain text, cho phép máy và các công cụ giám sát truy vấn, tính toán dễ dàng. |
| **PII Scrubbing** | Tự động quét và che mờ thông tin cá nhân nhạy cảm (Email, SĐT Việt Nam, CCCD, Thẻ ngân hàng, Hộ chiếu) trước khi ghi log/trace để bảo vệ quyền riêng tư. |
| **Trace & Span** | **Trace** biểu diễn toàn bộ hành trình của một request; **Span** đại diện cho từng bước công việc nhỏ bên trong (Root span, Retrieval span, Generation span). |
| **Prompt Management** | Quản lý prompt độc lập với source code trên Cloud (Langfuse). Cho phép promote version mới hoặc rollback version cũ mà không cần sửa code. |
| **SLO & Error Budget** | **SLO (Service Level Objective)** là mục tiêu chất lượng dịch vụ (ví dụ: $99.5\%$ request thành công và $\le 3000\text{ms}$). **Error Budget** là số lượng request lỗi/chậm được phép trong cửa sổ thời gian. |
| **Symptom-based Alert** | Cảnh báo dựa trên triệu chứng trải nghiệm người dùng (Latency, Error Rate) thay vì lỗi linh kiện nội bộ. |

---

## 🚀 2. HƯỚNG DẪN CHI TIẾT TỪNG CHECKPOINT (CP0 → CP4)

> ⚠️ **QUY TẮC CỐT LÕI KHI LÀM BÀI:**
> - Giữ nguyên toàn bộ cấu trúc file, các comment `# TODO: ...`, comment hướng dẫn và docstring gốc của đề bài.
> - Code triển khai giải pháp được bổ sung ngay bên dưới hoặc thay thế đúng vị trí placeholder mà không làm mất đi các ghi chú ban đầu.

---

### ⚙️ CHECKPOINT 0 (CP0): CÀI ĐẶT MÔI TRƯỜNG & ĐÁNH GIÁ BASELINE

#### 📍 1. Mục đích & Vai trò
- Thiết lập môi trường ảo Python cô lập, cài đặt đúng phiên bản thư viện cần thiết.
- Kết nối ứng dụng cục bộ tới nền tảng giám sát LLMOps chuyên nghiệp (**Langfuse Cloud**) qua API Key cá nhân.
- Ghi nhận chỉ số đo lường ban đầu (**Baseline**) khi mã nguồn còn chứa các `TODO` chưa hoàn thiện. Điểm số baseline (khoảng `30/100`) là minh chứng đối chiếu quan trọng để chứng minh sự cải thiện sau khi hoàn thành lab.

---

#### 📝 2. Hướng dẫn các bước setting:

##### **Bước 0.1: Cài đặt môi trường bằng `uv` (Khuyên dùng)**
Repository sử dụng công cụ quản lý gói hiện đại `uv`. Chạy trên Terminal tại thư mục gốc repository:

```bash
# Tạo môi trường ảo với Python 3.12 và đồng bộ toàn bộ thư viện từ uv.lock
uv venv --python 3.12
uv sync
```
*(Nếu dùng môi trường truyền thống: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`)*.

##### **Bước 0.2: Cấu hình file môi trường `.env`**
Sao chép template cấu hình `.env.example` sang file cấu hình thực thi `.env`:

```bash
cp .env.example .env
```

##### **Bước 0.3: Tạo Project trên Langfuse Cloud và cấu hình Key**
1. Truy cập [Langfuse Cloud](https://cloud.langfuse.com) và đăng ký/đăng nhập.
2. Tạo một Project mới có tên: `day13-k4-l3b-<MSSV>` (ví dụ: `day13-k4-l3b-2A202602467`).
3. Vào **Project Settings → API Keys**, nhấn **Create new API keys**.
4. Mở file `.env` vừa tạo và điền cặp key cá nhân vào:

```dotenv
APP_ENV=dev
APP_NAME=day13-l3b-monitoring-llmops-lab
LOG_LEVEL=INFO
LOG_PATH=data/logs.jsonl
AUDIT_LOG_PATH=data/audit.jsonl

LANGFUSE_PUBLIC_KEY="pk-lf-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
LANGFUSE_SECRET_KEY="sk-lf-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
LANGFUSE_BASE_URL="https://us.cloud.langfuse.com" # hoặc https://cloud.langfuse.com tùy vùng tạo
LANGFUSE_PROMPT_NAME=day13-chat
LANGFUSE_PROMPT_LABEL=production
```

> ⚠️ **LƯU Ý BẢO MẬT:** Tuyệt đối không commit file `.env`, không dùng chung key với học viên khác và không chụp lộ Secret Key trong các ảnh evidence.

##### **Bước 0.4: Chạy API Server và đo điểm Baseline**
- **Terminal 1 (Khởi động Server FastAPI):**
  ```bash
  uv run uvicorn app.main:app --reload --env-file .env
  ```
  *(Lưu ý: Nếu gặp lỗi `[Errno 98] Address already in use`, nguyên nhân là cổng 8000 đang bị chiếm bởi một ứng dụng khác như container Docker. Dùng lệnh `docker ps` để tìm container và chạy `docker stop <container_id>` để giải phóng port 8000)*.

- **Terminal 2 (Gửi Workload và chạy các công cụ kiểm định):**
  ```bash
  uv run python scripts/load_test.py
  uv run python scripts/validate_logs.py
  uv run python scripts/validate_dashboard.py
  uv run python -m pytest -q
  ```

- **Ghi nhận kết quả Baseline:**
  - `load_test.py`: Trả về các dòng có correlation_id là `MISSING`.
  - `validate_logs.py`: Điểm đạt khoảng `30/100` (bị trừ điểm do thiếu `correlation_id`, thiếu log enrichment và các trường bắt buộc).
  - `validate_dashboard.py`: Đạt `HỢP LỆ: 6/6 panel`.
  - `pytest`: Pass 22/22 tests starter.
  - Điểm số này đã được lưu vào cột **Baseline** tại Mục 3 trong file `submission/REPORT.md`.

---

### 🛡️ CHECKPOINT 1 (CP1): CORRELATION ID, STRUCTURED LOGGING & PII SCRUBBING

#### 📍 1. Mục đích & Nguyên lý kỹ thuật
Hệ thống log truyền thống bằng văn bản thô (plain text) không thể phục vụ việc phân tích tự động trên quy mô lớn. Checkpoint 1 giải quyết 3 bài toán sống còn trong LLMOps:
1. **Truy vết đơn nhất (Correlation Propagation):** Mỗi request đến được cấp một mã `correlation_id` duy nhất (`req-xxxxxxxx`). Mã này phải tự động xuất hiện ở mọi dòng log trong toàn bộ vòng đời của request và được trả về client qua Response Header `x-request-id`.
2. **Làm giàu ngữ cảnh (Log Context Enrichment):** Mọi dòng log sinh ra trong endpoint phải tự động chứa các siêu dữ liệu quan trọng: `user_id_hash` (đã băm), `session_id`, `feature`, `model`, `env`.
3. **Bảo mật dữ liệu nhạy cảm (PII Redaction/Scrubbing):** Quét và che giấu thông tin cá nhân (Email, SĐT Việt Nam, CCCD, Thẻ ngân hàng, Hộ chiếu) ngay tại pipeline bộ nhớ trước khi log được ghi xuống ổ đĩa cứng hoặc hiển thị ra ngoài màn hình.

---

#### 🗺️ 2. Sơ đồ luồng dữ liệu (Data Flow):

```text
HTTP Request
     │
     ▼
[CorrelationIdMiddleware]
     ├─ 1. clear_contextvars() (Reset ngữ cảnh cũ)
     ├─ 2. Sinh/Lấy correlation_id (dạng req-<8-hex>)
     ├─ 3. bind_contextvars(correlation_id=...)
     └─ 4. Gọi tiếp handler (và ghi latency vào response header x-response-time-ms)
     │
     ▼
[Endpoint /chat trong app/main.py]
     ├─ 5. bind_contextvars(user_id_hash, session_id, feature, model, env)
     ├─ 6. log.info("request_received")
     ├─ 7. agent.run(...)
     └─ 8. log.info("response_sent") hoặc log.error("request_failed")
     │
     ▼
[Structlog Pipeline trong app/logging_config.py]
     ├─ merge_contextvars (Hợp nhất correlation_id & enrichment vào log dict)
     ├─ TimeStamper & add_log_level (Gắn ts chuẩn ISO UTC và level)
     ├─ scrub_event (🔥 Quét regex và thay thế PII bằng [REDACTED_...])
     ├─ JsonlFileProcessor (Ghi dòng JSON an toàn vào data/logs.jsonl)
     └─ JSONRenderer (Xuất JSON ra console)
```

---

#### 💻 3. Hướng dẫn chi tiết từng file code:

---

#### **Bước 1.1: File `app/pii.py` — Bộ lọc làm sạch dữ liệu cá nhân (PII)**

##### 🔍 **Vai trò của file:**
`app/pii.py` là module phụ trách Data Governance & Privacy. File này chứa các biểu thức chính quy (Regex) và các hàm tiện ích để phát hiện, che giấu PII và băm định danh người dùng.

##### ⚠️ **Vấn đề nếu chưa sửa:**
Trong code starter, danh sách `PII_PATTERNS` chỉ có email, phone_vn, cccd, credit_card và có comment `# TODO: Add more patterns (e.g., Passport, Vietnamese address keywords)`. Nếu người dùng gửi số hộ chiếu hoặc các định dạng nhạy cảm khác, hệ thống sẽ lưu nguyên văn bản thô vào log, gây rò rỉ dữ liệu (PII Leakage).

##### 💡 **Giải thích chi tiết từng hàm & từng dòng code:**
- **`PII_PATTERNS`**: Dictionary chứa các cặp `loại_pii: regex_pattern`.
  - `"email"`: `r"[\w\.-]+@[\w\.-]+\.\w+"` — nhận diện cấu trúc email chuẩn.
  - `"phone_vn"`: `r"(?<!\d)(?:\+84|0)(?:[ .-]?\d){9}(?!\d)"` — sử dụng negative lookbehind `(?<!\d)` và negative lookahead `(?!\d)` để đảm bảo bắt chính xác số điện thoại 10 chữ số (bắt đầu bằng `0` hoặc `+84`), không bắt nhầm các chuỗi số dài hơn.
  - `"cccd"`: `r"\b\d{12}\b"` — sử dụng ranh giới từ `\b` và 12 chữ số liên tiếp của Căn cước công dân Việt Nam.
  - `"credit_card"`: `r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b"` — bắt 16 chữ số thẻ ATM/Visa chia thành 4 cụm.
  - **`"passport"` (TODO đã bổ sung):** `r"\b[A-Z][0-9]{7,8}\b"` — định dạng hộ chiếu phổ thông (1 chữ cái in hoa đứng đầu theo sau là 7 hoặc 8 chữ số).
- **`scrub_text(text: str) -> str`**: Duyệt qua từng pattern, dùng hàm `re.sub()` thay thế mọi chuỗi trùng khớp bằng nhãn định dạng an toàn `[REDACTED_<NAME>]` (ví dụ: `[REDACTED_EMAIL]`, `[REDACTED_PASSPORT]`).
- **`summarize_text(text: str, max_len: int = 80) -> str`**: Gọi `scrub_text` trước tiên để khử sạch PII, sau đó xóa khoảng trắng thừa/dòng mới và cắt ngắn tối đa 80 ký tự kèm `...` để hiển thị trong preview của log mà không làm phình kích thước log.
- **`hash_user_id(user_id: str) -> str`**: Băm định danh người dùng bằng thuật toán mật mã học `SHA-256`, lấy 12 ký tự hex đầu. Giúp nhận diện cùng một user giữa các session khác nhau mà không bao giờ lưu trữ ID nguyên bản (kỹ thuật Pseudonymization).

##### 📄 **Source code hoàn chỉnh của `app/pii.py`:**

```python
from __future__ import annotations

import hashlib
import re

PII_PATTERNS: dict[str, str] = {
    "email": r"[\w\.-]+@[\w\.-]+\.\w+",
    "phone_vn": r"(?<!\d)(?:\+84|0)(?:[ .-]?\d){9}(?!\d)",
    "cccd": r"\b\d{12}\b",
    "credit_card": r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
    # TODO: Add more patterns (e.g., Passport, Vietnamese address keywords)
    "passport": r"\b[A-Z][0-9]{7,8}\b",
}


def scrub_text(text: str) -> str:
    safe = text
    for name, pattern in PII_PATTERNS.items():
        safe = re.sub(pattern, f"[REDACTED_{name.upper()}]", safe)
    return safe


def summarize_text(text: str, max_len: int = 80) -> str:
    safe = scrub_text(text).strip().replace("\n", " ")
    return safe[:max_len] + ("..." if len(safe) > max_len else "")


def hash_user_id(user_id: str) -> str:
    return hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:12]
```

---

#### **Bước 1.2: File `app/logging_config.py` — Cấu hình Pipeline Structlog**

##### 🔍 **Vai trò của file:**
`app/logging_config.py` định nghĩa pipeline xử lý chuỗi các bộ xử lý log (processors) của thư viện `structlog` trước khi ghi ra file `data/logs.jsonl` hoặc console.

##### ⚠️ **Vấn đề nếu chưa sửa:**
Tại dòng 45-46 có comment:
```python
# TODO: Register your PII scrubbing processor here
# scrub_event,
```
Vì hàm `scrub_event` bị comment lại, nên pipeline của structlog sẽ bỏ qua bước làm sạch PII. Hậu quả là mọi thông tin người dùng gửi lên sẽ đi thẳng vào file `data/logs.jsonl` ở dạng rõ (raw), khiến bài test `validate_logs.py` bị trừ 30 điểm và vi phạm tiêu chuẩn bảo mật.

##### 💡 **Giải thích chi tiết từng hàm & từng dòng code:**
- **`JsonlFileProcessor`**: Processor tự định nghĩa nhận vào dictionary sự kiện `event_dict`, render thành chuỗi JSON và ghi nối tiếp (`append`) xuống file `data/logs.jsonl`.
- **`scrub_event(_: Any, __: str, event_dict: dict[str, Any]) -> dict[str, Any]`**: Duyệt qua trường `payload` (nếu là dict) và trường `event` (nếu là str) để gọi `scrub_text()`. Mọi trường con trong `payload` đều được làm sạch trước khi trả lại `event_dict`.
- **`configure_logging()`**:
  - `merge_contextvars`: Hợp nhất các biến ngữ cảnh được gán từ `bind_contextvars()` vào bản ghi log.
  - `structlog.processors.add_log_level`: Bổ sung trường `"level": "info"` hoặc `"error"`.
  - `structlog.processors.TimeStamper(fmt="iso", utc=True, key="ts")`: Tạo trường `"ts"` chứa timestamp chuẩn quốc tế ISO 8601 UTC (ví dụ: `2026-09-30T03:29:30.493983Z`).
  - **`scrub_event` (TODO đã kích hoạt):** Đặt ở vị trí quan trọng: **SAU** khi đã có đủ thông tin ngữ cảnh nhưng **TRƯỚC** khi `JsonlFileProcessor` ghi xuống ổ đĩa.
  - `JsonlFileProcessor()`: Ghi log sạch vào file jsonl.
  - `structlog.processors.JSONRenderer()`: Định dạng JSON cuối cùng cho console stdout.

##### 📄 **Source code hoàn chỉnh của `app/logging_config.py`:**

```python
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import structlog
from structlog.contextvars import merge_contextvars

from .pii import scrub_text

LOG_PATH = Path(os.getenv("LOG_PATH", "data/logs.jsonl"))


class JsonlFileProcessor:
    def __call__(self, logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        rendered = structlog.processors.JSONRenderer()(logger, method_name, event_dict)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(rendered + "\n")
        return event_dict


def scrub_event(_: Any, __: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    payload = event_dict.get("payload")
    if isinstance(payload, dict):
        event_dict["payload"] = {
            k: scrub_text(v) if isinstance(v, str) else v for k, v in payload.items()
        }
    if "event" in event_dict and isinstance(event_dict["event"], str):
        event_dict["event"] = scrub_text(event_dict["event"])
    return event_dict


def configure_logging() -> None:
    logging.basicConfig(format="%(message)s", level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")))
    structlog.configure(
        processors=[
            merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True, key="ts"),
            # TODO: Register your PII scrubbing processor here
            scrub_event,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            JsonlFileProcessor(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )


def get_logger() -> structlog.typing.FilteringBoundLogger:
    return structlog.get_logger()
```

---

#### **Bước 1.3: File `app/middleware.py` — Bắt chặn & Lan truyền Correlation ID**

##### 🔍 **Vai trò của file:**
Middleware là trạm gác cổng (intercepting filter) của FastAPI. Mọi request trước khi vào endpoint `/chat` đều phải đi qua `CorrelationIdMiddleware.dispatch()`, và mọi response trước khi trả về cho client cũng đi qua đây.

##### ⚠️ **Vấn đề nếu chưa sửa:**
Trong code starter:
- `clear_contextvars()` bị comment: Dẫn đến biến ngữ cảnh của request A có thể bị rò rỉ sang request B khi luồng coroutine được tái sử dụng trên Event Loop.
- `correlation_id = "MISSING"`: Tất cả các request đều có mã là chữ "MISSING", khiến các công cụ giám sát không thể phân biệt hay liên kết giữa các dòng log.
- `bind_contextvars()` bị comment: Khiến log không có trường `correlation_id`.
- Response header chưa gán `x-request-id` và `x-response-time-ms`.

##### 💡 **Giải thích chi tiết 4 TODOs:**
1. **TODO 1: `clear_contextvars()`**: Gọi đầu tiên để dọn dẹp mọi giá trị còn sót lại trong contextvars của tiến trình, đảm bảo tính cô lập tuyệt đối giữa các request đồng thời.
2. **TODO 2: Lấy hoặc sinh `correlation_id`**: Kiểm tra header `x-request-id` của request. Nếu client hoặc API Gateway đã truyền mã (và khác chuỗi `"MISSING"`), ta tái sử dụng để duy trì dấu vết phân tán (Distributed Tracing). Nếu chưa có, sinh mã mới bằng UUIDv4 lấy 8 ký tự hex: `f"req-{uuid.uuid4().hex[:8]}"` (ví dụ: `req-7f3b8a1c`).
3. **TODO 3: `bind_contextvars(correlation_id=correlation_id)`**: Đưa `correlation_id` vào structlog contextvars. Kể từ dòng này, mọi câu lệnh log ở bất kỳ tầng nào trong request đều tự động mang `correlation_id` này mà không cần truyền tay tham số. Gán thêm vào `request.state.correlation_id` để router có thể lấy giá trị trả về trong JSON body của `ChatResponse`.
4. **TODO 4: Gán Response Headers**: Sau khi `await call_next(request)` hoàn thành, tính khoảng thời gian bằng `duration_ms = int((time.perf_counter() - start) * 1000)` và gán vào 2 header:
   - `response.headers["x-request-id"] = correlation_id` (cho phép client biết request ID để tra cứu).
   - `response.headers["x-response-time-ms"] = str(duration_ms)` (cho phép đo latency từ phía client/gateway).

##### 📄 **Source code hoàn chỉnh của `app/middleware.py`:**

```python
from __future__ import annotations

import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from structlog.contextvars import bind_contextvars, clear_contextvars


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # TODO: Clear contextvars to avoid leakage between requests
        clear_contextvars()

        # TODO: Extract x-request-id from headers or generate a new one
        # Use format: req-<8-char-hex>
        header_id = request.headers.get("x-request-id")
        if header_id and header_id != "MISSING":
            correlation_id = header_id
        else:
            correlation_id = f"req-{uuid.uuid4().hex[:8]}"

        # TODO: Bind the correlation_id to structlog contextvars
        bind_contextvars(correlation_id=correlation_id)

        request.state.correlation_id = correlation_id

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = int((time.perf_counter() - start) * 1000)

        # TODO: Add the correlation_id and processing time to response headers
        response.headers["x-request-id"] = correlation_id
        response.headers["x-response-time-ms"] = str(duration_ms)

        return response
```

---

#### **Bước 1.4: File `app/main.py` — Bổ sung Ngữ cảnh Request (Log Enrichment)**

##### 🔍 **Vai trò của file:**
`app/main.py` là entrypoint chứa định nghĩa ứng dụng FastAPI, đăng ký middleware và endpoint chính `@app.post("/chat")`.

##### ⚠️ **Vấn đề nếu chưa sửa:**
Trong hàm `chat()`, comment `# TODO: Enrich logs with request context (user_id_hash, session_id, feature, model, env)` chưa được code. Do đó, các dòng log phát sinh trong endpoint (như `request_received`, `response_sent`) chỉ có thông tin tối thiểu mà thiếu đi các trường ngữ cảnh kinh doanh (kinh nghiệm người dùng, model nào xử lý, tính năng nào được gọi). Script `validate_logs.py` sẽ phạt 20 điểm vì thiếu enrichment fields.

##### 💡 **Giải thích chi tiết đoạn code bổ sung:**
- Khi request vào endpoint `/chat`, ta gọi `bind_contextvars(...)` với 5 tham số:
  - `user_id_hash=hash_user_id(body.user_id)`: Không lưu trực tiếp user_id thô mà băm lấy 12 ký tự hex bảo mật.
  - `session_id=body.session_id`: Nhóm các lượt hội thoại trong cùng một phiên chat.
  - `feature=body.feature`: Nhận diện nghiệp vụ (ví dụ: `qa`, `summary`, `refund`, `monitoring`).
  - `model=agent.model`: Tên model LLM đang cấu hình cho agent (ví dụ: `claude-sonnet-4-5`).
  - `env=os.getenv("APP_ENV", "dev")`: Môi trường triển khai (`dev`, `staging`, `prod`).
- Nhờ lệnh `bind_contextvars` này, tất cả các sự kiện `request_received`, `response_sent` hoặc `request_failed` phát sinh trong endpoint đều tự động mang đầy đủ 5 trường trên.

##### 📄 **Source code hoàn chỉnh của `app/main.py`:**

```python
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from structlog.contextvars import bind_contextvars

from .agent import LabAgent
from .incidents import disable, enable, status
from .logging_config import configure_logging, get_logger
from .metrics import record_error, snapshot
from .middleware import CorrelationIdMiddleware
from .pii import hash_user_id, summarize_text
from .schemas import ChatRequest, ChatResponse
from .tracing import tracing_enabled

configure_logging()
log = get_logger()
agent = LabAgent()


@asynccontextmanager
async def lifespan(_: FastAPI):
    log.info(
        "app_started",
        service=os.getenv("APP_NAME", "day13-monitoring-llmops-lab"),
        env=os.getenv("APP_ENV", "dev"),
        payload={"tracing_enabled": tracing_enabled()},
    )
    yield


app = FastAPI(title="Day 13 Monitoring & LLMOps Lab", lifespan=lifespan)
app.add_middleware(CorrelationIdMiddleware)


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "tracing_enabled": tracing_enabled(), "incidents": status()}


@app.get("/metrics")
async def metrics() -> dict:
    return snapshot()


@app.post("/chat", response_model=ChatResponse)
async def chat(request: Request, body: ChatRequest) -> ChatResponse:
    # TODO: Enrich logs with request context (user_id_hash, session_id, feature, model, env)
    bind_contextvars(
        user_id_hash=hash_user_id(body.user_id),
        session_id=body.session_id,
        feature=body.feature,
        model=agent.model,
        env=os.getenv("APP_ENV", "dev"),
    )

    log.info(
        "request_received",
        service="api",
        payload={"message_preview": summarize_text(body.message)},
    )
    try:
        result = agent.run(
            user_id=body.user_id,
            feature=body.feature,
            session_id=body.session_id,
            message=body.message,
            correlation_id=request.state.correlation_id,
        )
        log.info(
            "response_sent",
            service="api",
            latency_ms=result.latency_ms,
            ttft_ms=result.ttft_ms,
            tokens_in=result.tokens_in,
            tokens_out=result.tokens_out,
            cost_usd=result.cost_usd,
            quality_score=result.quality_score,
            tool_name="retrieval",
            tool_success=True,
            payload={"answer_preview": summarize_text(result.answer)},
        )
        return ChatResponse(
            answer=result.answer,
            correlation_id=request.state.correlation_id,
            latency_ms=result.latency_ms,
            ttft_ms=result.ttft_ms,
            tokens_in=result.tokens_in,
            tokens_out=result.tokens_out,
            cost_usd=result.cost_usd,
            quality_score=result.quality_score,
        )
    except Exception as exc:  # pragma: no cover
        error_type = type(exc).__name__
        record_error(error_type)
        log.error(
            "request_failed",
            service="api",
            error_type=error_type,
            tool_name="retrieval" if isinstance(exc, RuntimeError) else None,
            tool_success=False if isinstance(exc, RuntimeError) else None,
            payload={"detail": str(exc), "message_preview": summarize_text(body.message)},
        )
        raise HTTPException(status_code=500, detail=error_type) from exc


@app.post("/incidents/{name}/enable")
async def enable_incident(name: str) -> JSONResponse:
    try:
        enable(name)
        log.warning("incident_enabled", service="control", payload={"name": name})
        return JSONResponse({"ok": True, "incidents": status()})
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/incidents/{name}/disable")
async def disable_incident(name: str) -> JSONResponse:
    try:
        disable(name)
        log.warning("incident_disabled", service="control", payload={"name": name})
        return JSONResponse({"ok": True, "incidents": status()})
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
```

---

#### 🧪 4. Kiểm thử và chụp Evidence của Checkpoint 1:

Sau khi đã hoàn thiện 4 file trên (`app/pii.py`, `app/logging_config.py`, `app/middleware.py`, `app/main.py`), hãy tiến hành kiểm thử và chụp 3 evidence đầu tiên của bài lab:

##### **1. Chạy validator và chụp `evidence/02-log-validator.png`:**
1. Xóa file log cũ chứa dữ liệu baseline chưa đạt:
   ```bash
   rm -f data/logs.jsonl
   ```
2. Đảm bảo server uvicorn đang chạy trên Terminal 1 (`uv run uvicorn app.main:app --reload --env-file .env`), sau đó trên Terminal 2 chạy:
   ```bash
   uv run python scripts/load_test.py
   uv run python scripts/validate_logs.py
   ```
3. **Mục tiêu đạt được:** Điểm số đạt **100/100** (tối thiểu 80/100):
   ```text
   --- Lab Verification Results ---
   Total log records analyzed: 20
   Records with missing required fields: 0
   Records with missing enrichment (context): 0
   Unique correlation IDs found: 10
   Potential PII leaks detected: 0

   --- Grading Scorecard (Estimates) ---
   + [PASSED] Basic JSON schema
   + [PASSED] Correlation ID propagation
   + [PASSED] Log enrichment
   + [PASSED] PII scrubbing

   Estimated Score: 100/100
   ```
4. **Chụp ảnh:** Chụp terminal hiển thị khối **Grading Scorecard** và **Estimated Score: 100/100** $\to$ Lưu vào `submission/evidence/02-log-validator.png`.

---

##### **2. Tạo và chụp `evidence/04-structured-log.png`:**
Gửi một request với correlation ID tự đặt (ví dụ: `req-1a2b3c4d`) và in ra 2 khối JSON log có cấu trúc:

1. Chạy lệnh gửi request:
   ```bash
   uv run python -c "import httpx; r = httpx.post('http://127.0.0.1:8000/chat', json={'user_id':'demo','session_id':'demo-01','feature':'qa','message':'Explain traces'}, headers={'x-request-id':'req-1a2b3c4d'}); print(r.status_code, r.headers.get('x-request-id'), r.headers.get('x-response-time-ms'))"
   ```
2. Chạy lệnh in formatted JSON log của request vừa gửi:
   ```bash
   uv run python -c "import json,sys; [print(json.dumps(json.loads(l), ensure_ascii=False, indent=2)) for l in open('data/logs.jsonl', encoding='utf-8') if sys.argv[1] in l]" req-1a2b3c4d
   ```
3. **Chụp ảnh:** Màn hình terminal hiển thị cả dòng lệnh và **2 khối JSON** (`request_received` + `response_sent`), thấy rõ các trường: `ts`, `event`, `correlation_id` (`req-1a2b3c4d`), `user_id_hash`, `session_id`, `feature`, `model`, `env`, `latency_ms` $\to$ Lưu vào `submission/evidence/04-structured-log.png`.
*(Lưu ý: Nhớ ghi lại mã correlation ID này để kiểm tra chéo với trace ở CP2)*.

---

##### **3. Tạo và chụp `evidence/05-pii-redaction.png`:**
Gửi một request chứa chuỗi dữ liệu nhạy cảm PII thô (email, SĐT, CCCD, thẻ ngân hàng):

1. Chạy lệnh gửi request với nội dung chứa PII:
   ```bash
   uv run python -c "import httpx; r = httpx.post('http://127.0.0.1:8000/chat', json={'user_id':'demo','session_id':'demo-01','feature':'qa','message':'a@b.vn 0901234567 001099012345 4111 1111 1111 1111'}, headers={'x-request-id':'req-pii-test'}); print(r.status_code, r.headers.get('x-request-id'))"
   ```
   *(Lưu ý: Chuỗi tin nhắn phải ngắn gọn vì hàm preview sẽ cắt tại 80 ký tự)*.
2. Chạy lệnh in log của request PII:
   ```bash
   uv run python -c "import json,sys; [print(json.dumps(json.loads(l), ensure_ascii=False, indent=2)) for l in open('data/logs.jsonl', encoding='utf-8') if sys.argv[1] in l]" req-pii-test
   ```
3. **Chụp ảnh:** Màn hình terminal hiển thị dòng lệnh có PII thô và khối log đầu ra đã được che sạch hoàn toàn thành: `[REDACTED_EMAIL]`, `[REDACTED_PHONE_VN]`, `[REDACTED_CCCD]`, `[REDACTED_CREDIT_CARD]` $\to$ Lưu vào `submission/evidence/05-pii-redaction.png`.

---

### 🔍 CHECKPOINT 2 (CP2): TRACING, PROMPT MANAGEMENT & DASHBOARD/ALERTS

#### 📍 1. Mục đích & Nguyên lý kỹ thuật
Một request AI thường là một chuỗi xử lý phức tạp (Chain/Graph): từ kiểm tra bộ nhớ, tìm kiếm tài liệu liên quan (RAG Retrieval), định dạng prompt theo template, đến gọi LLM sinh văn bản (Generation). Nếu chỉ đo tổng thời gian (ví dụ: 3000ms), bạn không thể biết hệ thống bị nghẽn ở bước nào.
- **Child Observations (Spans Tree):** Chia nhỏ vết thực thi thành cây quan sát phân cấp. Root Trace chứa thông tin toàn cục; Retrieval Span đo lường bước RAG; Generation Span đo lường lời gọi LLM (tokens, cost, prompt version).
- **Prompt Management & Rollback:** Tách rời prompt template khỏi code. Lưu trữ prompt tập trung trên Langfuse với các nhãn (`production`, `baseline`, `candidate`) để cho phép thử nghiệm prompt mới hoặc rollback tức thì khi phát hiện suy giảm chất lượng mà không cần build hay redeploy ứng dụng.
- **Dashboard & Alerts:** Trực quan hóa dữ liệu vận hành theo hợp đồng 6 panel chuẩn và thiết lập cảnh báo triệu chứng kèm quy trình xử lý sự cố (Runbook).

---

#### 🗺️ 2. Sơ đồ cây Trace phân cấp (Trace Observation Tree):

```text
Trace: day13-agent-request (Root Context: user_id_hash, session_id, correlation_id)
 └── Agent Observation: lab-agent-run
      ├── [Span 1]: retrieval (as_type="retriever")
      │     ├── Input: {"query": "..."}
      │     └── Output: {"docs_count": 1}
      │
      ├── [Prompt Resolution]: resolve_prompt() -> Version, Label, Name
      │
      └── [Span 2]: generation (as_type="generation")
            ├── Model: claude-sonnet-4-5
            ├── Input: {"prompt": "..."}
            ├── Output: {"answer_preview": "..."}
            └── Usage: {"input_tokens": 120, "output_tokens": 95}
```

---

#### 💻 3. Hướng dẫn chi tiết từng file code & thao tác UI:

---

#### **Bước 2.1: File `app/agent.py` — Đo lường Child Observations (Spans)**

##### 🔍 **Vai trò của file:**
`app/agent.py` là bộ não điều phối (`LabAgent`). Lớp này thực thi tuần tự việc tìm kiếm tài liệu liên quan qua `retrieve()` và gọi mô hình `FakeLLM.generate()`.

##### ⚠️ **Vấn đề nếu chưa sửa:**
Tại dòng 74-75:
```python
# TODO (CP2): instrument retrieve() and FakeLLM.generate() as child
# observations. The nested generation must receive prompt, usage and cost.
```
Hiện tại cả bước `retrieve` và `FakeLLM.generate` chạy mà không có span con riêng biệt trên Langfuse. Trên giao diện Langfuse, bạn chỉ thấy một khối `lab-agent-run` duy nhất, không biết RAG tốn bao nhiêu giây và LLM tốn bao nhiêu giây.

##### 💡 **Giải thích chi tiết giải pháp kỹ thuật:**
1. **Helper `_safe_observation`**:
   - Khi chạy thực tế trên Langfuse Cloud, SDK Langfuse v4 cung cấp context manager `langfuse_client.start_as_current_observation(...)`.
   - Tuy nhiên, trong unit test `tests/test_agent_prompt_trace.py`, client được mock bằng `RecordingLangfuseClient` (chỉ có hàm `update_current_span`, không có hàm `start_as_current_observation`).
   - Nếu gọi thẳng `langfuse_client.start_as_current_observation(...)`, lệnh `pytest` sẽ vỡ ngay lập tức do lỗi `AttributeError`!
   - Vì vậy, ta định nghĩa helper `@contextmanager def _safe_observation(client, **kwargs)`: kiểm tra xem client có method này hay không. Nếu có thì yield observation span; nếu không thì yield `None`. Cách này đảm bảo **vừa trace chuẩn trên Cloud thật, vừa pass 100% toàn bộ unit tests**.
2. **Span `retrieval`**:
   - Khởi tạo với `name="retrieval"`, `as_type="retriever"`.
   - `input`: Lưu query câu hỏi đã được làm sạch PII qua `summarize_text(message)`.
   - `output`: Cập nhật số lượng tài liệu tìm thấy `retrieval_obs.update(output={"docs_count": len(docs)})`.
3. **Span `generation`**:
   - Sử dụng `with propagate_attributes(prompt=prompt.managed_prompt)` để liên kết trace observation trực tiếp với Prompt Entity trên Langfuse.
   - Khởi tạo observation với `name="generation"`, `as_type="generation"`, `model=self.model`.
   - `usage`: Cập nhật số token input và token output từ response của LLM. Nhờ đó, Langfuse tự động tính toán chi phí USD cho từng request.

##### 📄 **Source code hoàn chỉnh của `app/agent.py`:**

```python
from __future__ import annotations

import os
import time
from contextlib import contextmanager
from dataclasses import dataclass

from . import metrics
from .mock_llm import FakeLLM
from .mock_rag import retrieve
from .pii import hash_user_id, summarize_text
from .prompt_management import resolve_prompt
from .tracing import get_langfuse_client, observe, propagate_attributes, tracing_enabled


@dataclass
class AgentResult:
    answer: str
    latency_ms: int
    ttft_ms: int
    tokens_in: int
    tokens_out: int
    cost_usd: float
    quality_score: float


@contextmanager
def _safe_observation(client, **kwargs):
    """Bọc an toàn để tạo child observation khi client Langfuse hỗ trợ API v4."""
    if hasattr(client, "start_as_current_observation") and callable(client.start_as_current_observation):
        with client.start_as_current_observation(**kwargs) as obs:
            yield obs
    else:
        yield None


class LabAgent:
    def __init__(self, model: str = "claude-sonnet-4-5") -> None:
        self.model = model
        self.llm = FakeLLM(model=model)

    @observe(name="lab-agent-run", as_type="agent", capture_input=False, capture_output=False)
    def run(
        self,
        user_id: str,
        feature: str,
        session_id: str,
        message: str,
        correlation_id: str,
    ) -> AgentResult:
        langfuse_client = get_langfuse_client()
        with propagate_attributes(
            user_id=hash_user_id(user_id),
            session_id=session_id,
            tags=["lab", feature, self.model],
            trace_name="day13-agent-request",
            environment=os.getenv("APP_ENV", "dev"),
            metadata={
                "feature": feature,
                "model": self.model,
                "correlation_id": correlation_id,
            },
        ):
            started = time.perf_counter()

            # TODO (CP2): instrument retrieve() and FakeLLM.generate() as child
            # observations. The nested generation must receive prompt, usage and cost.
            with _safe_observation(
                langfuse_client,
                name="retrieval",
                as_type="retriever",
                input={"query": summarize_text(message)},
            ) as retrieval_obs:
                docs = retrieve(message)
                if retrieval_obs and hasattr(retrieval_obs, "update"):
                    retrieval_obs.update(output={"docs_count": len(docs)})

            prompt = resolve_prompt(
                langfuse_client,
                feature=feature,
                docs=docs,
                message=message,
                enabled=tracing_enabled(),
            )
            langfuse_client.update_current_span(
                metadata={
                    "doc_count": len(docs),
                    "query_preview": summarize_text(message),
                    "prompt_name": prompt.name,
                    "prompt_label": prompt.label,
                    "prompt_version": prompt.version,
                    "prompt_source": prompt.source,
                    "prompt_fetch_error": prompt.fetch_error or "",
                },
                version=prompt.version,
            )

            with propagate_attributes(prompt=prompt.managed_prompt):
                with _safe_observation(
                    langfuse_client,
                    name="generation",
                    as_type="generation",
                    model=self.model,
                    input={"prompt": summarize_text(prompt.text)},
                ) as gen_obs:
                    response = self.llm.generate(prompt.text)
                    if gen_obs and hasattr(gen_obs, "update"):
                        gen_obs.update(
                            output={"answer_preview": summarize_text(response.text)},
                            usage={
                                "input": response.usage.input_tokens,
                                "output": response.usage.output_tokens,
                            },
                        )

            quality_score = self._heuristic_quality(message, response.text, docs)
            latency_ms = int((time.perf_counter() - started) * 1000)
            cost_usd = self._estimate_cost(response.usage.input_tokens, response.usage.output_tokens)

        metrics.record_request(
            latency_ms=latency_ms,
            ttft_ms=response.ttft_ms,
            cost_usd=cost_usd,
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
            quality_score=quality_score,
        )

        return AgentResult(
            answer=response.text,
            latency_ms=latency_ms,
            ttft_ms=response.ttft_ms,
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
            cost_usd=cost_usd,
            quality_score=quality_score,
        )

    def _estimate_cost(self, tokens_in: int, tokens_out: int) -> float:
        input_cost = (tokens_in / 1_000_000) * 3
        output_cost = (tokens_out / 1_000_000) * 15
        return round(input_cost + output_cost, 6)

    def _heuristic_quality(self, question: str, answer: str, docs: list[str]) -> float:
        score = 0.5
        if docs:
            score += 0.2
        if len(answer) > 40:
            score += 0.1
        if question.lower().split()[0:1] and any(token in answer.lower() for token in question.lower().split()[:3]):
            score += 0.1
        if "[REDACTED" in answer:
            score -= 0.2
        return round(max(0.0, min(1.0, score)), 2)
```

---

#### **Bước 2.2: Thao tác Prompt Management & Rollback trên Langfuse UI**

1. Mở trang quản trị Langfuse Cloud, chọn đúng Project cá nhân `day13-k4-l3b-2A202602467`.
2. Vào menu **Prompts → Create New Prompt**:
   - **Name:** `day13-chat` (bắt buộc đúng tên theo cấu hình `LANGFUSE_PROMPT_NAME`).
   - **Type:** `Text`.
   - **Content (Version 1):**
     ```text
     Feature={{feature}}
     Docs={{docs}}
     Question={{message}}
     ```
   - **Gán Labels:** Tích chọn ô `Set the "production" label` khi tạo. Sau khi bấm **Create Prompt**, tại mục Labels của Version 1, gõ thêm nhãn **`baseline`** và nhấn **Enter**.
3. Tạo tiếp **Version 2** cho prompt `day13-chat`:
   - Bấm vào prompt `day13-chat`, chọn **Create new version** (hoặc nút `+`).
   - Chỉnh sửa nội dung prompt một chút (ví dụ thêm yêu cầu trả lời ngắn gọn):
     ```text
     Feature={{feature}}
     Context docs: {{docs}}
     User question: {{message}}
     Please answer concisely and accurately based on the context docs.
     ```
   - **Gán Label:** **KHÔNG** tích chọn ô `production` (để giữ `production` ở Version 1). Sau khi bấm Create/Save, tại mục Labels của Version 2, gõ nhãn **`candidate`** và nhấn **Enter**.
4. **Quy trình Promote và Rollback nhãn `production` & chuẩn bị Evidence:**
   - **Promote:** Trên UI Langfuse, tại Version 2, thêm nhãn `production` sang Version 2 (hoặc promote). Lúc này nhãn `production` trỏ tới Version 2 và app sẽ tự động nhận Version 2 cho các request mới mà không cần restart server.
   - **Rollback:** Khi cần quay về phiên bản cũ, chuyển nhãn `production` từ Version 2 quay trở lại Version 1 trên giao diện Langfuse.
   - **Bằng chứng cần chụp:** Quá trình này sẽ cung cấp bằng chứng cho `evidence/09-prompt-versions.png` (danh sách v1, v2 kèm nhãn `baseline`, `candidate`, `production`) và `evidence/10-prompt-rollback.png` (`10a` khi promote v2 và `10b` khi rollback v1). Chi tiết thao tác và lệnh kiểm tra được hướng dẫn tại Mục 4 bên dưới.

---

#### **Bước 2.3: File `config/alert_rules.yaml` — Cấu hình Cảnh báo Symptom-based**

##### 🔍 **Vai trò của file:**
File này định nghĩa các quy tắc kích hoạt cảnh báo (Alert Rules) khi các chỉ số đo lường (SLI) vượt ngưỡng cho phép trong khoảng thời gian nhất định (duration).

##### ⚠️ **Vấn đề nếu chưa sửa:**
Trong code starter, file này chứa các trường giữ chỗ `TODO_alert_1`, `TODO_alert_2`, `TODO_alert_3` và `severity: TODO`.

##### 💡 **Giải thích chi tiết 3 Alert Rules:**
1. **`HighLatencyP95` (Warning):**
   - Điều kiện: `p95(latency_ms) > 3000` duy trì trong `5m`.
   - Ý nghĩa: Cảnh báo khi 5% số lượng request chậm nhất có độ trễ vượt quá 3 giây. Đây là cảnh báo warning sớm để kỹ sư can thiệp trước khi vi phạm SLO.
2. **`HighErrorRate` (Critical):**
   - Điều kiện: `error_rate_pct > 2.0` duy trì trong `5m`.
   - Ý nghĩa: Cảnh báo khẩn cấp khi tỷ lệ lỗi vượt quá 2% (ngân sách lỗi SLO cho phép chỉ là 0.5%).
3. **`LowRetrievalSuccessRate` (Critical):**
   - Điều kiện: `retrieval_success_rate_pct < 90.0` duy trì trong `5m`.
   - Ý nghĩa: Cảnh báo bước truy xuất tài liệu RAG gặp sự cố (ví dụ vector database bị timeout hoặc sập), dẫn đến AI trả lời thiếu căn cứ ngữ cảnh.

##### 📄 **Source code hoàn chỉnh của `config/alert_rules.yaml`:**

```yaml
alerts:
  - name: HighLatencyP95
    severity: warning
    condition: p95(latency_ms) > 3000
    duration: 5m
    type: symptom-based
    channel: slack
    owner: student-2A202602467
    runbook: docs/alerts.md#alert-1

  - name: HighErrorRate
    severity: critical
    condition: error_rate_pct > 2.0
    duration: 5m
    type: symptom-based
    channel: slack
    owner: student-2A202602467
    runbook: docs/alerts.md#alert-2

  - name: LowRetrievalSuccessRate
    severity: critical
    condition: retrieval_success_rate_pct < 90.0
    duration: 5m
    type: symptom-based
    channel: slack
    owner: student-2A202602467
    runbook: docs/alerts.md#alert-3
```

---

#### **Bước 2.4: File `docs/alerts.md` — Sổ tay vận hành xử lý sự cố (Runbooks)**

##### 🔍 **Vai trò của file:**
Runbook là cẩm nang hướng dẫn cho kỹ sư trực hệ thống (On-call Engineer) biết chính xác cần làm gì khi có chuông báo động (Alert firing) reo lên. Một Runbook tốt phải nêu rõ: Triệu chứng, Mức độ ảnh hưởng, 3 bước kiểm tra đầu tiên theo quy trình Metrics → Logs → Traces, và Biện pháp khắc phục tạm thời (Mitigation).

##### 📄 **Source code hoàn chỉnh của `docs/alerts.md`:**

```markdown
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
```

---

#### 🧪 4. Hướng dẫn kiểm thử và chụp 7 Evidence của Checkpoint 2:

Sau khi hoàn thành code và cấu hình ở Checkpoint 2, tiến hành kiểm thử và thu thập 7 file evidence (`03`, `06`, `07`, `08a/08b`, `09`, `10a/10b`, `11`):

##### **1. Kiểm định Dashboard contract và chụp `evidence/03-dashboard-validator.png`:**
1. Chạy công cụ kiểm tra hợp đồng dashboard:
   ```bash
   uv run python scripts/validate_dashboard.py
   ```
2. **Mục tiêu đạt được:** Terminal xuất ra dòng thông báo:
   ```text
   HỢP LỆ: 6/6 panel có trong dashboard contract.
   ```
3. **Chụp ảnh:** Màn hình terminal hiển thị câu lệnh và kết quả hợp lệ $\to$ Lưu vào `submission/evidence/03-dashboard-validator.png`.

---

##### **2. Tạo Traffic và chụp danh sách Traces `evidence/06-trace-list.png`:**
1. Đảm bảo server uvicorn đang chạy trên Terminal 1, trên Terminal 2 chạy load test để sinh ra tối thiểu 10 traces trên Langfuse:
   ```bash
   uv run python scripts/load_test.py
   ```
2. Mở trình duyệt vào [Langfuse Cloud](https://cloud.langfuse.com), chọn đúng project cá nhân `day13-k4-l3b-2A202602467`, bấm menu **Tracing** ở cột trái.
3. **Yêu cầu ảnh chụp:**
   - Thấy rõ **Tên project cá nhân** (`day13-k4-l3b-2A202602467`) ở góc trên màn hình.
   - Thấy **Khoảng thời gian** (Time range).
   - Thấy danh sách **$\ge 10$ traces** có tên `day13-agent-request`.
   - **Cột Input và Output phải TRỐNG:** Đây là tiêu chí chấm điểm bảo mật PII bắt buộc (chứng minh decorator `@observe(..., capture_input=False, capture_output=False)` đã che mờ dữ liệu thô).
4. **Chụp ảnh:** Lưu vào `submission/evidence/06-trace-list.png`.

---

##### **3. Mở Trace và chụp Waterfall Tree `evidence/07-trace-waterfall.png`:**
1. Trên giao diện Langfuse Tracing, tìm và bấm mở đúng trace tương ứng với request đã gửi ở ảnh `04` (đối chiếu qua mã `correlation_id`, ví dụ `req-1a2b3c4d`).
2. Chọn góc nhìn **Timeline** (bật công tắc **Show labels**) hoặc góc nhìn **Tree**.
3. **Yêu cầu ảnh chụp:**
   - Cấu trúc phân cấp cha - con rõ ràng:
     ```text
     day13-agent-request (Root trace)
      └── lab-agent-run (Agent observation)
           ├── retrieval (Retriever span)
           └── generation (Generation span)
     ```
   - Mỗi observation/span có thanh thời gian latency riêng biệt.
4. **Chụp ảnh:** Lưu vào `submission/evidence/07-trace-waterfall.png`.

---

##### **4. Chụp chi tiết Metadata và Generation Span: `evidence/08-trace-metadata.png` (hoặc 08a & 08b):**
Trong cùng màn hình Trace ở ảnh 07, tiến hành chụp 2 vị trí quan trọng:
- **Ảnh 08a (`evidence/08a-trace-metadata-agent.png`):**
  - Bấm chọn span `lab-agent-run` $\to$ chọn tab **Metadata** ở bảng bên phải.
  - **Nội dung phải thấy:** `correlation_id` (trùng khớp với mã ở ảnh 04), `prompt_name: day13-chat`, `prompt_label: production` (hoặc `baseline`), `prompt_version: 1`, `prompt_source: langfuse`, `doc_count`.
- **Ảnh 08b (`evidence/08b-trace-metadata-generation.png`):**
  - Bấm chọn span con `generation`.
  - **Nội dung phải thấy:** `model: claude-sonnet-4-5`, Token usage (`input`, `output`), Chi phí `cost` (USD), Thẻ liên kết `Prompt: day13-chat - vN`. Cột Input/Output trống.
- **Chụp ảnh:** Lưu thành 2 file `08a-...png`, `08b-...png` hoặc ghép thành `submission/evidence/08-trace-metadata.png`.

---

##### **5. Chụp danh sách Prompt Versions trên Langfuse `evidence/09-prompt-versions.png`:**
1. Trên Langfuse Cloud, nhấp vào menu **Prompts** ở thanh điều hướng bên trái $\to$ bấm chọn prompt `day13-chat`.
2. **Yêu cầu ảnh chụp:**
   - Hiển thị danh sách các phiên bản: **Version 1** và **Version 2**.
   - Hiển thị các nhãn (Labels) đã gán: `baseline`, `candidate`, `production` (có thêm nhãn `latest` do Langfuse tự động gán cho version mới nhất là hoàn toàn bình thường).
   - ⚠️ *Lưu ý quan trọng:* Phải chụp tại trang **Prompts**, tuyệt đối không chụp nhầm trang Traces!
3. **Chụp ảnh:** Lưu vào `submission/evidence/09-prompt-versions.png`.

---

##### **6. Chụp Promote & Rollback Prompt `evidence/10-prompt-rollback.png` (hoặc 10a & 10b):**
Thực hiện chu trình đổi nhãn và lưu ảnh minh chứng:
- **Thao tác Promote & Ảnh 10a (`evidence/10a-prompt-promote.png`):**
  - Trên giao diện Prompt `day13-chat`, chuyển nhãn `production` sang Version 2.
  - Chụp màn hình trang Prompt hiển thị nhãn `production` đang nằm ở Version 2.
  - Gửi 1 request kiểm tra:
    ```bash
    uv run python -c "import httpx; r = httpx.post('http://127.0.0.1:8000/chat', json={'user_id':'test','session_id':'s-v2','feature':'qa','message':'Testing v2'}, headers={'x-request-id':'req-test-v2'}); print(r.status_code, r.headers.get('x-request-id'))"
    ```
  - Mở trace của `req-test-v2` trên Langfuse, sao chép **Trace ID** của request này để ghi vào Report (Mục 5).
- **Thao tác Rollback & Ảnh 10b (`evidence/10b-prompt-rollback.png`):**
  - Chuyển nhãn `production` quay trở lại Version 1 trên giao diện Langfuse.
  - Chụp màn hình trang Prompt hiển thị nhãn `production` đã quay về Version 1.
  - Gửi 1 request kiểm tra:
    ```bash
    uv run python -c "import httpx; r = httpx.post('http://127.0.0.1:8000/chat', json={'user_id':'test','session_id':'s-v1','feature':'qa','message':'Testing v1'}, headers={'x-request-id':'req-test-v1'}); print(r.status_code, r.headers.get('x-request-id'))"
    ```
  - Mở trace của `req-test-v1` trên Langfuse, sao chép **Trace ID** của request này để ghi vào Report (Mục 5).
- **Chụp ảnh:** Lưu thành 2 file `10a-...png`, `10b-...png` hoặc ghép thành `submission/evidence/10-prompt-rollback.png`.

---

##### **7. Mở Dashboard runtime và chụp đủ 6 Panel `evidence/11-dashboard-overview.png`:**
1. Mở giao diện Dashboard giám sát runtime (Streamlit, Gradio, Grafana, notebook hoặc script vẽ biểu đồ từ file `data/logs.jsonl`).
2. **Yêu cầu ảnh chụp:** Hiển thị đầy đủ **6 panel** theo hợp đồng `config/dashboard.yaml`:
   1. **Latency:** Đồ thị đường P50, P95, P99 và **TTFT P95** kèm đường ngưỡng SLO `3000ms`.
   2. **Traffic:** Số lượng request / tốc độ gọi theo phút (rate per minute).
   3. **Errors:** Tỷ lệ lỗi ($\le 2\%$) và **Retrieval success rate** ($\ge 90\%$).
   4. **Cost:** Tổng chi phí USD tích lũy over time.
   5. **Tokens:** Số lượng Input tokens và Output tokens.
   6. **Quality:** Điểm chất lượng trung bình Proxy ($\ge 0.75$).
   - Thấy rõ: Tên từng panel, đơn vị đo (ms, %, requests_per_minute, usd, count), đường ngưỡng threshold/SLO và khoảng thời gian (Time range: 60m).
3. **Chụp ảnh:** Lưu vào `submission/evidence/11-dashboard-overview.png` (nếu không chụp hết một màn hình, có thể tách thành `11a-...png` và `11b-...png`).

---

### 🚨 CHECKPOINT 3 (CP3): ĐIỀU TRA SỰ CỐ (INCIDENT INVESTIGATION)

#### 📍 1. Mục đích & Bối cảnh Sự cố (Challenge)
Trong bài lab này, repository đã có sẵn file `config/challenge.json` chính thức:
- **Challenge ID:** `day13-k4-l3b-monitoring-llmops-v1`
- **Sự cố được kích hoạt:** `rag_slow` (Mô phỏng bước tìm kiếm tài liệu RAG bị nghẽn làm chậm hệ thống).
- **Tính năng bị ảnh hưởng:** `monitoring`.
- **Ngưỡng cảnh báo Latency:** `2000ms`.

---

#### 🛠️ 2. Quy trình điều tra 4 bước chi tiết:

##### **Bước 3.1: Kích hoạt sự cố và đẩy Traffic**
Trên Terminal 2 (đảm bảo server uvicorn vẫn đang chạy ở Terminal 1):
```bash
# Kích hoạt sự cố challenge rag_slow
uv run python scripts/inject_incident.py

# Gửi các query chính thức của challenge với concurrency = 5
uv run python scripts/load_test.py --challenge --concurrency 5
```
Bạn sẽ thấy trên màn hình: các request của feature `monitoring` có độ trễ vọt lên $> 2500\text{ms}$ thay vì $\approx 370\text{ms}$ như bình thường!

##### **Bước 3.2: Điều tra theo chuỗi Metrics → Logs → Traces → Root Cause**

1. **Bước 1: Metrics (Dashboard)**
   - Mở giao diện Dashboard giám sát. Quan sát thấy panel **Latency**: đường chỉ số P95 tăng vọt từ $370\text{ms}$ lên $> 2500\text{ms}$ (vượt xa đường đỏ SLO 3000ms hoặc ngưỡng cảnh báo 2000ms).
   - *Bằng chứng:* Chụp ảnh đồ thị tăng vọt này và lưu vào `submission/evidence/12-incident-metric.png`.

2. **Bước 2: Logs (Lọc Correlation ID)**
   - Mở terminal hoặc file `data/logs.jsonl`, lọc các dòng có latency cao:
     ```bash
     tail -n 20 data/logs.jsonl
     ```
   - Nhìn vào dòng log sự kiện `response_sent`:
     ```json
     {"service": "api", "latency_ms": 2874, "ttft_ms": 52, "event": "response_sent", "correlation_id": "req-9a8b7c6d", "feature": "monitoring", ...}
     ```
   - Trích xuất mã `correlation_id` bị chậm: ví dụ `req-9a8b7c6d`.
   - *Bằng chứng:* Chụp ảnh dòng log chứa correlation_id này lưu vào `submission/evidence/13-incident-log.png`.

3. **Bước 3: Traces (Phân tích Span Waterfall trên Langfuse)**
   - Mở Langfuse UI, dán mã `req-9a8b7c6d` vào ô tìm kiếm Traces.
   - Nhấp vào Trace để mở biểu đồ thời gian dạng thác nước (**Waterfall Tree**):
     ```text
     day13-agent-request [2874ms]
     └── lab-agent-run [2874ms]
         ├── retrieval [2502ms] 👈 (THỦ PHẠM: Chiếm 87% toàn bộ độ trễ!)
         └── generation [155ms] (LLM sinh token bình thường, chỉ mất 155ms)
     ```
   - Xác định chính xác: Span `retrieval` bị nghẽn $2.5\text{s}$, trong khi `generation` hoàn toàn bình thường.
   - *Bằng chứng:* Chụp ảnh cây span waterfall này lưu vào `submission/evidence/14-incident-trace.png`.

4. **Bước 4: Root Cause, Fix Action & Phòng ngừa**
   - **Root Cause (Nguyên nhân gốc rễ):** Hàm `retrieve()` trong `app/mock_rag.py` gặp sự cố mô phỏng `rag_slow` gây trễ nhân tạo 2.5s khi tìm kiếm tài liệu cho từ khóa `monitoring`.
   - **Fix Action (Hành động khắc phục ngay):** Tắt sự cố mô phỏng:
     ```bash
     uv run python scripts/inject_incident.py --disable
     ```
   - **Preventive Measure (Biện pháp phòng ngừa lâu dài):** Bổ sung cơ chế timeout 1000ms cho bước gọi vector search, kích hoạt Circuit Breaker chuyển sang fallback context khi retrieval quá tải và thiết lập cảnh báo `HighLatencyP95`.

---

#### 🧪 3. Hướng dẫn kiểm thử và chụp 3 Evidence của Checkpoint 3:

Sau khi kích hoạt sự cố và điều tra theo chuỗi 4 bước, tiến hành thu thập 3 file evidence của incident (`12`, `13`, `14`):

##### **1. Mở Dashboard và chụp đồ thị sự cố `evidence/12-incident-metric.png`:**
1. Đảm bảo server uvicorn đang chạy trên Terminal 1. Trên Terminal 2 kích hoạt challenge và tạo traffic:
   ```bash
   uv run python scripts/inject_incident.py
   uv run python scripts/load_test.py --challenge --concurrency 5
   ```
2. Mở giao diện Dashboard giám sát runtime (Streamlit/Gradio/Grafana/Langfuse hoặc biểu đồ).
3. **Yêu cầu ảnh chụp:** Quan sát thấy rõ cả đoạn bình thường (baseline latency $\sim 370\text{ms}$) và đoạn bất thường tăng vọt ($> 2000\text{ms}$, lên tới $\sim 2800\text{ms}$) trên cùng một trục thời gian.
4. **Chụp ảnh:** Lưu vào `submission/evidence/12-incident-metric.png`.

---

##### **2. Lọc Log bất thường và chụp `evidence/13-incident-log.png`:**
1. Chạy lệnh one-liner để lọc ra danh sách các request bị chậm từ file `data/logs.jsonl`:
   ```bash
   uv run python -c "import json; rows=[json.loads(l) for l in open('data/logs.jsonl', encoding='utf-8')]; [print(r['ts'], r['correlation_id'], r['session_id'], r['latency_ms'], 'ms') for r in rows if r.get('event')=='response_sent' and r.get('latency_ms',0)>2000]"
   ```
   *(Nếu là kịch bản lỗi, chạy lệnh: `uv run python -c "import json; rows=[json.loads(l) for l in open('data/logs.jsonl', encoding='utf-8')]; [print(r['ts'], r['correlation_id'], r.get('session_id'), r.get('error_type'), r.get('tool_success')) for r in rows if r.get('event')=='request_failed']"`)*.
2. Chọn một mã `correlation_id` bất thường trong danh sách in ra (ví dụ: `req-9a8b7c6d`).
3. Chạy lệnh in định dạng JSON hoàn chỉnh của riêng request đó:
   ```bash
   uv run python -c "import json,sys; [print(json.dumps(json.loads(l), ensure_ascii=False, indent=2)) for l in open('data/logs.jsonl', encoding='utf-8') if sys.argv[1] in l]" req-9a8b7c6d
   ```
4. **Yêu cầu ảnh chụp:** Terminal hiển thị cả câu lệnh và khối JSON `response_sent` có `correlation_id`, timestamp giờ UTC, `feature: monitoring`, và giá trị độ trễ bất thường `latency_ms > 2000`.
5. **Chụp ảnh:** Lưu vào `submission/evidence/13-incident-log.png`.
   *(⚠️ Nhớ ghi lại mã `correlation_id` này để đối chiếu ở ảnh 14 và điền vào Mục 7 của `submission/REPORT.md`)*.

---

##### **3. Mở Trace trên Langfuse và chụp Waterfall Tree `evidence/14-incident-trace.png`:**
1. Mở [Langfuse Cloud](https://cloud.langfuse.com), vào menu **Tracing**.
2. Dán mã `correlation_id` từ ảnh 13 (ví dụ: `req-9a8b7c6d`) vào thanh tìm kiếm Traces.
3. Bấm mở Trace tương ứng, chọn chế độ xem Timeline hoặc Tree.
4. **Yêu cầu ảnh chụp:**
   - Cây phân cấp Waterfall thấy rõ span `retrieval` bị nghẽn kéo dài ($> 2500\text{ms}$, chiếm $\sim 87\%$ toàn bộ độ trễ), trong khi span `generation` hoàn toàn bình thường ($\sim 150\text{ms}$).
   - Tab Metadata hiển thị `correlation_id` trùng khớp 100% với ảnh 13.
5. **Chụp ảnh:** Lưu vào `submission/evidence/14-incident-trace.png`.
6. **Tắt kịch bản sự cố sau khi chụp xong:**
   ```bash
   uv run python scripts/inject_incident.py --disable
   ```

---

### 📊 CHECKPOINT 4 (CP4): BÁO CÁO, EVIDENCE VÀ NỘP BÀI

#### 📍 8.1. Báo cáo cá nhân
Điền đầy đủ mọi mục trong `submission/REPORT.md` (theo chuẩn `docs/SUBMISSION.md §8`): thông tin học viên, evidence index, bảng baseline và kết quả cuối, logging/PII, tracing/prompt (có 2 trace ID), dashboard/SLO/alert, điều tra challenge, quyết định kỹ thuật, blocker, bài học.
- Ảnh dẫn bằng đường dẫn tương đối, ví dụ: `![Trace waterfall](evidence/07-trace-waterfall.png)`.
- Tuyệt đối không dùng đường dẫn cục bộ máy tính như `C:\Users\...` hoặc `/home/lqaq/...`.

---

#### 📸 8.2. Hướng dẫn chụp Evidence chi tiết

Lưu ảnh `.png` (test/validator có thể dùng file `.txt`) vào thư mục `submission/evidence/`.

##### **Cách chụp màn hình:**
| Hệ điều hành | Phím tắt chụp một vùng màn hình |
|---|---|
| **Windows** | `Win + Shift + S` |
| **macOS** | `Cmd + Shift + 4` |
| **Ubuntu / Linux** | `Shift + PrtSc` |

##### **Quy tắc chung khi chụp evidence:**
- Ảnh terminal phải thấy: **Lệnh thực thi + Kết quả**.
- Ảnh Langfuse phải thấy: **Tên project (`day13-k4-l3b-2A202602467`) + Khoảng thời gian**.
- Chữ phải rõ ràng, đọc được số liệu.
- Tuyệt đối **không chụp lộ file `.env`**, trang API Keys hay Secret Key.

---

##### ⚡ **Hai lệnh one-liner để tạo & in log cho Evidence 04 và 05:**
Để lấy log của một request, gửi request có ID tự đặt (`req-` + 8 ký tự hex) rồi in định dạng JSON của nó. Hai lệnh này chạy được trên mọi terminal (thay `req-1a2b3c4d` bằng ID tùy chọn của bạn):

- **Lệnh 1 (Gửi request kèm correlation_id tự đặt):**
  ```bash
  uv run python -c "import httpx; r = httpx.post('http://127.0.0.1:8000/chat', json={'user_id':'demo','session_id':'demo-01','feature':'qa','message':'Explain traces'}, headers={'x-request-id':'req-1a2b3c4d'}); print(r.status_code, r.headers.get('x-request-id'), r.headers.get('x-response-time-ms'))"
  ```
- **Lệnh 2 (In formatted JSON log của request đó):**
  ```bash
  uv run python -c "import json,sys; [print(json.dumps(json.loads(l), ensure_ascii=False, indent=2)) for l in open('data/logs.jsonl', encoding='utf-8') if sys.argv[1] in l]" req-1a2b3c4d
  ```

---

##### 📋 **Bảng chi tiết 14 Evidence bắt buộc:**

| # | Tên file | Chụp ở đâu / Làm gì | Ảnh phải thấy rõ nội dung gì? |
|---|---|---|---|
| **01** | `01-pytest.png` | Sau commit code cuối: chạy `git log -1 --oneline` rồi `uv run python -m pytest -q` | Mã commit + `22 passed` (toàn bộ tests pass) |
| **02** | `02-log-validator.png` | Xóa/di chuyển log cũ ra ngoài repo → restart server → chạy `load_test.py` → chạy `validate_logs.py` | Khối **Grading Scorecard** + **Estimated Score ≥ 80** (mục tiêu 100/100) |
| **03** | `03-dashboard-validator.png` | Chạy lệnh `uv run python scripts/validate_dashboard.py` | Thông báo: `HỢP LỆ: 6/6 panel có trong dashboard contract.` |
| **04** | `04-structured-log.png` | Chạy 2 lệnh one-liner ở trên với ID tự đặt (ví dụ: `req-1a2b3c4d`) | **2 khối JSON**: `request_received` + `response_sent`, hiển thị đủ `ts`, `event`, `correlation_id`, `user_id_hash`, `session_id`, `feature`, `model`, `env`, `latency_ms`. *(Ghi mã ID này vào report)* |
| **05** | `05-pii-redaction.png` | Như lệnh 04 nhưng đổi `message` thành chuỗi PII: `a@b.vn 0901234567 001099012345 4111 1111 1111 1111` *(lưu ý: câu ngắn vì preview bị cắt ở 80 ký tự)* | Dòng lệnh có PII thô và khối log in ra hiển thị đã được thay bằng: `[REDACTED_EMAIL]`, `[REDACTED_PHONE_VN]`, `[REDACTED_CCCD]`, `[REDACTED_CREDIT_CARD]` |
| **06** | `06-trace-list.png` | Vào Langfuse UI → menu **Tracing** | Thấy **Tên project** (`day13-k4-l3b-2A202602467`), khoảng thời gian, danh sách **$\ge 10$ traces** `day13-agent-request`, **cột Input/Output phải trống** *(vì đã cấu hình không capture input/output để bảo mật PII)* |
| **07** | `07-trace-waterfall.png` | Mở trace của request ở ảnh 04 → chọn góc nhìn **Timeline** (bật *Show labels*) hoặc **Tree** | Cây phân cấp: `lab-agent-run` là cha của `retrieval` và `generation`, mỗi dòng có thanh thời gian latency riêng |
| **08** | `08-trace-metadata.png`<br>*(hoặc 08a & 08b)* | **08a:** bấm vào span `lab-agent-run` → chọn tab Metadata.<br>**08b:** bấm vào span `generation` | **08a:** `correlation_id` trùng khớp ảnh 04, `prompt_name/label/version`, `prompt_source=langfuse`.<br>**08b:** model (`claude-sonnet-4-5`), usage tokens, cost USD, nhãn `Prompt: day13-chat - vN`. Cột Input/Output trống |
| **09** | `09-prompt-versions.png` | Vào Langfuse UI → menu **Prompts** → chọn prompt `day13-chat` | Thấy đủ **Version 1** và **Version 2** kèm các nhãn `baseline`, `candidate`, `production` (có thêm `latest` là bình thường) |
| **10** | `10-prompt-rollback.png`<br>*(hoặc 10a & 10b)* | Chụp trang prompt sau khi promote (10a) và sau khi rollback (10b) | Nhãn `production` được chuyển sang v2 (10a), sau đó được chuyển quay trở về v1 (10b) |
| **11** | `11-dashboard-overview.png`<br>*(hoặc 11a/11b/11c)* | Mở Dashboard runtime, chụp đủ 6 panel | Tên panel, đơn vị, threshold, time range; panel latency có TTFT; panel errors có retrieval success rate |
| **12** | `12-incident-metric.png` | Mở Dashboard ngay sau khi chạy challenge | Đồ thị thể hiện rõ đoạn bình thường (baseline) và đoạn tăng vọt bất thường trên cùng trục thời gian |
| **13** | `13-incident-log.png` | Lọc request bất thường (dùng lệnh bên dưới), rồi in formatted log của 1 request bất thường bằng lệnh ở 04 | Dòng log có `correlation_id`, timestamp, giá trị độ trễ bất thường (`latency_ms > 2000`) |
| **14** | `14-incident-trace.png` | Trên Langfuse, tìm và mở trace có cùng `correlation_id` với ảnh 13 | Waterfall tree thấy rõ span `retrieval` bị chậm kéo dài (chiếm phần lớn thời gian) + metadata có `correlation_id` khớp log |

---

##### 🔍 **Lệnh lọc request bất thường phục vụ ảnh 13:**

- **Lọc request chậm (`latency_ms > 2000`):**
  ```bash
  uv run python -c "import json; rows=[json.loads(l) for l in open('data/logs.jsonl', encoding='utf-8')]; [print(r['ts'], r['correlation_id'], r['session_id'], r['latency_ms'], 'ms') for r in rows if r.get('event')=='response_sent' and r.get('latency_ms',0)>2000]"
  ```
- **Lọc request lỗi (`request_failed`):**
  ```bash
  uv run python -c "import json; rows=[json.loads(l) for l in open('data/logs.jsonl', encoding='utf-8')]; [print(r['ts'], r['correlation_id'], r.get('session_id'), r.get('error_type'), r.get('tool_success')) for r in rows if r.get('event')=='request_failed']"
  ```

---

#### ⚖️ 8.3. Bảng tự kiểm tra chéo (Cross-Validation Checklist)
Trước khi nộp, bạn bắt buộc phải đối chiếu chéo các thông tin giữa các ảnh để tránh bị trừ điểm lỗi không nhất quán:

| Tiêu chí kiểm tra | Cặp Evidence phải khớp nhau | Ý nghĩa kiểm chứng |
|---|---|---|
| **Cùng `correlation_id`** | Ảnh `04` ↔ Ảnh `08a`<br>Ảnh `13` ↔ Ảnh `14` ↔ Mục 7 trong Report | Chứng minh log và trace phản ánh chính xác cùng một request đơn nhất. |
| **Cùng trace** | Ảnh `07`, `08a`, `08b` là cùng một trace, và trace này phải nằm trong danh sách ở ảnh `06` | Chứng minh trace chi tiết thực sự nằm trong luồng chạy của project. |
| **Cùng thời điểm** | Giờ trong log là **UTC** (hậu tố `Z`); Langfuse hiển thị giờ địa phương Việt Nam (**UTC+7**).<br>*Ví dụ: `04:39Z` trong log = `11:39` trên giao diện Langfuse.* | Giảng viên sẽ đối chiếu thời gian để xác nhận tính xác thực. |
| **Cùng version** | 2 trace ID ghi trong Report phải có `prompt_version` tương ứng là 1 và 2 | Chứng minh đã chạy thử nghiệm cả 2 phiên bản prompt. |
| **Cùng người thực hiện** | Tên project `day13-k4-l3b-2A202602467` trên ảnh Langfuse khớp với MSSV trong Report và tên repo | Chống gian lận hoặc dùng ảnh của học viên khác. |
| **Cùng đề challenge** | `challenge_id` trong Report khớp đúng file `config/challenge.json` (`day13-k4-l3b-monitoring-llmops-v1`) | Chứng minh đã điều tra đúng đề thi của lớp. |

---

#### 🚀 8.4. Kiểm tra cuối cùng và lệnh nộp bài an toàn

Chạy chuỗi lệnh kiểm định trên commit cuối cùng:
```bash
uv run python -m pytest -q
uv run python scripts/validate_logs.py
uv run python scripts/validate_dashboard.py
git status --short
git log -1 --oneline
```

> ⚠️ **CẢNH BÁO BẢO MẬT KHI DÙNG GIT:**
> - **KHÔNG DÙNG** `git add .` vì rất dễ vô tình thêm file `.env`, file cấu hình sự cố `config/challenge.json`, file log `data/logs.jsonl` hoặc thư mục `.venv/`.
> - **CHỈ DÙNG** lệnh add cụ thể từng thư mục bài làm:
>   ```bash
>   git add app tests config docs submission
>   ```
> - Kiểm tra lại bằng `git status`: đảm bảo danh sách chuẩn bị commit **KHÔNG CÓ** `.env`, `challenge.json`, `.venv/` hay log thô chứa PII.

---

#### 📝 8.5. Nội dung mẫu điền hoàn chỉnh cho `submission/REPORT.md`:

```markdown
# Báo cáo cá nhân — K4-L3B Day 13 Monitoring & LLMOps

## 1. Thông tin học viên

- **Họ và tên:** Lâm Quang Anh Quân
- **MSSV:** 2A202602467
- **Lớp:** K4-L3B
- **Repository URL:** https://github.com/awun0105/K4-L3-DAY13-LamQuangAnhQuan-2A202602467-Monitoring-LLMOps.git
- **Commit SHA cuối:** (Chạy `git rev-parse HEAD` để lấy mã commit)
- **Challenge ID:** day13-k4-l3b-monitoring-llmops-v1
- **Tên project Langfuse cá nhân:** `day13-k4-l3b-2A202602467`

## 2. Evidence index

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
- **Trace ID của mỗi version:** (Dán 2 Trace ID cụ thể lấy từ giao diện Langfuse).
- **Cách promote và rollback `production`:** Trên Langfuse Prompts UI, chuyển nhãn `production` sang Version 2 để promote; khi phát hiện sự cố, chuyển nhãn `production` quay lại Version 1 trên giao diện mà không cần chỉnh sửa code hay restart server.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** 6 panel định nghĩa trong `config/dashboard.yaml` gồm: Latency (P50/P95/P99/TTFT), Traffic (req/min), Errors & Retrieval Success Rate, Tokens & Cost (USD), Quality Proxy, Prompt Versions Distribution.
- **SLO và lý do chọn:** Latency P95 <= 3000ms và Tỷ lệ thành công >= 99.5% trong cửa sổ 28 ngày. Lý do: Giữ trải nghiệm phản hồi mượt mà cho ứng dụng chat tương tác thời gian thực.
- **Cách tính error budget:** Với SLO 99.5%, ngân sách lỗi là 0.5%. Nếu hệ thống phục vụ 10,000 request thì tối đa 50 request được phép thất bại hoặc chậm hơn 3000ms.
- **Ba alert và runbook tương ứng:**
  1. `HighLatencyP95`: P95 latency > 3000ms kéo dài 5 phút (Runbook tại `docs/alerts.md#alert-1`).
  2. `HighErrorRate`: Error rate > 2.0% kéo dài 5 phút (Runbook tại `docs/alerts.md#alert-2`).
  3. `LowRetrievalSuccessRate`: RAG success rate < 90.0% kéo dài 5 phút (Runbook tại `docs/alerts.md#alert-3`).

## 7. Điều tra challenge

- **Challenge ID:** day13-k4-l3b-monitoring-llmops-v1
- **Khoảng thời gian điều tra:** Khoảng 10-15 phút trong quá trình chạy load test challenge.
- **Triệu chứng từ metrics:** Panel Latency trên Dashboard ghi nhận P95 tăng vọt từ ~370ms lên hơn 2800ms cho feature `monitoring`.
- **Log line và correlation ID liên quan:** `{"event": "response_sent", "correlation_id": "req-xxxxxxxx", "latency_ms": 2874, "feature": "monitoring"}`.
- **Trace ID và span gây ảnh hưởng:** Mở trace `req-xxxxxxxx` trên Langfuse, xác định Span `retrieval` chiếm 2502ms / 2874ms tổng độ trễ.
- **Root cause:** Kịch bản sự cố `rag_slow` kích hoạt làm nghẽn bước truy xuất tài liệu vector store của feature `monitoring` trong 2.5 giây.
- **Fix action:** Tắt sự cố bằng lệnh `uv run python scripts/inject_incident.py --disable`.
- **Preventive measure:** Thêm timeout 1s cho hàm retrieve, cấu hình Circuit Breaker với fallback context và bật cảnh báo `HighLatencyP95`.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** Đặt processor `scrub_event` trong pipeline structlog trước khi ghi file và render JSON. Lý do: Bảo vệ quyền riêng tư ngay tại tầng in-memory pipeline, triệt tiêu nguy cơ rò rỉ PII xuống ổ cứng.
- **Một lỗi/blocker đã gặp:** Cổng 8000 bị chiếm dụng bởi container Docker cũ từ trước (`[Errno 98] Address already in use`).
- **Cách tìm nguyên nhân và xử lý:** Kiểm tra cổng bằng `ss -tulpn | grep 8000`, nhận diện container `clip-image-retrieval-gradio-app-app-1` qua `docker ps` và dừng lại bằng `docker stop`.
- **Cách hiểu luồng Metrics → Logs → Traces:** Metrics cung cấp cái nhìn vĩ mô (triệu chứng gì, xảy ra khi nào); Logs giúp khoanh vùng vi mô (request cụ thể nào bị ảnh hưởng qua correlation_id); Traces mổ xẻ chi tiết nội tại request (span nào là thủ phạm gây nghẽn/lỗi).
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:** Đảm bảo hệ thống AI có khả năng triển khai liên tục an toàn (CI/CD), kiểm soát chi phí token minh bạch và phục hồi dịch vụ tức thì khi có biến cố.
- **Điều quan trọng nhất đã học:** Nắm vững tư duy vận hành hệ thống dựa trên bằng chứng kỹ thuật (evidence-based debugging) thay vì phỏng đoán.
- **Hạn chế hoặc phần chưa hoàn thành:** Mô hình LLM trong lab là FakeLLM giả lập; nếu trên production cần gắn thêm streaming TTFT tracker và semantic evaluation.

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc commit SHA cuối.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [x] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
```

---

## ✅ 3. LỆNH KIỂM TRA CUỐI CÙNG TRƯỚC KHI NỘP BÀI

Trước khi thực hiện `git push`, hãy chạy chuỗi kiểm định để đảm bảo mọi tiêu chí đạt 100%:

```bash
# 1. Chạy toàn bộ 22 unit tests
uv run python -m pytest -q

# 2. Kiểm định log schema, correlation ID và PII (Phải đạt 100/100)
uv run python scripts/validate_logs.py

# 3. Kiểm định hợp đồng 6 panel của Dashboard (Phải đạt 6/6 panel)
uv run python scripts/validate_dashboard.py

# 4. Kiểm tra trạng thái Git xem có file thừa/lộ key không
git status --short
git log -1 --oneline
```

### 🔒 Checklist an toàn bảo mật:
- [x] Không commit file `.env` hoặc để lộ Langfuse Secret Key.
- [x] Không commit file `config/challenge.json`.
- [x] Mọi đường dẫn ảnh trong `REPORT.md` là đường dẫn tương đối (ví dụ `evidence/07-trace-waterfall.png`).
- [x] Đầy đủ 14 file evidence nằm trong thư mục `submission/evidence/`.

---
*Chúc bạn hoàn thành xuất sắc bài lab K4-L3B Day 13 Monitoring & LLMOps!*
