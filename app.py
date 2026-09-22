import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="S&P 500 Stock Analysis", page_icon="▲", layout="wide")

# ============================================================
# Design tokens
# ============================================================
BG = "#0B1220"
PANEL = "#111A2C"
LINE = "#26314A"
TEXT = "#E7ECF5"
MUTED = "#8592AB"
GAIN = "#34D399"
LOSS = "#F97066"
HILITE = "#F5B94D"

FONT_DISPLAY = "Space Grotesk"
FONT_BODY = "IBM Plex Sans"

PLOTLY_TEMPLATE = dict(
    layout=dict(
        paper_bgcolor=PANEL,
        plot_bgcolor=PANEL,
        font=dict(family=FONT_BODY, color=TEXT, size=13),
        xaxis=dict(gridcolor=LINE, zerolinecolor=LINE, linecolor=LINE),
        yaxis=dict(gridcolor=LINE, zerolinecolor=LINE, linecolor=LINE),
        margin=dict(t=10, b=10, l=10, r=10),
    )
)

st.markdown(
    f"""
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        html, body, [class*="css"] {{
            font-family: '{FONT_BODY}', sans-serif;
            background-color: {BG};
            color: {TEXT};
        }}
        .stApp {{ background-color: {BG}; }}
        section[data-testid="stSidebar"] {{
            background-color: {PANEL};
            border-right: 1px solid {LINE};
        }}
        h1, h2, h3, .hero-ticker {{
            font-family: '{FONT_DISPLAY}', sans-serif;
        }}
        .hero-row {{
            display: flex;
            align-items: baseline;
            gap: 20px;
            border-bottom: 1px solid {LINE};
            padding-bottom: 18px;
            margin-bottom: 18px;
        }}
        .hero-ticker {{
            font-size: 44px;
            font-weight: 700;
            letter-spacing: -0.5px;
            color: {TEXT};
        }}
        .hero-growth {{
            font-size: 26px;
            font-weight: 600;
            font-family: '{FONT_DISPLAY}', sans-serif;
        }}
        .ledger {{
            display: flex;
            border: 1px solid {LINE};
            border-radius: 6px;
            overflow: hidden;
            margin-bottom: 28px;
        }}
        .ledger-item {{
            flex: 1;
            padding: 14px 20px;
            border-right: 1px solid {LINE};
        }}
        .ledger-item:last-child {{ border-right: none; }}
        .ledger-label {{
            font-size: 12px;
            color: {MUTED};
            letter-spacing: 0.3px;
            margin-bottom: 4px;
        }}
        .ledger-value {{
            font-family: '{FONT_DISPLAY}', sans-serif;
            font-size: 22px;
            font-weight: 600;
            color: {TEXT};
        }}
        .section-label {{
            font-size: 13px;
            color: {MUTED};
            text-transform: none;
            letter-spacing: 0.2px;
            margin-bottom: 6px;
            font-weight: 500;
        }}
        .insight-box {{
            border-left: 3px solid {HILITE};
            background-color: {PANEL};
            padding: 16px 20px;
            border-radius: 4px;
            font-size: 14px;
            line-height: 1.6;
            color: {TEXT};
        }}
        .source-link {{
            font-size: 12px;
            color: {MUTED};
        }}
        .source-link a {{ color: {MUTED}; }}
        hr {{ border-color: {LINE}; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# Data
# ============================================================
@st.cache_data
def load_data():
    df = pd.read_parquet("stock_data.parquet")
    return df

df = load_data()

@st.cache_data
def build_summary(df):
    first_last = (
        df.sort_values("date")
        .groupby("Name", observed=True)
        .agg(first_close=("close", "first"), last_close=("close", "last"))
        .reset_index()
    )
    agg = (
        df.groupby("Name", observed=True)
        .agg(avg_close=("close", "mean"), avg_volatility=("Daily Volatility", "mean"))
        .reset_index()
    )
    summary = first_last.merge(agg, on="Name")
    summary["growth_pct"] = (
        (summary["last_close"] - summary["first_close"]) / summary["first_close"] * 100
    ).round(2)
    return summary

summary = build_summary(df)

# ============================================================
# Sidebar
# ============================================================
st.sidebar.markdown(
    f"<div style='font-family:{FONT_DISPLAY};font-size:20px;font-weight:700;margin-bottom:4px;'>S&amp;P 500</div>"
    f"<div style='color:{MUTED};font-size:13px;margin-bottom:24px;'>Stock Analysis, 2013–2018</div>",
    unsafe_allow_html=True,
)

stock_list = sorted(df["Name"].cat.categories.tolist())
default_idx = stock_list.index("NVDA") if "NVDA" in stock_list else 0
selected_stock = st.sidebar.selectbox("Ticker", stock_list, index=default_idx)

year_list = sorted(df["Year"].unique().tolist())
selected_year = st.sidebar.selectbox("Year — Top / Bottom 5", ["All years"] + [int(y) for y in year_list])

st.sidebar.markdown("<br>", unsafe_allow_html=True)
st.sidebar.markdown(
    f"<div class='source-link'>Rebuilt from the original SQL + Power BI project.<br>"
    f"<a href='https://github.com/Naiv07/SP500-Stock_Analysis' target='_blank'>View source on GitHub →</a></div>",
    unsafe_allow_html=True,
)

# ============================================================
# Hero
# ============================================================
row = summary[summary["Name"] == selected_stock].iloc[0]
growth_color = GAIN if row["growth_pct"] >= 0 else LOSS
growth_sign = "+" if row["growth_pct"] >= 0 else ""

st.markdown(
    f"""
    <div class="hero-row">
        <div class="hero-ticker">{selected_stock}</div>
        <div class="hero-growth" style="color:{growth_color};">{growth_sign}{row['growth_pct']:.2f}%</div>
        <div style="color:{MUTED}; font-size:14px;">5-year growth</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class="ledger">
        <div class="ledger-item">
            <div class="ledger-label">First close</div>
            <div class="ledger-value">${row['first_close']:.2f}</div>
        </div>
        <div class="ledger-item">
            <div class="ledger-label">Last close</div>
            <div class="ledger-value">${row['last_close']:.2f}</div>
        </div>
        <div class="ledger-item">
            <div class="ledger-label">Avg close</div>
            <div class="ledger-value">${row['avg_close']:.2f}</div>
        </div>
        <div class="ledger-item">
            <div class="ledger-label">Avg daily volatility</div>
            <div class="ledger-value">{row['avg_volatility']:.2f}%</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# Price + Volume
# ============================================================
stock_data = df[df["Name"] == selected_stock].sort_values("date")

left, right = st.columns([2, 1])

with left:
    st.markdown("<div class='section-label'>Price trend</div>", unsafe_allow_html=True)
    fig_price = px.line(stock_data, x="date", y="close")
    fig_price.update_traces(line_color=HILITE, line_width=1.8)
    fig_price.update_layout(**PLOTLY_TEMPLATE["layout"], height=340, xaxis_title=None, yaxis_title="Close ($)")
    st.plotly_chart(fig_price, use_container_width=True, config={"displayModeBar": False})

with right:
    st.markdown("<div class='section-label'>Volume</div>", unsafe_allow_html=True)
    fig_vol = px.bar(stock_data, x="date", y="volume")
    fig_vol.update_traces(marker_color=LINE)
    fig_vol.update_layout(**PLOTLY_TEMPLATE["layout"], height=340, xaxis_title=None, yaxis_title=None)
    st.plotly_chart(fig_vol, use_container_width=True, config={"displayModeBar": False})

st.markdown("<br>", unsafe_allow_html=True)

# ============================================================
# Top / Bottom 5
# ============================================================
if selected_year == "All years":
    year_summary = summary.copy()
else:
    yr_df = df[df["Year"] == selected_year]
    fl = (
        yr_df.sort_values("date")
        .groupby("Name", observed=True)
        .agg(first_close=("close", "first"), last_close=("close", "last"))
        .reset_index()
    )
    fl["growth_pct"] = ((fl["last_close"] - fl["first_close"]) / fl["first_close"] * 100).round(2)
    year_summary = fl

col_top, col_bottom = st.columns(2)

with col_top:
    st.markdown(f"<div class='section-label'>Top 5 by growth — {selected_year}</div>", unsafe_allow_html=True)
    top5 = year_summary.nlargest(5, "growth_pct").sort_values("growth_pct")
    fig_top = go.Figure(go.Bar(x=top5["growth_pct"], y=top5["Name"], orientation="h", marker_color=GAIN))
    fig_top.update_layout(**PLOTLY_TEMPLATE["layout"], height=260, xaxis_title=None, yaxis_title=None)
    st.plotly_chart(fig_top, use_container_width=True, config={"displayModeBar": False})

with col_bottom:
    st.markdown(f"<div class='section-label'>Bottom 5 by growth — {selected_year}</div>", unsafe_allow_html=True)
    bottom5 = year_summary.nsmallest(5, "growth_pct").sort_values("growth_pct", ascending=False)
    fig_bottom = go.Figure(go.Bar(x=bottom5["growth_pct"], y=bottom5["Name"], orientation="h", marker_color=LOSS))
    fig_bottom.update_layout(**PLOTLY_TEMPLATE["layout"], height=260, xaxis_title=None, yaxis_title=None)
    st.plotly_chart(fig_bottom, use_container_width=True, config={"displayModeBar": False})

st.markdown("<br>", unsafe_allow_html=True)

# ============================================================
# Risk / Return scatter — full universe, independent of filters
# ============================================================
st.markdown("<div class='section-label'>Risk / return — all 505 stocks (independent of filters above)</div>", unsafe_allow_html=True)

fig_scatter = go.Figure()
fig_scatter.add_trace(
    go.Scatter(
        x=summary["avg_volatility"], y=summary["growth_pct"],
        mode="markers", text=summary["Name"],
        marker=dict(size=6, color=MUTED, opacity=0.55),
        hovertemplate="%{text}<br>Volatility: %{x:.2f}%<br>Growth: %{y:.2f}%<extra></extra>",
        showlegend=False,
    )
)
sel = summary[summary["Name"] == selected_stock]
fig_scatter.add_trace(
    go.Scatter(
        x=sel["avg_volatility"], y=sel["growth_pct"],
        mode="markers+text", text=[selected_stock], textposition="top center",
        textfont=dict(color=HILITE, family=FONT_DISPLAY, size=13),
        marker=dict(size=12, color=HILITE, line=dict(width=1, color=BG)),
        showlegend=False,
    )
)
fig_scatter.update_layout(
    **PLOTLY_TEMPLATE["layout"], height=420,
    xaxis_title="Avg daily volatility (%)", yaxis_title="5-year growth (%)",
)
st.plotly_chart(fig_scatter, use_container_width=True, config={"displayModeBar": False})

# ============================================================
# Insight
# ============================================================
st.markdown(
    f"""
    <div class="insight-box">
        <strong>Key insight —</strong> NVDA delivered the strongest 5-year return (1749.64%) without sitting at
        the extreme end of the volatility range — visually reinforcing the near-zero correlation (r ≈ 0.08)
        found between trading volume and price movement in the underlying SQL analysis.
    </div>
    """,
    unsafe_allow_html=True,
)
