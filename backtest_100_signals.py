import sys
import os
import ccxt
import pandas as pd
from datetime import datetime

sys.path.insert(0, os.path.abspath('.'))

from core.indicator import GeminiIndicator
from utils.telegram import TelegramNotifier
from dotenv import load_dotenv
import yaml
import asyncio

async def run_backtest():
    print("[BACKTEST] 1-apreldan bugungacha bo'lgan tarixiy ma'lumotlar tahlil qilinmoqda...")
    load_dotenv()
    
    # settings.yaml dan sozlamalarni o'qiymiz
    with open('config/settings.yaml', 'r') as f:
        cfg = yaml.safe_load(f)
    
    # Telegramni sozlash
    lock = __import__('threading').Lock()
    notifier = TelegramNotifier(cfg, lock)
    
    min_q = cfg.get('smc', {}).get('min_quality', 50.0)
    print(f"[INFO] Sifat chegarasi: {min_q}%")
    
    exchange = ccxt.binance()
    symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT'] # Kripto uchun (Forex Yahoo'da backtest qiyinroq)
    
    # 1-aprel 2026 timestamp (millisekundlarda)
    since = int(datetime(2026, 4, 1).timestamp() * 1000)
    
    ind = GeminiIndicator(cfg)
    
    total_signals = 0
    wins = 0
    losses = 0
    timeouts_profit = 0
    timeouts_loss = 0
    
    for sym in symbols:
        try:
            print(f"--- {sym} ma'lumotlari yuklanmoqda...")
            # Barcha ma'lumotlarni apreldan boshlab olish
            all_ohlcv = []
            current_since = since
            while len(all_ohlcv) < 5000: # Max 5000 sham (apreldan hozirgacha yetadi)
                ohlcv = exchange.fetch_ohlcv(sym, '15m', since=current_since, limit=1000)
                if not ohlcv: break
                all_ohlcv.extend(ohlcv)
                current_since = ohlcv[-1][0] + 1
                if len(ohlcv) < 1000: break
                
            df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            print(f"DONE: {len(df)} ta sham yuklandi.")
            
            # Tahlil
            for i in range(200, len(df) - 50, 1): # Har bir shamda tekshirish (aniqroq test)
                window = df.iloc[i-200:i].copy()
                sig = ind.generate_signal(window, sym, '15m', loss_streak=0, htf_df=None)
                
                if sig and sig.quality >= min_q:
                    total_signals += 1
                    
                    # Check outcome in the next 50 candles
                    future = df.iloc[i:i+50]
                    hit_tp = False
                    hit_sl = False
                    
                    for _, row in future.iterrows():
                        high = row['high']
                        low = row['low']
                        
                        if sig.direction == 'buy':
                            if low <= sig.sl:
                                hit_sl = True
                                break
                            if high >= sig.tp1:
                                hit_tp = True
                                break
                        else:
                            if high >= sig.sl:
                                hit_sl = True
                                break
                            if low <= sig.tp1:
                                hit_tp = True
                                break
                    
                    if hit_tp:
                        wins += 1
                    elif hit_sl:
                        losses += 1
                    else:
                        # Senior Quant mantiqi: Timeout bo'lganda pozitsiyaning oxirgi holatini tekshirish
                        final_close = future['close'].iloc[-1]
                        if sig.direction == 'buy':
                            if final_close > sig.entry:
                                timeouts_profit += 1
                            else:
                                timeouts_loss += 1
                        else:
                            if final_close < sig.entry:
                                timeouts_profit += 1
                            else:
                                timeouts_loss += 1
                        
                    if total_signals >= 100:
                        break
                        
        except Exception as e:
            print(f"Xato {sym}: {e}")
            
        if total_signals >= 100:
            break

    report = (
        f"📊 <b>BACKTEST NATIJALARI (Apr-May)</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🪙 Instrumentlar: BTC, ETH, SOL\n"
        f"⚙️ Sifat chegarasi: <b>{min_q}%</b>\n\n"
        f"📥 Jami signallar: {total_signals}\n"
        f"✅ TP urganlar: {wins}\n"
        f"❌ SL urganlar: {losses}\n"
        f"⏳ Timeout (Profit): {timeouts_profit}\n"
        f"⏳ Timeout (Loss): {timeouts_loss}\n\n"
        f"🏆 <b>Real Win-Rate: {((wins + timeouts_profit) / total_signals * 100) if total_signals > 0 else 0:.1f}%</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 Titan V27.2 Analyzer"
    )
    
    print("\n[TELEGRAM] Hisobot yuborilmoqda...")
    await notifier.send(report)
    print("DONE.")

if __name__ == '__main__':
    asyncio.run(run_backtest())
