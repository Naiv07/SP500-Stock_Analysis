# S&P 500 Stock Analysis Project — Documentation

## Project Overview
**Dataset:** S&P 500 historical daily stock prices (5 years) — `all_stocks_5yr.csv`
**Source:** [Kaggle - S&P 500 stock data](https://www.kaggle.com/datasets/camnugent/sandp500)
**Columns:** date, open, high, low, close, volume, Name (ticker symbol)

**Goal:** Build a SQL + Power BI heavy portfolio project (second project, different domain from the Zomato restaurant analysis) demonstrating:
- SQL querying against a real dataset
- Excel dashboard development
- Power BI dashboard development with a proper data model
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

## Part 1 — Data Loading (Python + SQLite)

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

## Part 2 — SQL Queries & Findings

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

### Export: Summary table for Excel / Power BI dashboard
```python
summary_report = pd.read_sql_query("""
    WITH cte AS (
        SELECT Name, close, date,
               FIRST_VALUE(close) OVER (PARTITION BY Name ORDER BY date ASC) AS first_close,
               FIRST_VALUE(close) OVER (PARTITION BY Name ORDER BY date DESC) AS last_close,
               AVG(close) OVER (PARTITION BY Name) AS Avg_close,
               AVG((high - low) / low * 100) OVER (PARTITION BY Name) AS Avg_Volatility
        FROM stock_prices
    )
    SELECT DISTINCT Name, Avg_close, Avg_Volatility, first_close, last_close,
           ROUND((last_close - first_close) / first_close * 100, 2) AS Growth_pct
    FROM cte
    ORDER BY Growth_pct DESC
    """,
    conn
)
with pd.ExcelWriter("stock_analysis_dashboard.xlsx") as writer:
    summary_report.to_excel(writer, sheet_name='Summary', index=False)
    df.to_excel(writer, sheet_name='DailyData', index=False)
```

**Purpose:** Builds a per-stock `Summary` sheet (avg close, avg volatility, first/last close, growth %) computed via SQL window functions, alongside the full `DailyData` sheet — exported to `stock_analysis_dashboard.xlsx` as the working file for the Excel dashboard and the source connected to Power BI.

---

## Part 3 — Excel Dashboard

### KPI Selector Panel (Sheet1)
Built a single-stock, year-by-year breakdown table driven by a name-input cell (`$H$7`), showing average open, average close, first closing value, and last closing value per year (2013–2018).

**Average open / close:**
```
Average of open  = AVERAGEIFS(Table2[open], Table2[Name], $H$7, Table2[Year], VALUE(G10))
Average of close = AVERAGEIFS(Table2[close], Table2[Name], $H$7, Table2[Year], VALUE(G10))
```

**First / last closing value:**
```
First closing value = INDEX(Table2[close], MATCH(1, (Table2[Name]=$H$7)*(Table2[date]=MINIFS(Table2[date],Table2[Name],$H$7,Table2[Year],VALUE(G10))), 0))

Last closing value = INDEX(Table2[close], MATCH(1, (Table2[Name]=$H$7)*(Table2[date]=MAXIFS(Table2[date],Table2[Name],$H$7,Table2[Year],VALUE(G10))), 0))
```
(entered as array formulas)

**Debugging note:** First attempt used `MINIFS`/`MAXIFS` directly on the `close` column — `MINIFS(Table2[close], Table2[Name], $H$7, Table2[Year], VALUE(G10))`. This returns the **lowest/highest closing price of the year**, not the close on the **first/last trading day** of the year — two different things. A stock can dip mid-year below its year-end close, which would silently misreport "first close" as the year's low instead of January's actual close. Fixed by first finding the min/max **date** for that stock/year, then using `INDEX/MATCH` to pull the `close` value at that exact date. Verified against the SQL-derived `Summary` sheet: NVDA's 2013 first close ($12.37) and 2018 last close ($228.80) matched exactly.

### Supporting column
Added a calculated `Year` column to `DailyData` (`=YEAR(Table2[[#This Row],[date]])`) to enable the year-level `AVERAGEIFS`/`MINIFS`/`MAXIFS` filtering above, without altering the SQL-exported source data.

---

## Part 4 — Power BI Data Model

### Why rebuild in Power BI rather than import the Excel `Summary` sheet directly
`Summary` contains pre-aggregated, frozen values computed once in Excel (e.g. NVDA's overall `Growth_pct` = 1749.64%, fixed across the full 2013–2018 range). If imported as-is, it wouldn't respond to slicers — a report filtered to 2016 would still display the full-range number, silently wrong. Decision: import only `DailyData` as the single source of truth, and recompute every KPI as a DAX measure so it responds live to whatever's filtered.

### Star schema
- **Fact table:** `DailyData` — one row per stock per trading day (date, open, high, low, close, volume, Name, Year)
- **Dimension: `Stocks`** — distinct list of 505 tickers, built via Power Query (duplicate `DailyData` → keep only `Name` → Remove Duplicates). Related to `DailyData[Name]`, cardinality **Many-to-one**, single cross-filter direction.
- **Dimension: `Dates`** — standalone calendar table, built with a DAX calculated table:
  ```
  Dates = CALENDARAUTO()
  ```
  Marked as an official date table (required for time-intelligence functions to work correctly). Related to `DailyData[date]`, cardinality **Many-to-one**.
  Calculated columns added on top:
  ```
  Year    = YEAR(Dates[Date])
  Quarter = QUARTER(Dates[Date])
  Month   = MONTH(Dates[Date])
  ```

**Debugging note:** The raw `DailyData[Year]` column (carried over from Excel) defaults to Sum as its aggregation type in Power BI, since it's numeric. Left unchanged, dragging it into any visual would silently sum year values across rows (e.g. "8,066,051" instead of "2017") instead of behaving as a label. Fixed by setting its Default Summarization to "Don't summarize." This became less relevant once the proper `Dates` dimension was built, but is a common first-project trap worth documenting.

---

## Part 5 — DAX Measures

All measures built on the `DailyData` fact table, using the `VAR`/`RETURN` pattern for readability and to sidestep an intermittent Power BI editor bug (a "PLACEHOLDER" compile error) encountered with deeply nested inline filter arguments.

```
First Close Date = MIN(DailyData[date])

First Close =
VAR FCDate = [First Close Date]
RETURN
CALCULATE(SUM(DailyData[close]), DailyData[date] = FCDate)

Last Close Date = MAX(DailyData[date])

Last Close =
VAR LCDate = [Last Close Date]
RETURN
CALCULATE(SUM(DailyData[close]), DailyData[date] = LCDate)

Growth % = DIVIDE([Last Close] - [First Close], [First Close])
```

**Daily Volatility (calculated column on `DailyData`):**
```
Daily Volatility = ROUND(DIVIDE(DailyData[high] - DailyData[low], DailyData[low]) * 100, 2)
```

**Avg Volatility (measure):**
```
Avg Volatility = AVERAGE(DailyData[Daily Volatility])
```

**Why `Avg Volatility` needed a column first, not just a measure:** the metric is "average of each day's individual `(high-low)/low` ratio" — not "(sum of all highs − sum of all lows) / sum of all lows" computed once over the whole filtered range. Those two produce different numbers (summing first and dividing once is not equivalent to averaging a set of individual ratios). The per-row `Daily Volatility` column computes the correct daily figure first; the measure then averages across whatever's filtered.

All measures verified against the SQL-derived `Summary` sheet values before being used in visuals (e.g. NVDA's `First Close`/`Last Close` matched Q3's SQL result of $12.37 / $228.80 exactly).

---

## Part 6 — Power BI Dashboard Visuals

| Visual | Fields | Notes |
|---|---|---|
| KPI Cards ×4 | `First Close`, `Last Close`, `Growth %`, `Avg Volatility` | Meaningful only when filtered to one stock via the `Stocks[Name]` slicer |
| Top 5 Growth % (bar) | `Stocks[Name]` axis, `Growth %` value, Top N filter (Top 5 by Growth %) | Dynamically re-ranks per selected `Year` |
| Bottom 5 Growth % (bar) | Same, Top N filter set to Bottom 5 | Dynamically re-ranks per selected `Year` |
| Risk/Return Scatter | X: `Avg Volatility`, Y: `Growth %`, one dot per `Stocks[Name]` | Decoupled from the `Name`/`Year` slicers via Edit Interactions, so it always shows all 505 stocks |
| Trend Line | X: `Dates[Year]`, Y: `Last Close` + `First Close` | Stays connected to the `Name` slicer — single-stock trajectory |
| Volume Trend | X: `Dates[Year]`, Y: Average of `volume` | Connected to both slicers |
| Slicers | `Stocks[Name]`, `Dates[Year]` | |

**Debugging note (slicer interactions):** By default, every visual on a Power BI page responds to every slicer. This initially collapsed the Top 5/Bottom 5 and scatter visuals down to whatever single stock was selected in the `Name` slicer (e.g. "Top 5 by Growth %" computed over a filtered set of 1 stock). Fixed using Edit Interactions to set the slicer's effect on those specific visuals to "None," so ranking/distribution visuals stay computed across the full dataset while the KPI cards and trend line remain slicer-responsive.

**Design note:** The Top 5/Bottom 5 charts were deliberately left connected to the `Year` slicer (a later decision, reversing the interaction fix above for that slicer specifically) so they answer "who performed best in a given year," rather than only showing the fixed 2013–2018 all-time ranking — titled accordingly so the two meanings aren't confused.

---

## Key Insight
NVDA is the standout outlier in the risk/return scatter — high `Growth %` (1749.64%) achieved without correspondingly extreme `Avg Volatility` relative to the rest of the dataset — visually supporting the finding (also reached independently via SQL correlation analysis, r ≈ 0.08) that high volatility does not reliably predict high returns across the S&P 500.

---

## Business Insights & Recommendations

### Insights
- **Growth was heavily sector-concentrated.** The top 5 performers by cumulative growth (NVDA, NFLX, ALGN, EA, STZ) are dominated by tech, streaming, and consumer names, reflecting the broader 2013–2018 tech sector expansion. The bottom 5 (DISCK, DISCA, UA, RRC, CHK) skew toward legacy media and energy — sectors that faced structural disruption (cord-cutting) or commodity price shocks (2014–2016 oil crash) over this same window.
- **High return did not require extreme volatility.** NVDA delivered the strongest 5-year return in the dataset (1749.64%, ~17.5x) while sitting in a moderate volatility range compared to other stocks in the risk/return scatter — not the most volatile stock in the dataset. This is reinforced by the near-zero SQL correlation (r ≈ 0.08) between trading volume and daily price-change magnitude: heavy trading activity did not reliably signal large price swings.
- **Volatility clustered around real macro events, not randomly.** The five most volatile months in the dataset (Feb 2018, Jan/Feb 2016, Aug 2015, Oct 2015) map directly onto documented market shocks — "Volmageddon" (Feb 2018), the oil price collapse and China slowdown fears (early 2016), and China's stock market crash/yuan devaluation (Aug 2015). Volatility spikes were event-driven, not evenly distributed across the 5-year period.
- **Absolute share price is a poor standalone signal.** PCLN (Priceline) had by far the highest average closing price ($1,312.87), but this reflects the company's choice not to split its stock rather than superior performance — a reminder that price level alone doesn't indicate return quality.

### Recommendations
- **Don't use volatility or volume as a standalone proxy for return potential.** The weak volume/price-change correlation and NVDA's moderate-volatility/high-growth profile both suggest that risk metrics in isolation are poor predictors here — return drivers (sector trends, company fundamentals) matter more than short-term price/volume noise.
- **Treat sector exposure as a primary lens for this period's results.** Given how concentrated both the top and bottom performers were by sector, a portfolio strategy informed by this data alone should weight sector trend analysis (tech/streaming growth vs. legacy media/energy disruption) over individual stock volatility screening.
- **Anchor volatility analysis to known macro events when interpreting spikes.** Since the highest-volatility months line up with identifiable market shocks, future monitoring should flag macro catalysts (rate decisions, commodity shocks, geopolitical events) rather than treating volatility spikes as noise to be filtered out.
- **Extend the analysis with fundamentals data.** This dataset (price/volume only) can show *what* happened but not fully *why* — a natural next step would be joining in earnings, P/E, or sector classification data to test whether growth was fundamentals-driven or momentum-driven, particularly for the top/bottom-5 performers.

---

## Business Questions Answered
1. ✅ Which stock had the highest average closing price over the 5-year period? — PCLN
2. ✅ Which stock was the most volatile (highest daily % price swing)? — CHK
3. ✅ Which company had the best cumulative growth from start to end date? — NVDA
4. ✅ What's the correlation between trading volume and price movement? — 0.08 (very weak)
5. ✅ Which month had the highest overall market volatility? — Feb 2018

## Tech Stack
- **Python** — pandas, sqlite3 (data loading and cleaning)
- **SQL (SQLite)** — window functions, CTEs, aggregations
- **Excel** — Power Pivot, Power Query, array formulas, dynamic dashboard
- **Power BI** — star schema data model, DAX measures, cross-filtered dashboard

## Next Steps
- [ ] Final polish pass on Power BI dashboard formatting/titles
- [ ] Push `.pbix` file and dashboard screenshots to GitHub
- [ ] Write final insights summary for portfolio README
