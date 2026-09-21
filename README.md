# S&P 500 Stock Analysis Project — Documentation

## Project Overview
**Dataset:** S&P 500 historical daily stock prices (5 years) — `all_stocks_5yr.csv`
**Source:** [Kaggle - S&P 500 stock data](https://www.kaggle.com/datasets/camnugent/sandp500)
**Columns:** date, open, high, low, close, volume, Name (ticker symbol)

**Goal:** Build a SQL + Power BI heavy portfolio project (second project, different domain from the Zomato restaurant analysis) demonstrating:
- SQL querying against a real dataset
- Power BI dashboard development
- Business insight generation from financial/stock data

---

## Tech Stack Decision

### Why SQLite instead of MySQL
- Attempted local MySQL Server setup first — ran into extended configuration issues:
  - MySQL Workbench showed "offline" — server wasn't listening on expected port
  - Found server was running on port 3307 instead of default 3306
  - Root password authentication kept failing
  - Attempted safe-mode password reset (`--skip-grant-tables`) — ran into datadir path issues
  - Eventually did a clean reinstall of MySQL Community Server
  - After reinstall, hit `secure_file_priv` restriction blocking `LOAD DATA INFILE` from the project folder
- **Decision:** Switched to SQLite via Python instead — serverless, no configuration, same SQL syntax for the queries this project needs (SELECT, JOIN, GROUP BY, window functions)
- MySQL/PostgreSQL are built for production multi-user systems; SQLite is the standard, appropriate choice for local single-person analysis projects

---

## Steps Completed

### 1. Data Loading (Python + SQLite)
```python
import pandas as pd
import sqlite3

df = pd.read_csv(r'C:\Users\troos\OneDrive\Documents\Projects\Stocks Analysis\all_stocks_5yr.csv')

# Convert date column to proper datetime (original format was DD-MM-YYYY), strip time component
df['date'] = pd.to_datetime(df['date'], format='%d-%m-%Y').dt.date

conn = sqlite3.connect('stock_analysis.db')
df.to_sql('stock_prices', conn, index=False, if_exists='replace')

print("Done. Rows loaded:", len(df))
```

**Result:** 619,040 rows loaded successfully.

**Data range confirmed:**
- Start date: 2013-02-08
- End date: 2018-02-07
- Companies: 505 (full S&P 500 coverage)
- 5 years of daily data

---

## SQL Queries & Findings

### Q1: Which stock had the highest average closing price?
```python
close = pd.read_sql_query(
    'SELECT Name, AVG(close) AS avg_close FROM stock_prices GROUP BY Name ORDER BY avg_close DESC LIMIT 1',
    conn
)
```

**Result:** PCLN (Priceline) — avg_close = $1,312.87

**Insight:** Priceline traded at unusually high per-share prices compared to the rest of the S&P 500 throughout this period (before its 2018 rebrand to Booking Holdings), reflecting the company's decision not to split its stock.

---

### Q2a: Which stock had the highest average intraday volatility?
```python
avg_volatility = pd.read_sql_query(
    "SELECT Name, AVG((high - low) / low * 100) AS avg_intraday_volatility FROM stock_prices GROUP BY Name ORDER BY avg_intraday_volatility DESC LIMIT 1",
    conn
)
```

**Result:** CHK (Chesapeake Energy) — avg_intraday_volatility = 4.89%

**Insight:** Chesapeake Energy, an oil & gas company, had the highest average daily price swing — consistent with energy sector stocks being highly sensitive to commodity price fluctuations during this period (2013-2018 included the 2014-2016 oil price crash).

**Debugging note:** Initial query returned an implausible 1224% for PCLN due to an operator precedence bug — `AVG(high - low / low * 100)` was missing parentheses around `(high - low)`, causing SQL to calculate `low / low` (always 1) before the subtraction, rather than the intended `(high - low) / low`. Corrected to `AVG((high - low) / low * 100)`. This is a good reminder to always verify aggregate results against manual spot-checks before trusting them.

---

### Q3: Which stock had the highest cumulative growth (first close vs last close)?
```python
q3 = pd.read_sql_query(
    """
    WITH cte AS (
        SELECT Name, date, close,
               FIRST_VALUE(close) OVER (PARTITION BY Name ORDER BY date ASC) AS first_close,
               FIRST_VALUE(close) OVER (PARTITION BY Name ORDER BY date DESC) AS last_close
        FROM stock_prices
    )
    SELECT DISTINCT Name, first_close, last_close,
           (last_close - first_close) / first_close * 100 AS growth_pct
    FROM cte
    ORDER BY growth_pct DESC
    """,
    conn
)
```

**Result — Top 10 by cumulative growth:**
| Stock | First Close | Last Close | Growth % |
|---|---|---|---|
| NVDA | $12.37 | $228.80 | 1749.64% |
| NFLX | $25.85 | $264.56 | 923.33% |
| ALGN | $32.73 | $234.33 | 615.95% |
| EA | $17.37 | $123.05 | 608.41% |
| STZ | $31.85 | $214.15 | 572.37% |
| AVGO | $35.32 | $237.38 | 572.08% |
| FB | $28.55 | $180.18 | 531.21% |
| MU | $7.75 | $42.01 | 442.06% |
| AMZN | $261.95 | $1416.78 | 440.86% |
| ATVI | $13.41 | $69.46 | 417.97% |

**Insight:** NVIDIA delivered the strongest investor returns in the S&P 500 over this period — a ~17.5x return from 2013 to 2018, driven by GPU demand for gaming and cryptocurrency mining, ahead of the AI boom that would later push it even higher. This confirms and extends the finding from Q2b (price range) — NVDA wasn't just volatile in range, it genuinely compounded value for long-term holders. Notably, streaming (NFLX), tech (FB, AMZN), and semiconductors (AVGO, MU) dominate the top growth list, reflecting the broader 2013-2018 tech sector expansion.

**Technical note:** Used `FIRST_VALUE()` window functions with opposite `ORDER BY` directions (ASC for first chronological close, DESC for last) rather than correlated subqueries — cleaner and more efficient for this per-stock "first/last" pattern.

---

### Q4: Is there a correlation between trading volume and price movement?
```python
data = pd.read_sql_query(
    """
    SELECT Name, date, volume,
           ABS((close - open) / open * 100) AS price_change_pct
    FROM stock_prices
    """,
    conn
)

correlation = data['volume'].corr(data['price_change_pct'])
print("Correlation between volume and price change:", correlation)
```

**Result:** Correlation = 0.08 (very weak)

**Insight:** Contrary to common assumption, high trading volume does NOT strongly predict large price swings across the S&P 500. A correlation of 0.08 (on a scale of -1 to +1) indicates almost no meaningful relationship — stocks can experience heavy trading volume with minimal price change, or significant price swings on comparatively modest volume. This challenges the popular retail-investor intuition that "high volume signals a big move."

**Technical note:** SQLite lacks a built-in `CORR()` function (unlike MySQL/PostgreSQL), so the raw data was pulled via SQL and correlation was calculated using pandas' `.corr()` method. `ABS()` was applied to price change % since direction (up/down) is irrelevant to this question — only the magnitude of movement matters when comparing against volume.

---

### Q5: Which month had the highest overall market volatility?
```python
q5 = pd.read_sql_query(
    """
    SELECT strftime('%Y-%m', date) AS year_month,
           AVG((high - low) / low * 100) AS avg_volatility
    FROM stock_prices
    GROUP BY year_month
    ORDER BY avg_volatility DESC
    LIMIT 5
    """,
    conn
)
```

**Result — Top 5 most volatile months (across all 505 stocks):**
| Month | Avg Volatility |
|---|---|
| Feb 2018 | 3.75% |
| Jan 2016 | 3.36% |
| Feb 2016 | 3.19% |
| Aug 2015 | 2.81% |
| Oct 2015 | 2.48% |

**Insight:** The most volatile months align precisely with well-documented real-world market events: February 2018 corresponds to "Volmageddon" (a sudden volatility spike and market correction); January-February 2016 reflects the global selloff driven by crashing oil prices and China economic slowdown fears; August 2015 corresponds to China's stock market crash and yuan devaluation, which triggered a global selloff. This confirms the dataset accurately captures real market history, not just abstract price movements.

**Technical note:** Used SQLite's `strftime('%Y-%m', date)` to extract year-month from the date column — SQLite's equivalent of MySQL's `DATE_FORMAT()` or PostgreSQL's `TO_CHAR()`.

---

### Q2b: Which stock had the widest overall price range across the period?
```python
price_range = pd.read_sql_query(
    'SELECT Name, (MAX(close) - MIN(close)) / MIN(close) * 100 AS ovr_price_range FROM stock_prices GROUP BY Name ORDER BY ovr_price_range DESC LIMIT 1',
    conn
)
```

**Result:** NVDA — ovr_price_range = 1935.7%

**Verified:** MIN(close) = $12.13, MAX(close) = $246.85

**Insight:** NVIDIA grew nearly 20x over the 5-year period (2013-2018), driven by GPU demand for gaming and early cryptocurrency mining — well before the AI boom that later propelled it further. This is the strongest organic growth story in the dataset.

---

### Export: Summary table for Excel / Power BI dashboard
```python
summary_report = pd.read_sql_query(""" with cte as(
                                   select name, close, date,
                                   first_value(close) over (partition by name order by date asc) as first_close,
                                   first_value(close) over (partition by name order by date desc) as last_close,
                                   avg(close) over (partition by name) as Avg_close,
                                   avg((high - low) / low * 100) over (partition by name) as Avg_Volatility 
                                   from stock_prices
                                   )
                                   select distinct name, Avg_close, Avg_Volatility, first_close, last_close, 
                                   round((last_close - first_close) / first_close * 100 , 2) as Growth_pct
                                   from cte
                                   order by Growth_pct desc
                                   """, 
                                   conn
                                   )
with pd.ExcelWriter("stock_analysis_dashboard.xlsx") as writer:
    summary_report.to_excel(writer, sheet_name='Summary', index=False)
    df.to_excel(writer, sheet_name='DailyData', index=False)
```

**Purpose:** Builds a per-stock `Summary` sheet (avg close, avg volatility, first/last close, growth %) computed via SQL window functions, alongside the full `DailyData` sheet — exported to `stock_analysis_dashboard.xlsx` as the working file for the Excel dashboard and the source connected to Power BI.

---

## Business Questions to Answer (SQL)
1. Which stock had the highest average closing price over the 5-year period?
2. Which stock was the most volatile (highest daily % price swing)?
3. Which company had the best cumulative growth from start to end date?
4. What's the correlation between trading volume and price movement?
5. Which month had the highest overall market volatility?

## Planned SQL Techniques
- `LAG()` — day-over-day price change calculation
- `STDDEV()` / manual variance calc — volatility measurement
- `strftime()` (SQLite's date formatting function) + `GROUP BY` — monthly aggregation
- Window functions for running totals / cumulative growth
- CTEs to chain multi-step calculations

---

## Next Steps
- [ ] Write and verify each SQL business question query
- [ ] Export query results for Power BI
- [ ] Connect Power BI to SQLite (or export to CSV as bridge if direct connection isn't straightforward)
- [ ] Build dashboard: trend line, volatility bar chart, KPI cards, cross-filtering
- [ ] Write insights and push to GitHub with README
