import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="S&P 500 Stock Analysis", page_icon="📈", layout="wide")

# ----------------------------
# Load data
# ----------------------------
@st.cache_data
def load_data():
    df = pd.read_parquet("stock_data.parquet")
    df["date"] = pd.to_datetime(df["date"])
    return df

df = load_data()

# ----------------------------
# Precompute per-stock summary (mirrors the SQL CTE from the original analysis)
# ----------------------------
@st.cache_data
def build_summary(df):
    first_last = (
        df.sort_values("date")
        .groupby("Name")
        .agg(first_close=("close", "first"), last_close=("close", "last"))
        .reset_index()
    )
    agg = (
        df.groupby("Name")
        .agg(avg_close=("close", "mean"), avg_volatility=("Daily Volatility", "mean"))
        .reset_index()
    )
    summary = first_last.merge(agg, on="Name")
    summary["growth_pct"] = (
        (summary["last_close"] - summary["first_close"]) / summary["first_close"] * 100
    ).round(2)
    return summary

summary = build_summary(df)

# ----------------------------
# Sidebar controls (mirrors the Power BI slicers)
# ----------------------------
st.sidebar.title("Filters")
stock_list = sorted(df["Name"].unique())
selected_stock = st.sidebar.selectbox("Stock", stock_list, index=stock_list.index("NVDA") if "NVDA" in stock_list else 0)

year_list = sorted(df["Year"].dropna().unique())
selected_year = st.sidebar.selectbox("Year (for Top/Bottom 5 charts)", ["All"] + [int(y) for y in year_list])

st.sidebar.markdown("---")
st.sidebar.caption(
    "Rebuilt from the original SQL + Power BI project. "
    "[View source](https://github.com/Naiv07/SP500-Stock_Analysis)"
)

# ----------------------------
# Title
# ----------------------------
st.title("📈 S&P 500 Stock Analysis")
st.caption("5 years of daily data (2013–2018) · 505 companies · 619,000+ rows")

# ----------------------------
# KPI Cards (respond to the stock selector, like the Power BI cards)
# ----------------------------
stock_row = summary[summary["Name"] == selected_stock].iloc[0]

col1, col2, col3, col4 = st.columns(4)
col1.metric("First Close", f"${stock_row['first_close']:.2f}")
col2.metric("Last Close", f"${stock_row['last_close']:.2f}")
col3.metric("Growth %", f"{stock_row['growth_pct']:.2f}%")
col4.metric("Avg Volatility", f"{stock_row['avg_volatility']:.2f}%")

st.markdown("---")

# ----------------------------
# Price trend (single stock, connected to slicer)
# ----------------------------
left, right = st.columns([2, 1])

with left:
    st.subheader(f"{selected_stock} — Price Trend")
    stock_data = df[df["Name"] == selected_stock].sort_values("date")
    fig_price = px.line(stock_data, x="date", y="close", labels={"close": "Close Price ($)", "date": "Date"})
    fig_price.update_layout(height=380, margin=dict(t=10, b=10))
    st.plotly_chart(fig_price, use_container_width=True)

with right:
    st.subheader("Volume Trend")
    fig_vol = px.bar(stock_data, x="date", y="volume", labels={"volume": "Volume", "date": "Date"})
    fig_vol.update_layout(height=380, margin=dict(t=10, b=10))
    st.plotly_chart(fig_vol, use_container_width=True)

st.markdown("---")

# ----------------------------
# Top 5 / Bottom 5 Growth (year-aware, matching the Power BI Edit Interactions behavior)
# ----------------------------
if selected_year == "All":
    year_summary = summary.copy()
else:
    yr_df = df[df["Year"] == selected_year]
    first_last_y = (
        yr_df.sort_values("date")
        .groupby("Name")
        .agg(first_close=("close", "first"), last_close=("close", "last"))
        .reset_index()
    )
    first_last_y["growth_pct"] = (
        (first_last_y["last_close"] - first_last_y["first_close"]) / first_last_y["first_close"] * 100
    ).round(2)
    year_summary = first_last_y

col_top, col_bottom = st.columns(2)

with col_top:
    st.subheader(f"Top 5 by Growth % ({selected_year})")
    top5 = year_summary.nlargest(5, "growth_pct")
    fig_top = px.bar(top5, x="growth_pct", y="Name", orientation="h", color="growth_pct",
                      color_continuous_scale="Greens")
    fig_top.update_layout(height=320, margin=dict(t=10, b=10), showlegend=False, coloraxis_showscale=False)
    fig_top.update_yaxes(categoryorder="total ascending")
    st.plotly_chart(fig_top, use_container_width=True)

with col_bottom:
    st.subheader(f"Bottom 5 by Growth % ({selected_year})")
    bottom5 = year_summary.nsmallest(5, "growth_pct")
    fig_bottom = px.bar(bottom5, x="growth_pct", y="Name", orientation="h", color="growth_pct",
                         color_continuous_scale="Reds_r")
    fig_bottom.update_layout(height=320, margin=dict(t=10, b=10), showlegend=False, coloraxis_showscale=False)
    fig_bottom.update_yaxes(categoryorder="total descending")
    st.plotly_chart(fig_bottom, use_container_width=True)

st.markdown("---")

# ----------------------------
# Risk / Return Scatter (deliberately shows ALL 505 stocks, decoupled from slicers
# — mirrors the Edit Interactions decision made in the original Power BI dashboard)
# ----------------------------
st.subheader("Risk / Return — All 505 Stocks")
st.caption("Always shows the full dataset, independent of the stock and year filters above — same design choice as the Power BI version, so outliers like NVDA remain visible in context.")

fig_scatter = px.scatter(
    summary, x="avg_volatility", y="growth_pct", hover_name="Name",
    labels={"avg_volatility": "Avg Daily Volatility (%)", "growth_pct": "5-Year Growth (%)"},
    opacity=0.6,
)
# Highlight the currently selected stock
sel = summary[summary["Name"] == selected_stock]
fig_scatter.add_trace(
    go.Scatter(
        x=sel["avg_volatility"], y=sel["growth_pct"], mode="markers+text",
        text=[selected_stock], textposition="top center",
        marker=dict(size=14, color="red", symbol="star"),
        name=selected_stock, showlegend=False,
    )
)
fig_scatter.update_layout(height=450, margin=dict(t=10, b=10))
st.plotly_chart(fig_scatter, use_container_width=True)

# ----------------------------
# Footer / insight callout
# ----------------------------
st.info(
    "**Key insight:** NVDA delivered the strongest 5-year return (1749.64%) without sitting at "
    "the extreme end of the volatility range — visually reinforcing the near-zero correlation "
    "(r ≈ 0.08) found between trading volume and price movement in the underlying SQL analysis."
)
