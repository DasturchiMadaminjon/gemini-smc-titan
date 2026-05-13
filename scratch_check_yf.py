import yfinance as yf
import pandas as pd

ticker = "XAUUSD=X"
interval = "15m"
period = "60d"

tk = yf.Ticker(ticker)
df = tk.history(period=period, interval=interval)

print(f"Ticker: {ticker}")
print(f"Columns: {df.columns.tolist()}")
print(f"First 5 rows:\n{df.head()}")
