"""
scratch/simulate_signal.py
SMC signal generatsiyasini simulyatsiya qilish va testdan o'tkazish.
Ushbu skript sun'iy ravishda "Bullish BOS" (Yuqoriga buzib o'tish) yaratadi.
"""
import pandas as pd
import numpy as np
import yaml
from core.indicator import GeminiIndicator

def generate_bullish_bos_data():
    """Signallar chiqishi uchun ideal 'Bullish BOS' ma'lumotlarini yaratish."""
    # 250 ta sham
    n = 250
    dates = pd.date_range("2024-01-01", periods=n, freq="15min")
    
    # 1. Start
    base = [2000] * 150
    
    # 2. Pivot High (must be center of 11-13 candles)
    pivot_formation = [2005]*6 + [2100] + [2005]*6
    
    # 3. Build up to BOS 2100
    breakout = np.linspace(2005, 2150, 87) # 150 + 13 + 87 = 250
    
    close = np.concatenate([base, pivot_formation, breakout])
    
    # Shovqin qo'shish
    close += np.random.normal(0, 1, n)
    
    df = pd.DataFrame({
        'open':   close - np.random.uniform(1, 3, n),
        'high':   close + np.random.uniform(2, 5, n),
        'low':    close - np.random.uniform(2, 5, n),
        'close':  close,
        'volume': np.random.randint(5000, 15000, n).astype(float)
    }, index=dates)
    
    # Breakout paytida hajm ko'payishi (VSA)
    df.iloc[-10:, df.columns.get_loc('volume')] *= 3
    
    return df

def run_test():
    print("[TEST] Signal generatsiyasi simulyatsiyasi boshlandi...")
    
    # 1. Config yuklash
    with open('config/settings.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # 2. Ma'lumot tayyorlash
    df = generate_bullish_bos_data()
    print(f"--- {len(df)} ta sham yaratildi. Oxirgi narx: {df['close'].iloc[-1]:.2f}")
    
    # 3. Indikatorni ishga tushirish
    config['smc']['min_quality'] = 50.0
    ind = GeminiIndicator(config)
    
    # 4. Signal qidirish
    sig = ind.generate_signal(df, "XAU/USD", "15min", loss_streak=0)
    
    if sig:
        print("\n[MUVAFFAQIYAT] Signal aniqlandi!")
        print("--------------------")
        print(f"Signal: {sig.direction.upper()}")
        print(f"Sifat: {sig.quality}%")
        print(f"Kirish: {sig.entry:.2f}")
        print(f"Stop-Loss: {sig.sl:.2f}")
        print(f"TP1: {sig.tp1:.2f}")
        print(f"TP2: {sig.tp2:.2f}")
        print(f"TP3: {sig.tp3:.2f}")
        print(f"Asos: {sig.reason}")
        print("--------------------")
    else:
        print("\n[LOG] Signal aniqlanmadi (Sifat < 75 yoki BOS yo'q).")
        # Nega chiqmaganini tushunish uchun debug:
        close = df['close'].iloc[-1]
        ema200 = df['close'].rolling(200).mean().iloc[-1]
        print(f"DEBUG: Close={close:.2f}, EMA200={ema200:.2f}")

if __name__ == "__main__":
    run_test()
