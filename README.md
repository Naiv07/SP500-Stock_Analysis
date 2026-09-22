# 📈 S&P 500 Stock Analysis

![Power BI Dashboard](Screenshot%202026-09-22%20224046.png)

# Objective

In this project, I have analyzed 5 years of S&P 500 daily stock price data to understand which stocks delivered the strongest returns, which were the most volatile, and whether trading volume actually predicts price movement:

1. Extracted the S&P 500 dataset to identify top-performing and most volatile stocks, and to test the common assumption that high trading volume signals big price swings.
2. Modeled the data using Python and SQL (SQLite) on VS Code, after an initial local MySQL setup proved unworkable for this project's scope.
3. Using cleaning and validation methods, I identified and corrected null rows, a date-format bug, and a query logic bug before trusting any result.
4. Generated observations, an Excel dashboard, and a Power BI dashboard with a proper star-schema data model.

As this is a data analysis project, my emphasis is primarily on cleaning, query correctness, and generating key observations and analytics.

The sections below will explain additional details on the technologies and files utilized.

# Table of Content

- [Problem Statement](#problem-statement)
- [Dataset Used](#dataset-used)
- [Tools Used](#tools-used)
- [Data Cleaning](#data-cleaning)
- [Key Findings](#key-findings)
- [Excel Dashboard](#excel-dashboard)
- [Power BI Dashboard](#power-bi-dashboard)
- [Suggestions & Business Recommendations](#suggestions--business-recommendations)
- [Limitations](#limitations)

## Problem Statement

Investors and analysts often rely on intuition — "high volume means a big move," "high volatility means high returns" — rather than a clear, data-backed analysis of what actually drove returns in the S&P 500. Using this dataset, I will showcase how the data was cleaned and validated, which stocks and sectors actually delivered the strongest and weakest performance between 2013 and 2018, and whether volume and volatility are reliable predictors of return.

## Dataset Used

This project uses the Kaggle dataset of S&P 500 historical daily stock prices, covering 5 years (2013–2018) of open, high, low, close, and volume data for all 505 companies in the index at the time.

More info about the dataset can be found here:
- Website: [Kaggle - S&P 500 stock data](https://www.kaggle.com/datasets/camnugent/sandp500)

## Tools Used

The following technologies are used to build this project:

- **Language:** Python
- **Libraries:** Pandas, sqlite3, openpyxl
- **Database:** SQLite (window functions, CTEs, aggregations)
- **Environment:** VS Code
- **Dashboard:** Microsoft Excel (Power Pivot, Power Query, AVERAGEIFS, MINIFS/MAXIFS, INDEX/MATCH array formulas)
- **Dashboard:** Power BI (star schema data model, DAX measures)
- **Data Source:** Kaggle
- **Version Control:** Git & GitHub

## Data Cleaning

In this step, I loaded the CSV file into Python and carried out cleaning and validation activities before loading the data into SQLite for analysis.

Here's the specific cleaning and debugging work that was performed:

1. Converted the `date` column from its original DD-MM-YYYY string format into a proper date type, and stripped the time component that appeared after conversion.
2. Dropped 8 rows with null `high`/`low`/`open`/`close` values out of 619,040 total rows.
3. Attempted a local MySQL Server setup first, but hit extended configuration issues (wrong port, failed authentication, `secure_file_priv` restrictions blocking `LOAD DATA INFILE`). Switched to SQLite via Python instead, since it's serverless and sufficient for this project's single-user scope.
4. Caught and fixed an operator precedence bug in the volatility formula — `AVG(high - low / low * 100)` (missing parentheses) was silently returning an impossible 1224% for PCLN, instead of the correct `AVG((high - low) / low * 100)`. Verified the fix by manually spot-checking the underlying rows before trusting the corrected result.
5. In the Excel dashboard, caught a second logic bug: using `MINIFS`/`MAXIFS` directly on the `close` column returns the year's lowest/highest closing *price*, not the close on the year's first/last *trading day* — two different things. Fixed by finding the min/max `date` first, then using `INDEX/MATCH` to pull the `close` at that exact date, and verified the result against the SQL-derived summary.

## Key Findings

After completing the above steps I ran SQL queries and generated observations from the results as insights.

1. **Highest average closing price**
   PCLN (Priceline) had the highest average closing price over the 5-year period at $1,312.87. This reflects the company's decision not to split its stock, rather than superior performance — a reminder that price level alone doesn't indicate return quality.

2. **Highest average intraday volatility**
   CHK (Chesapeake Energy) had the highest average day-to-day price swing at 4.89%, consistent with energy sector stocks being highly sensitive to commodity price swings during this period, which included the 2014–2016 oil price crash.

3. **Widest overall price range**
   NVDA had the widest price range across the period at 1935.7%, growing from a low of $12.13 to a high of $246.85 — driven by GPU demand for gaming and early cryptocurrency mining, well before the AI boom that would later push it even further.

4. **Highest cumulative growth (first close vs last close)**
   NVDA again led with 1749.64% growth ($12.37 → $228.80), a ~17.5x return for investors who held throughout. NFLX (923%), ALGN (616%), EA (608%), and other tech/consumer names dominate the top 10, reflecting the broader 2013–2018 tech sector expansion.

5. **Correlation between trading volume and price movement**
   Correlation = 0.08 — essentially no meaningful relationship. Contrary to the common assumption that heavy trading volume signals a big price move, this dataset shows stocks can trade heavily with minimal price change, or swing significantly on comparatively modest volume.

6. **Most volatile months market-wide**
   The five most volatile months (Feb 2018, Jan 2016, Feb 2016, Aug 2015, Oct 2015) line up precisely with real market events: "Volmageddon" (Feb 2018), the oil price collapse and China slowdown fears (early 2016), and China's stock market crash and yuan devaluation (Aug 2015) — confirming volatility spikes were event-driven, not random.

## Excel Dashboard

Built a single-stock, year-by-year dashboard with:

- Name-input selector cell driving all metrics for a chosen stock
- Average open and average close per year (`AVERAGEIFS`)
- First and last closing value per year, found via `INDEX/MATCH` against the min/max trading date for that year (not simply the year's lowest/highest price — see Data Cleaning above)
- Built on top of a `Summary` sheet and full `DailyData` sheet exported directly from the SQL analysis, linked via Power Pivot's Data Model for combined reporting

![Excel Dashboard](Screenshot%202026-09-22%20223917.png)

## Power BI Dashboard

Rebuilt the analysis as a proper star schema rather than importing the frozen Excel summary values, so every KPI recalculates live as the report is filtered:

- **Fact table:** `DailyData` — one row per stock per trading day
- **Dimension tables:** `Stocks` (505 distinct tickers, built via Power Query) and `Dates` (a standalone `CALENDARAUTO()` calendar table, marked as the official date table)
- **DAX measures:** `First Close`, `Last Close`, `Growth %`, and a per-row `Daily Volatility` column averaged into `Avg Volatility` — calculated as the average of each day's individual ratio, not a single ratio of summed highs/lows (the two give different, non-equivalent numbers)

**Visuals:**
- 4 KPI cards (First Close, Last Close, Growth %, Avg Volatility) — respond to the stock slicer
- Top 5 / Bottom 5 Growth % bar charts — re-rank dynamically per selected year
- Risk/Return scatter (Avg Volatility vs Growth %, one dot per stock) — deliberately disconnected from the slicers via Edit Interactions, so it always shows all 505 stocks at once
- Price trend line and volume trend, both responsive to the stock slicer
- Stock name and year slicers

![Power BI Dashboard — default view](Screenshot%202026-09-22%20230037.png)

The Top 5/Bottom 5 charts and trend line are fully interactive — selecting a stock and year re-ranks and re-filters every visual on the page:

![Power BI Dashboard — filtered to GOOGL, 2013](Screenshot%202026-09-22%20224430.png)

**Key visual insight:** NVDA is the standout outlier in the risk/return scatter — high `Growth %` (1749.64%) achieved without correspondingly extreme `Avg Volatility` — visually confirming the same finding reached independently through the SQL correlation analysis (r ≈ 0.08).

## Suggestions & Business Recommendations

1. **Don't use volatility or trading volume as a standalone proxy for return potential.** The near-zero volume/price-change correlation (0.08) and NVDA's moderate-volatility/high-growth profile both show that short-term risk metrics, taken alone, are poor predictors of return in this dataset — underlying company and sector fundamentals matter more.

2. **Weight sector exposure heavily when interpreting this period's winners and losers.** Growth was concentrated in tech, streaming, and consumer names (NVDA, NFLX, ALGN, EA), while the weakest performers skewed toward legacy media and energy — sectors facing structural disruption (cord-cutting) or commodity shocks (the 2014–2016 oil crash) over the same window.

3. **Anchor volatility monitoring to known macro catalysts, not treat spikes as noise.** Since the five most volatile months map directly onto identifiable market events, future analysis should flag scheduled catalysts (rate decisions, commodity shocks, geopolitical events) rather than filtering volatility out as randomness.

4. **Extend the analysis with fundamentals data before drawing investment conclusions.** Price and volume data alone can show *what* happened but not fully *why* — joining in earnings, P/E, or sector classification data would help test whether the top/bottom performers' moves were fundamentals-driven or momentum-driven.

## Limitations

**Dataset limitations:**
- Covers only 2013–2018; more recent market behavior (including NVDA's later AI-driven rally) is not captured
- Price and volume only — no fundamentals (earnings, P/E, revenue) to explain *why* a stock moved, only that it did
- Limited to the 505 companies that were in the S&P 500 during this window; index composition changes over time aren't reflected

**Analytical limitations:**
- Correlation between volume and price movement doesn't rule out more complex, non-linear relationships that a simple Pearson correlation wouldn't capture
- "Most volatile month" and "highest growth stock" findings are descriptive, not causal — they identify *what* happened, not a tested explanation of *why*
