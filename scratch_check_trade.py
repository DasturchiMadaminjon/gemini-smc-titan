import yfinance as yf
import pandas as pd

tk = yf.Ticker("GC=F")
df = tk.history(interval="5m", period="5d")

if df.index.tzinfo is None:
    df.index = df.index.tz_localize('UTC')
else:
    df.index = df.index.tz_convert('UTC')

target_time = pd.to_datetime("2026-05-12 16:55:00+00:00")
df_filtered = df[df.index >= target_time]

entry = 4674.6
sl = 4790.5
tp1 = 4500.8

print("--- TRADE ANALYSIS ---")
print(f"Start time: {target_time}")
print(f"Entry: {entry}")
print(f"SL: {sl}")
print(f"TP1: {tp1}")
print("----------------------")

if df_filtered.empty:
    print("No data after target time.")
else:
    min_low = df_filtered['Low'].min()
    max_high = df_filtered['High'].max()
    print(f"Since entry, Max High: {max_high}")
    print(f"Since entry, Min Low: {min_low}")
    
    trade_status = "RUNNING"
    for index, row in df_filtered.iterrows():
        if row['High'] >= sl:
            print(f"[{index}] ❌ STOP LOSS HIT at {row['High']:.2f}")
            trade_status = "LOSS"
            break
        elif row['Low'] <= tp1:
            print(f"[{index}] ✅ TP1 HIT at {row['Low']:.2f}")
            trade_status = "WIN"
            break
            
    if trade_status == "RUNNING":
        current_price = df_filtered.iloc[-1]['Close']
        print(f"Trade is still RUNNING. Current price: {current_price:.2f}")
        
        if current_price < entry:
            print(f"Currently in PROFIT: +{entry - current_price:.2f} points")
        else:
            print(f"Currently in DRAWDOWN: -{current_price - entry:.2f} points")
