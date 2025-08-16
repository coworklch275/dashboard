# -*- coding: utf-8 -*-
import io
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="월별 매출 대시보드",
    layout="wide",
    page_icon="📈",
)

# --------------------------
# 샘플 데이터
# --------------------------
SAMPLE_CSV = """월,매출액,전년동월,증감률
2024-01,12000000,10500000,14.3
2024-02,13500000,11200000,20.5
2024-03,11000000,12800000,-14.1
2024-04,18000000,15200000,18.4
2024-05,21000000,18500000,13.5
2024-06,19500000,17000000,14.7
2024-07,17500000,16000000,9.4
2024-08,16000000,15000000,6.7
2024-09,15500000,14500000,6.9
2024-10,22000000,20000000,10.0
2024-11,23000000,21000000,9.5
2024-12,24000000,21500000,11.6
"""

# --------------------------
# 사이드바: 파일 업로드/옵션
# --------------------------
st.sidebar.title("데이터 입력")
uploaded = st.sidebar.file_uploader("CSV 업로드 (컬럼: 월, 매출액, 전년동월, 증감률)", type=["csv"])
use_sample = st.sidebar.checkbox("샘플 데이터 사용", value=uploaded is None)

window = st.sidebar.number_input("이동평균 창(개월)", min_value=2, max_value=12, value=3, step=1)
st.sidebar.caption("CSV의 '월'은 YYYY-MM, 숫자 컬럼은 정수/실수여야 합니다.")

# --------------------------
# 데이터 로드/전처리
# --------------------------
@st.cache_data
def load_df(file_bytes: bytes | None, use_sample_flag: bool) -> pd.DataFrame:
    if use_sample_flag or not file_bytes:
        df = pd.read_csv(io.StringIO(SAMPLE_CSV))
    else:
        df = pd.read_csv(io.BytesIO(file_bytes))
    # 타입 보정
    df["월"] = pd.to_datetime(df["월"], format="%Y-%m")
    for col in ["매출액", "전년동월", "증감률"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["월"]).sort_values("월").reset_index(drop=True)
    return df

df = load_df(uploaded.read() if uploaded else None, use_sample)

if df.empty or not set(["월", "매출액", "전년동월", "증감률"]).issubset(df.columns):
    st.error("유효한 데이터가 아닙니다. 컬럼: 월, 매출액, 전년동월, 증감률 이 필요합니다.")
    st.stop()

# 파생
df["월_label"] = df["월"].dt.strftime("%Y-%m")
df["매출액_이동평균"] = df["매출액"].rolling(window=window, min_periods=window).mean()

# --------------------------
# KPI (요약 수치)
# --------------------------
col1, col2, col3, col4 = st.columns(4)
total_sales = int(df["매출액"].sum())
avg_growth = float(df["증감률"].mean())
yoy_total = float((df["매출액"].sum() - df["전년동월"].sum()) / df["전년동월"].sum() * 100) if df["전년동월"].sum() else np.nan
max_row = df.loc[df["매출액"].idxmax()]
min_row = df.loc[df["매출액"].idxmin()]

col1.metric("연 누적 매출", f"{total_sales:,.0f} 원")
col2.metric("평균 증감률", f"{avg_growth:.1f} %")
col3.metric("전년 대비(누적) 증가율", f"{yoy_total:.1f} %")
col4.metric("최대/최소 매출 월", f"{max_row['월_label']} / {min_row['월_label']}")

st.markdown("---")

# --------------------------
# 1) 월별 추세 비교 (현재 vs 전년동월)
# --------------------------
fig_line = go.Figure()
fig_line.add_trace(go.Scatter(
    x=df["월_label"], y=df["매출액"], mode="lines+markers",
    name="매출액", hovertemplate="월=%{x}<br>매출액=%{y:,} 원"
))
fig_line.add_trace(go.Scatter(
    x=df["월_label"], y=df["전년동월"], mode="lines+markers",
    name="전년동월", hovertemplate="월=%{x}<br>전년동월=%{y:,} 원"
))
fig_line.update_layout(
    title="월별 매출 추세 비교 (현재 vs 전년동월)",
    xaxis_title="월",
    yaxis_title="금액(원)",
    hovermode="x unified",
    height=420,
    margin=dict(l=40, r=20, t=60, b=40)
)
st.plotly_chart(fig_line, use_container_width=True)

# --------------------------
# 2) 전년 대비 증감률 (%) 바 차트
# --------------------------
bar_colors = np.where(df["증감률"] >= 0, "#16a34a", "#dc2626")
fig_bar = go.Figure()
fig_bar.add_trace(go.Bar(
    x=df["월_label"], y=df["증감률"], marker_color=bar_colors,
    name="증감률", hovertemplate="월=%{x}<br>증감률=%{y:.1f}%"
))
fig_bar.add_hline(y=0, line_width=1, line_dash="solid", line_color="#64748b")
fig_bar.update_layout(
    title="전년 대비 증감률 (%)",
    xaxis_title="월",
    yaxis_title="증감률(%)",
    height=420,
    margin=dict(l=40, r=20, t=60, b=40)
)
st.plotly_chart(fig_bar, use_container_width=True)

# --------------------------
# 3) 3개월 이동평균(창 선택 가능) 라인
# --------------------------
fig_mma = go.Figure()
fig_mma.add_trace(go.Scatter(
    x=df["월_label"], y=df["매출액"], mode="lines+markers",
    name="매출액(원자료)", opacity=0.45,
    hovertemplate="월=%{x}<br>매출액=%{y:,} 원"
))
fig_mma.add_trace(go.Scatter(
    x=df["월_label"], y=df["매출액_이동평균"], mode="lines+markers",
    name=f"매출액 {window}MMA",
    hovertemplate=f"월=%{{x}}<br>{window}MMA=%{{y:,.0f}} 원"
))
fig_mma.update_layout(
    title=f"{window}개월 이동평균 (매출액)",
    xaxis_title="월",
    yaxis_title="금액(원)",
    hovermode="x unified",
    height=420,
    margin=dict(l=40, r=20, t=60, b=40)
)
st.plotly_chart(fig_mma, use_container_width=True)

# --------------------------
# 원천 데이터 확인
# --------------------------
with st.expander("데이터 미리보기 / 다운로드"):
    st.dataframe(df[["월_label", "매출액", "전년동월", "증감률", "매출액_이동평균"]].rename(
        columns={"월_label": "월"}), use_container_width=True)
    st.download_button(
        label="현재 데이터 CSV 다운로드",
        data=df.to_csv(index=False).encode("utf-8-sig"),
        file_name="월별_매출_가공데이터.csv",
        mime="text/csv"
    )
