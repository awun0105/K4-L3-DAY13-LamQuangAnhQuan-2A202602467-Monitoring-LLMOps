"""
Streamlit Monitoring & Observability Runtime Dashboard
Tuân thủ 100% hợp đồng config/dashboard.yaml và tài liệu quy chuẩn docs/dashboard-spec.md
Phục vụ thu thập Evidence 11 (Dashboard overview) và Evidence 12 (Incident metric)
K4-L3B Day 13 Monitoring & LLMOps
"""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import yaml

# Cấu hình trang chuẩn Streamlit
st.set_page_config(
    page_title="K4-L3B Day 13 Monitoring & LLMOps",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS cho giao diện hiện đại, sắc nét khi chụp ảnh evidence
st.markdown(
    """
    <style>
    /* Header & Typography */
    .main-title {
        font-size: 1.85rem;
        font-weight: 800;
        color: #1E3A8A;
        margin-bottom: 0.1rem;
        letter-spacing: -0.5px;
    }
    .sub-title {
        font-size: 0.95rem;
        color: #4B5563;
        margin-bottom: 1rem;
    }
    /* Card Styles */
    .metric-box {
        background: linear-gradient(135deg, #F9FAFB 0%, #F3F4F6 100%);
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        padding: 12px 14px;
        margin-bottom: 10px;
    }
    .panel-header {
        font-size: 1.1rem;
        font-weight: 700;
        color: #111827;
        margin-bottom: 4px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    /* Badges */
    .badge-pass {
        background-color: #DEF7EC;
        color: #03543F;
        padding: 3px 8px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 0.78rem;
        border: 1px solid #BCF0DA;
    }
    .badge-breach {
        background-color: #FDE8E8;
        color: #9B1C1C;
        padding: 3px 8px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 0.78rem;
        border: 1px solid #FBD5D5;
    }
    .badge-unit {
        background-color: #E0E7FF;
        color: #3730A3;
        padding: 2px 7px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-left: 6px;
    }
    .badge-slo {
        background-color: #FEF3C7;
        color: #92400E;
        padding: 2px 7px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    /* Streamlit Metric tweak */
    div[data-testid="stMetricValue"] {
        font-size: 1.35rem !important;
        font-weight: 700 !important;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.78rem !important;
        color: #6B7280 !important;
        font-weight: 500 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=5)
def load_config() -> dict:
    """Tải cấu hình từ config/dashboard.yaml để đối chiếu contract"""
    config_path = Path("config/dashboard.yaml")
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            return yaml.safe_load(f).get("dashboard", {})
    return {}


def load_logs(file_path: str = "data/logs.jsonl") -> pd.DataFrame:
    """Đọc và chuẩn hóa dữ liệu từ data/logs.jsonl"""
    path = Path(file_path)
    if not path.exists():
        return pd.DataFrame()

    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                records.append(data)
            except json.JSONDecodeError:
                continue

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)
    if "ts" in df.columns:
        df["datetime"] = pd.to_datetime(df["ts"], utc=True, errors="coerce")
    return df


# ---------------- SIDEBAR CONTROLS ----------------
st.sidebar.title("🛠️ Điều khiển Dashboard")
config = load_config()

log_file_input = st.sidebar.text_input("📁 Đường dẫn file log", value="data/logs.jsonl")

time_window_mode = st.sidebar.radio(
    "🕒 Cách tính khoảng thời gian (Time Range):",
    [
        "60 phút hoạt động (Activity Window - Khuyên dùng chụp ảnh)",
        "60 phút tính từ hiện tại (Live Wall-Clock)",
        "Toàn bộ logs (All Time)",
    ],
    index=0,
)

view_mode = st.sidebar.radio(
    "🖥️ Chế độ hiển thị (Layout Mode):",
    [
        "📌 Toàn cảnh 6 Panel (Chụp ảnh 11-dashboard-overview.png)",
        "📑 Phân tách 11a & 11b (Nếu chụp 2 ảnh riêng)",
        "🚨 Điều tra sự cố Challenge (Chụp ảnh 12-incident-metric.png)",
    ],
    index=0,
)

auto_refresh = st.sidebar.checkbox("🔄 Tự động làm mới (Auto Refresh)", value=False)
refresh_interval = st.sidebar.slider("Chu kỳ làm mới (giây)", 15, 60, 30)

if st.sidebar.button("🔃 Làm mới dữ liệu ngay"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.divider()
st.sidebar.markdown(
    """
    **📋 Hợp đồng SLO / Ngưỡng kỹ thuật:**
    - **Latency:** P95 &le; 3000ms | Warning &le; 2000ms
    - **Traffic:** Rate &ge; 1 req/min
    - **Errors:** Error rate &le; 2.0% | Retrieval &ge; 90%
    - **Cost:** Total cost &le; $2.50
    - **Tokens:** Total tokens &le; 50,000
    - **Quality:** Mean score &ge; 0.75
    """
)

# ---------------- DATA LOADING & FILTERING ----------------
df_all = load_logs(log_file_input)

# Tiêu đề giao diện
st.markdown('<div class="main-title">📊 K4-L3B Day 13 Monitoring & LLMOps</div>', unsafe_allow_html=True)
now_utc_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

if df_all.empty or "datetime" not in df_all.columns:
    st.markdown(
        f'<div class="sub-header">Time Range: <b>60 minutes</b> &bull; Refresh: <b>30s</b> &bull; Giờ hiện tại: <code>{now_utc_str}</code> &bull; Nguồn: <code>{log_file_input}</code></div>',
        unsafe_allow_html=True,
    )
    st.warning(f"⚠️ Chưa có dữ liệu hoặc file `{log_file_input}` chưa tồn tại. Hãy chạy `uv run python scripts/load_test.py` để sinh traffic.")
    st.stop()

# Xử lý lọc dữ liệu theo Time Range
df_all = df_all.dropna(subset=["datetime"]).sort_values("datetime")
max_log_time = df_all["datetime"].max()
now_utc = datetime.now(timezone.utc)

if "Activity Window" in time_window_mode:
    cutoff_time = max_log_time - timedelta(minutes=60)
    df = df_all[df_all["datetime"] >= cutoff_time].copy()
    time_label = f"60 phút hoạt động ({cutoff_time.strftime('%H:%M')} &rarr; {max_log_time.strftime('%H:%M')} UTC)"
elif "Live Wall-Clock" in time_window_mode:
    cutoff_time = now_utc - timedelta(minutes=60)
    df = df_all[df_all["datetime"] >= cutoff_time].copy()
    if df.empty:
        st.info("ℹ️ Không có request trong 60 phút vừa qua. Đang hiển thị toàn bộ logs gần nhất.")
        df = df_all.copy()
    time_label = f"60 phút gần nhất ({cutoff_time.strftime('%H:%M')} &rarr; {now_utc.strftime('%H:%M')} UTC)"
else:
    df = df_all.copy()
    time_label = f"Toàn bộ ({len(df)} records)"

st.markdown(
    f'<div class="sub-header"><b>Time Range: 60 minutes</b> ({time_label}) &bull; Refresh: <b>30s</b> &bull; Cập nhật: <code>{now_utc_str}</code> &bull; Tổng logs: <b>{len(df)}</b> events</div>',
    unsafe_allow_html=True,
)

# Phân loại theo event
req_received = df[df["event"] == "request_received"].copy()
resp_sent = df[df["event"] == "response_sent"].copy()
req_failed = df[df["event"] == "request_failed"].copy()

# Tính toán các chỉ số vĩ mô (KPIs)
total_requests = len(req_received)
total_responses = len(resp_sent)
total_failed = len(req_failed)
error_rate = (total_failed / total_requests * 100) if total_requests > 0 else 0.0

p50_lat = float(resp_sent["latency_ms"].quantile(0.50)) if (not resp_sent.empty and "latency_ms" in resp_sent) else 0.0
p95_lat = float(resp_sent["latency_ms"].quantile(0.95)) if (not resp_sent.empty and "latency_ms" in resp_sent) else 0.0
p99_lat = float(resp_sent["latency_ms"].quantile(0.99)) if (not resp_sent.empty and "latency_ms" in resp_sent) else 0.0
ttft_p95 = float(resp_sent["ttft_ms"].quantile(0.95)) if (not resp_sent.empty and "ttft_ms" in resp_sent.columns) else 0.0

total_cost = float(resp_sent["cost_usd"].sum()) if (not resp_sent.empty and "cost_usd" in resp_sent) else 0.0
tokens_in_sum = int(resp_sent["tokens_in"].sum()) if (not resp_sent.empty and "tokens_in" in resp_sent) else 0
tokens_out_sum = int(resp_sent["tokens_out"].sum()) if (not resp_sent.empty and "tokens_out" in resp_sent) else 0
avg_quality = float(resp_sent["quality_score"].mean()) if (not resp_sent.empty and "quality_score" in resp_sent) else 0.0

tools_df = resp_sent[resp_sent["tool_name"].notna()] if ("tool_name" in resp_sent.columns) else pd.DataFrame()
if not tools_df.empty and "tool_success" in tools_df.columns:
    success_tools = (tools_df["tool_success"] == True).sum()
    retrieval_success_pct = float(success_tools / len(tools_df) * 100)
else:
    retrieval_success_pct = 100.0

# ---------------- THANH TỔNG HỢP SLO SUMMARY ----------------
st.markdown("### 🎯 Trạng thái 6 Chỉ số SLO / Threshold")
slo_cols = st.columns(6)

with slo_cols[0]:
    is_p95_pass = p95_lat <= 3000
    st.metric("1. Latency P95", f"{p95_lat:.0f} ms", delta="SLO <= 3000ms", delta_color="off")
    st.markdown(
        f'<span class="{ "badge-pass" if is_p95_pass else "badge-breach" }">{ "🟢 PASS" if is_p95_pass else "🔴 BREACH" }</span>',
        unsafe_allow_html=True,
    )

with slo_cols[1]:
    traffic_1m = req_received.set_index("datetime").resample("1min").size() if not req_received.empty else pd.Series()
    peak_rate = int(traffic_1m.max()) if not traffic_1m.empty else 0
    is_traffic_pass = peak_rate >= 1
    st.metric("2. Traffic Rate", f"{peak_rate} req/m", delta="Target >= 1", delta_color="off")
    st.markdown(
        f'<span class="{ "badge-pass" if is_traffic_pass else "badge-breach" }">{ "🟢 PASS" if is_traffic_pass else "🔴 BREACH" }</span>',
        unsafe_allow_html=True,
    )

with slo_cols[2]:
    is_error_pass = (error_rate <= 2.0) and (retrieval_success_pct >= 90.0)
    st.metric("3. Error Rate", f"{error_rate:.1f} %", delta=f"RAG: {retrieval_success_pct:.0f}%", delta_color="off")
    st.markdown(
        f'<span class="{ "badge-pass" if is_error_pass else "badge-breach" }">{ "🟢 PASS" if is_error_pass else "🔴 BREACH" }</span>',
        unsafe_allow_html=True,
    )

with slo_cols[3]:
    is_cost_pass = total_cost <= 2.5
    st.metric("4. Total Cost", f"${total_cost:.4f}", delta="Budget <= $2.50", delta_color="off")
    st.markdown(
        f'<span class="{ "badge-pass" if is_cost_pass else "badge-breach" }">{ "🟢 PASS" if is_cost_pass else "🔴 BREACH" }</span>',
        unsafe_allow_html=True,
    )

with slo_cols[4]:
    is_token_pass = max(tokens_in_sum, tokens_out_sum) <= 50000
    st.metric("5. Tokens", f"{tokens_in_sum + tokens_out_sum:,}", delta="Limit <= 50k", delta_color="off")
    st.markdown(
        f'<span class="{ "badge-pass" if is_token_pass else "badge-breach" }">{ "🟢 PASS" if is_token_pass else "🔴 BREACH" }</span>',
        unsafe_allow_html=True,
    )

with slo_cols[5]:
    is_quality_pass = avg_quality >= 0.75
    st.metric("6. Quality", f"{avg_quality:.2f}", delta="Target >= 0.75", delta_color="off")
    st.markdown(
        f'<span class="{ "badge-pass" if is_quality_pass else "badge-breach" }">{ "🟢 PASS" if is_quality_pass else "🔴 BREACH" }</span>',
        unsafe_allow_html=True,
    )

st.divider()


# ---------------- HÀM VẼ CÁC PANEL ----------------
def render_panel_latency(chart_height: int = 260):
    st.markdown(
        '<div class="panel-header"><span>1️⃣ Latency percentiles and TTFT <span class="badge-unit">Unit: ms</span></span><span class="badge-slo">Threshold: P95 &le; 3000ms</span></div>',
        unsafe_allow_html=True,
    )
    if resp_sent.empty or "latency_ms" not in resp_sent.columns:
        st.info("Chưa có dữ liệu `response_sent`.")
        return

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("P50 Latency", f"{p50_lat:.1f} ms")
    m2.metric("P95 Latency", f"{p95_lat:.1f} ms")
    m3.metric("P99 Latency", f"{p99_lat:.1f} ms")
    m4.metric("TTFT P95", f"{ttft_p95:.1f} ms")

    fig = go.Figure()
    # Đường Latency
    fig.add_trace(
        go.Scatter(
            x=resp_sent["datetime"],
            y=resp_sent["latency_ms"],
            mode="lines+markers",
            name="Latency (ms)",
            line=dict(color="#2563EB", width=2),
            marker=dict(size=6, color=["#DC2626" if lat > 2000 else "#2563EB" for lat in resp_sent["latency_ms"]]),
            hovertemplate="Time: %{x}<br>Latency: %{y:.1f} ms<extra></extra>",
        )
    )
    # Đường TTFT
    if "ttft_ms" in resp_sent.columns:
        fig.add_trace(
            go.Scatter(
                x=resp_sent["datetime"],
                y=resp_sent["ttft_ms"],
                mode="lines",
                name="TTFT (ms)",
                line=dict(color="#10B981", width=1.5, dash="dot"),
                hovertemplate="Time: %{x}<br>TTFT: %{y:.1f} ms<extra></extra>",
            )
        )
    # SLO Threshold (3000ms)
    fig.add_hline(
        y=3000,
        line_dash="dash",
        line_color="#DC2626",
        annotation_text="SLO: 3000ms",
        annotation_position="top right",
    )
    # Warning Threshold (2000ms)
    fig.add_hline(
        y=2000,
        line_dash="dot",
        line_color="#F59E0B",
        annotation_text="Warning: 2000ms",
        annotation_position="bottom right",
    )
    fig.update_layout(
        height=chart_height,
        margin=dict(l=10, r=10, t=25, b=20),
        xaxis_title="Thời gian (UTC)",
        yaxis_title="Latency (ms)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_panel_traffic(chart_height: int = 260):
    st.markdown(
        '<div class="panel-header"><span>2️⃣ Request traffic <span class="badge-unit">Unit: req/min</span></span><span class="badge-slo">Threshold: Rate &ge; 1</span></div>',
        unsafe_allow_html=True,
    )
    if req_received.empty:
        st.info("Chưa có dữ liệu `request_received`.")
        return

    # Tính traffic theo 1 phút
    traffic_df = req_received.set_index("datetime").resample("1min").size().reset_index(name="count")
    curr_rate = int(traffic_df["count"].iloc[-1]) if not traffic_df.empty else 0
    p_rate = int(traffic_df["count"].max()) if not traffic_df.empty else 0

    t1, t2, t3 = st.columns(3)
    t1.metric("Total Requests", f"{total_requests}")
    t2.metric("Latest Rate", f"{curr_rate} req/m")
    t3.metric("Peak Rate", f"{p_rate} req/m")

    fig = px.bar(
        traffic_df,
        x="datetime",
        y="count",
        labels={"datetime": "Thời gian (UTC)", "count": "Requests/phút"},
        color_discrete_sequence=["#4F46E5"],
    )
    fig.add_hline(
        y=1,
        line_dash="dash",
        line_color="#10B981",
        annotation_text="Threshold: 1 req/min",
        annotation_position="top left",
    )
    fig.update_layout(
        height=chart_height,
        margin=dict(l=10, r=10, t=25, b=20),
        xaxis_title="Thời gian (UTC)",
        yaxis_title="Req / phút",
    )
    st.plotly_chart(fig, use_container_width=True)


def render_panel_errors(chart_height: int = 260):
    st.markdown(
        '<div class="panel-header"><span>3️⃣ Error rate and retrieval success <span class="badge-unit">Unit: %</span></span><span class="badge-slo">Threshold: Error &le; 2%</span></div>',
        unsafe_allow_html=True,
    )
    e1, e2, e3 = st.columns(3)
    e1.metric("Error Rate", f"{error_rate:.2f} %")
    e2.metric("Retrieval Success", f"{retrieval_success_pct:.1f} %")
    e3.metric("Failed Requests", f"{total_failed}")

    fig = go.Figure()
    # Gauge Error Rate
    fig.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=error_rate,
            title={"text": "Error Rate % (SLO &le; 2%)", "font": {"size": 13}},
            domain={"x": [0, 0.48], "y": [0, 1]},
            gauge={
                "axis": {"range": [0, 10]},
                "bar": {"color": "#DC2626" if error_rate > 2 else "#10B981"},
                "threshold": {"line": {"color": "red", "width": 3}, "thickness": 0.75, "value": 2.0},
            },
        )
    )
    # Gauge Retrieval Success
    fig.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=retrieval_success_pct,
            title={"text": "Retrieval Success % (SLO &ge; 90%)", "font": {"size": 13}},
            domain={"x": [0.52, 1], "y": [0, 1]},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#10B981" if retrieval_success_pct >= 90 else "#DC2626"},
                "threshold": {"line": {"color": "green", "width": 3}, "thickness": 0.75, "value": 90.0},
            },
        )
    )
    fig.update_layout(height=chart_height, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

    # Breakdown by error_type theo query: count_by(error_type)
    if total_failed > 0 and "error_type" in req_failed.columns:
        error_counts = req_failed["error_type"].value_counts().reset_index()
        error_counts.columns = ["error_type", "count"]
        st.caption("🔍 Error Breakdown by Error Type:")
        st.dataframe(error_counts, use_container_width=True, hide_index=True)
    else:
        st.caption("✅ Không có lỗi ghi nhận &bull; Error Breakdown: 0 issues")


def render_panel_cost(chart_height: int = 260):
    st.markdown(
        '<div class="panel-header"><span>4️⃣ Cost over time <span class="badge-unit">Unit: USD ($)</span></span><span class="badge-slo">Budget: &le; $2.50</span></div>',
        unsafe_allow_html=True,
    )
    if resp_sent.empty or "cost_usd" not in resp_sent.columns:
        st.info("Chưa có dữ liệu `cost_usd`.")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Cost", f"${total_cost:.4f}")
    cost_per_req = total_cost / total_responses if total_responses > 0 else 0
    c2.metric("Avg Cost / Req", f"${cost_per_req:.6f}")
    c3.metric("Remaining Budget", f"${max(0.0, 2.5 - total_cost):.4f}")

    resp_cost = resp_sent.sort_values("datetime").copy()
    resp_cost["cum_cost"] = resp_cost["cost_usd"].cumsum()

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=resp_cost["datetime"],
            y=resp_cost["cum_cost"],
            mode="lines",
            name="Cumulative Cost ($)",
            line=dict(color="#059669", width=2),
            fill="tozeroy",
            fillcolor="rgba(16, 185, 129, 0.12)",
            hovertemplate="Time: %{x}<br>Cost: $%{y:.4f}<extra></extra>",
        )
    )
    fig.add_hline(
        y=2.5,
        line_dash="dash",
        line_color="#DC2626",
        annotation_text="Budget: $2.50",
        annotation_position="top left",
    )
    fig.update_layout(
        height=chart_height,
        margin=dict(l=10, r=10, t=25, b=20),
        xaxis_title="Thời gian (UTC)",
        yaxis_title="Chi phí ($ USD)",
    )
    st.plotly_chart(fig, use_container_width=True)


def render_panel_tokens(chart_height: int = 260):
    st.markdown(
        '<div class="panel-header"><span>5️⃣ Input and output tokens <span class="badge-unit">Unit: tokens</span></span><span class="badge-slo">Limit: &le; 50,000</span></div>',
        unsafe_allow_html=True,
    )
    if resp_sent.empty or "tokens_in" not in resp_sent.columns or "tokens_out" not in resp_sent.columns:
        st.info("Chưa có dữ liệu tokens.")
        return

    k1, k2, k3 = st.columns(3)
    k1.metric("Tokens In", f"{tokens_in_sum:,}")
    k2.metric("Tokens Out", f"{tokens_out_sum:,}")
    k3.metric("Total Tokens", f"{tokens_in_sum + tokens_out_sum:,}")

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=resp_sent["datetime"],
            y=resp_sent["tokens_in"],
            name="Tokens In",
            marker_color="#3B82F6",
        )
    )
    fig.add_trace(
        go.Bar(
            x=resp_sent["datetime"],
            y=resp_sent["tokens_out"],
            name="Tokens Out",
            marker_color="#8B5CF6",
        )
    )
    fig.update_layout(
        barmode="stack",
        height=chart_height,
        margin=dict(l=10, r=10, t=25, b=20),
        xaxis_title="Thời gian (UTC)",
        yaxis_title="Tokens",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_panel_quality(chart_height: int = 260):
    st.markdown(
        '<div class="panel-header"><span>6️⃣ Quality proxy <span class="badge-unit">Unit: score (0-1)</span></span><span class="badge-slo">Target: &ge; 0.75</span></div>',
        unsafe_allow_html=True,
    )
    if resp_sent.empty or "quality_score" not in resp_sent.columns:
        st.info("Chưa có dữ liệu `quality_score`.")
        return

    min_q = float(resp_sent["quality_score"].min())
    max_q = float(resp_sent["quality_score"].max())

    q1, q2, q3 = st.columns(3)
    q1.metric("Mean Score", f"{avg_quality:.2f}")
    q2.metric("Min Score", f"{min_q:.2f}")
    q3.metric("Max Score", f"{max_q:.2f}")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=resp_sent["datetime"],
            y=resp_sent["quality_score"],
            mode="lines+markers",
            name="Quality Score",
            line=dict(color="#F59E0B", width=2),
            marker=dict(size=6),
            hovertemplate="Time: %{x}<br>Score: %{y:.2f}<extra></extra>",
        )
    )
    fig.add_hline(
        y=0.75,
        line_dash="dash",
        line_color="#10B981",
        annotation_text="SLO Target: 0.75",
        annotation_position="bottom right",
    )
    fig.update_layout(
        height=chart_height,
        margin=dict(l=10, r=10, t=25, b=20),
        xaxis_title="Thời gian (UTC)",
        yaxis_title="Quality Score",
        yaxis=dict(range=[0, 1.05]),
    )
    st.plotly_chart(fig, use_container_width=True)


# ---------------- RENDER THEO VIEW MODE ĐÃ CHỌN ----------------
if "Toàn cảnh 6 Panel" in view_mode:
    # Bố cục 2 cột x 3 hàng chuẩn cho 6 Panel để chụp trọn vẹn trong 1 ảnh Evidence 11
    row1_c1, row1_c2 = st.columns(2)
    with row1_c1:
        render_panel_latency(chart_height=250)
    with row1_c2:
        render_panel_traffic(chart_height=250)

    st.divider()

    row2_c1, row2_c2 = st.columns(2)
    with row2_c1:
        render_panel_errors(chart_height=250)
    with row2_c2:
        render_panel_cost(chart_height=250)

    st.divider()

    row3_c1, row3_c2 = st.columns(2)
    with row3_c1:
        render_panel_tokens(chart_height=250)
    with row3_c2:
        render_panel_quality(chart_height=250)

elif "Phân tách 11a & 11b" in view_mode:
    tab_11a, tab_11b = st.tabs(["📸 Evidence 11a (Latency, Traffic, Errors)", "📸 Evidence 11b (Cost, Tokens, Quality)"])
    with tab_11a:
        st.subheader("Nhóm Panel 11a: Hiệu năng & Lưu lượng")
        col_a1, col_a2 = st.columns(2)
        with col_a1:
            render_panel_latency(chart_height=300)
        with col_a2:
            render_panel_traffic(chart_height=300)
        st.divider()
        render_panel_errors(chart_height=280)

    with tab_11b:
        st.subheader("Nhóm Panel 11b: Chi phí, Tokens & Chất lượng")
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            render_panel_cost(chart_height=300)
        with col_b2:
            render_panel_tokens(chart_height=300)
        st.divider()
        render_panel_quality(chart_height=280)

else:  # Điều tra sự cố Challenge (Evidence 12)
    st.subheader("🚨 Chế độ Điều tra Sự cố Challenge (Evidence 12: Incident Metric)")
    st.markdown(
        """
        > 💡 **Mục đích:** Chụp màn hình đồ thị thể hiện rõ **đoạn baseline bình thường (~370ms)** và **đoạn tăng vọt bất thường (>2000ms do sự cố `rag_slow`)** trên cùng một trục thời gian.
        """
    )
    # Hiển thị biểu đồ Latency lớn và toàn diện
    render_panel_latency(chart_height=400)

    st.divider()
    st.markdown("### 🔎 Danh sách Request bất thường (Latency > 2000ms)")
    if not resp_sent.empty:
        slow_requests = resp_sent[resp_sent["latency_ms"] > 2000].sort_values("datetime", ascending=False)
        if not slow_requests.empty:
            st.error(f"⚠️ Phát hiện **{len(slow_requests)} request bất thường** vượt ngưỡng 2000ms!")
            slow_cols = [c for c in ["ts", "correlation_id", "feature", "latency_ms", "ttft_ms", "tool_name", "tool_success"] if c in slow_requests.columns]
            st.dataframe(slow_requests[slow_cols], use_container_width=True)
            st.info(f"👉 Dùng mã `correlation_id` bất thường đầu tiên: **`{slow_requests['correlation_id'].iloc[0]}`** để chụp ảnh `13-incident-log.png` và mở trace `14-incident-trace.png`.")
        else:
            st.success("✅ Chưa phát hiện request nào vượt ngưỡng 2000ms. Hãy chạy kịch bản challenge để tạo đột biến độ trễ:")
            st.code("uv run python scripts/inject_incident.py\nuv run python scripts/load_test.py --challenge --concurrency 5")


# ---------------- LOG EXPLORER TABLE (DÀNH CHO MỌI CHẾ ĐỘ) ----------------
with st.expander("📋 Bảng tra cứu Log chi tiết (Log Explorer)", expanded=False):
    st.markdown("Dùng để tìm kiếm request nhanh và đối chiếu `correlation_id` giữa log và Langfuse.")
    exp_c1, exp_c2 = st.columns([1, 2])
    with exp_c1:
        f_feat = st.multiselect("Lọc theo feature:", options=df["feature"].dropna().unique().tolist() if "feature" in df else [])
    with exp_c2:
        search_txt = st.text_input("Tìm kiếm correlation_id:", "")

    v_df = resp_sent.copy() if not resp_sent.empty else df.copy()
    if f_feat and "feature" in v_df.columns:
        v_df = v_df[v_df["feature"].isin(f_feat)]
    if search_txt and "correlation_id" in v_df.columns:
        v_df = v_df[v_df["correlation_id"].str.contains(search_txt, na=False)]

    disp = [c for c in ["ts", "correlation_id", "feature", "latency_ms", "ttft_ms", "cost_usd", "tokens_in", "tokens_out", "quality_score"] if c in v_df.columns]
    st.dataframe(v_df[disp].sort_values("ts", ascending=False).head(30), use_container_width=True)

# ---------------- NON-BLOCKING AUTO REFRESH ----------------
if auto_refresh:
    # Dùng JavaScript setTimeout không chặn thread để UI luôn mượt mà
    st.components.v1.html(
        f"""
        <script>
            setTimeout(function() {{
                window.parent.location.reload();
            }}, {refresh_interval * 1000});
        </script>
        """,
        height=0,
    )
