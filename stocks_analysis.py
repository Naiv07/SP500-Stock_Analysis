import pandas as pd
import sqlite3

df = pd.read_csv(r"C:\Users\troos\OneDrive\Documents\Projects\Stocks Analysis\all_stocks_5yr.csv")
df['date'] = pd.to_datetime(df['date'], format = "%d-%m-%Y").dt.date
df = df.dropna(subset = ['high', 'low', 'open' , 'close'])

conn = sqlite3.connect('stocks_analysis.db')
df.to_sql('stock_prices', conn, index= False, if_exists = 'replace')

print('Done. Rows loaded!', len(df))

print('\n')
res = pd.read_sql_query("""Select * 
                        from stock_prices 
                        limit 10""", conn)
print(res)

print('\n')
summary = pd.read_sql_query("""select min(date) as start_date, max(date) as end_date, count(distinct name) as num_of_comp 
                            from stock_prices""", conn)
print(summary)

print('\n')
close = pd.read_sql_query("""select name, round(avg(close),2) as avg_close 
                          from stock_prices 
                          group by name
                          order by avg_close desc 
                          limit 1""", conn)
print(close)

print('\n')
avg_volatility = pd.read_sql_query("""select name , round(avg((high - low) / low * 100),2) as avg_intraday_volatility 
                                   from stock_prices 
                                   group by name 
                                   order by avg_intraday_volatility desc 
                                   limit 1""", conn)
print(avg_volatility)

print('\n')
highest_price_range = pd.read_sql_query("""select name, round((max(close) - min(close)) / (min(close) * 100),2) as highest_price_range 
                                        from stock_prices 
                                        group by name 
                                        order by highest_price_range desc 
                                        limit 1""", conn)
print(highest_price_range)

print('\n')
q3 = pd.read_sql_query(
    """with cte as(select name, date, close, 
            first_value(close) over (partition by name order by date asc) as first_close,
            first_value(close) over (partition by name order by date desc) as last_close
        from stock_prices
        )
    select distinct name, round((first_close),2) as first_close, round((last_close),2) as last_close ,
    round(((last_close - first_close) / first_close * 100),2) as growth_pct 
    from cte
    order by growth_pct desc
    """,
    conn
)
print(q3.head(10))

print('\n')
cor = pd.read_sql_query("""
                        select name, date, volume, 
                        round(abs((close - open) / open * 100),2) as price_change_pct
                        from stock_prices
                        """,
                        conn)
core = df['volume'].corr(cor['price_change_pct'])
print("Correlation b/w price changes vs. volume : ",round(core,2))

print('\n')
high_voli = pd.read_sql_query(""" 
                              select strftime('%Y -%m', date) as yr_month,
                              round(avg((high - low) / low * 100),2) as avg_volatility
                              from stock_prices
                              group by yr_month
                              order by avg_volatility desc
                              limit 5""",
                              conn
                              )
print("The highest months of volatility across the dataset:\n",high_voli)

export = df.to_csv(r"C:\Users\troos\OneDrive\Documents\Projects\Stocks Analysis\stocks_analysis.csv")