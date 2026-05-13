import pandas as pd
import numpy as np
from core.indicator import GeminiIndicator
from utils.exchange import ExchangeClient
import yaml
import os
import sys
from datetime import datetime

# Konsol kodirovkasini sozlash
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath('.'))

class SMCBacktester:
    """
    SMC Strategiyasi uchun professional Backtest dvigateli.
    Haqiqiy komissiya, slippage va MDD hisob-kitoblari bilan.
    """

    def __init__(self, config_path: str, initial_balance: float = 1000.0):
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config fayli topilmadi: {config_path}")
            
        with open(config_path, 'r') as f:
            self.cfg = yaml.safe_load(f)
        
        self.indicator = GeminiIndicator(self.cfg)
        self.exchange = ExchangeClient(self.cfg)
        
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.trades = []
        
        # Binance Futures standarti: 0.04% komissiya va 0.01% sirpanish
        self.fee_rate = 0.0004  
        self.slippage = 0.0001  

    async def run(self, symbol: str, timeframe: str = '15m', days: int = 43):
        print(f"🚀 {symbol} uchun {days} kunlik backtest boshlandi (Aprel - Bugun)...")
        
        # 1. Real birja tarixini yuklash
        print(f"📥 {symbol} uchun ma'lumotlar yuklanmoqda...", flush=True)
        limit = days * 96 
        df = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        
        print(f"📥 {symbol} uchun HTF ma'lumotlar yuklanmoqda...", flush=True)
        htf_df = await self.exchange.fetch_ohlcv(symbol, '1h', limit=days * 24)
        
        if df is None or len(df) < 300:
            print(f"❌ {symbol} uchun ma'lumot yetarli emas! (L: {len(df) if df is not None else 0})", flush=True)
            return

        print(f"📊 {symbol}: {len(df)} ta sham tahlil qilinmoqda...", flush=True)

        # 2. Vaqt bo'yicha iteratsiya (Look-ahead bias oldini olish uchun)
        # 100 ta shamni indikator isishi uchun qoldiramiz
        for i in range(100, len(df)):
            if i % 500 == 0:
                print(f"🔄 {symbol}: {i}/{len(df)} sham qayta ishlandi...", flush=True)
                
            current_window = df.iloc[:i]
            
            # HTF trendni o'sha paytdagi holat bo'yicha filtrlash
            current_htf = None
            if htf_df is not None and not htf_df.empty:
                current_htf = htf_df[htf_df.index <= current_window.index[-1]]
            
            # Signal generatsiya qilish
            # Eslatma: get_analysis AI ni backtestda ishlatmaymiz (juda sekin va qimmat bo'ladi)
            # Faqat texnik indikator qismini ishlatamiz
            signal = self.indicator.generate_signal(current_window, symbol, timeframe, htf_df=current_htf)
            
            if signal and signal.quality >= self.cfg.get('smc', {}).get('min_quality', 75.0):
                self._process_trade(df, i, signal)

        self._generate_report(symbol)

    def _process_trade(self, df, start_idx, signal):
        """Savdo natijasini kelajakdagi shamlar orqali aniqlash."""
        entry = signal.entry * (1 + self.slippage if signal.direction == 'buy' else 1 - self.slippage)
        sl = signal.sl
        tp = signal.tp1 # Backtestda TP1 ni hisoblaymiz (eng xavfsiz)
        
        risk_per_trade = self.balance * (self.cfg.get('trend', {}).get('risk_perc', 2.0) / 100)
        price_risk = abs(entry - sl)
        if price_risk == 0: return
        
        qty = risk_per_trade / price_risk
        
        # Savdo qachon yopilishini qidirish
        for j in range(start_idx + 1, len(df)):
            high, low = df['high'].iat[j], df['low'].iat[j]
            
            # Stop-Loss urildimi?
            if (signal.direction == 'buy' and low <= sl) or (signal.direction == 'sell' and high >= sl):
                pnl = -risk_per_trade - (entry * qty * self.fee_rate)
                self._record(df.index[j], "SL", pnl, signal)
                return
                
            # Take-Profit urildimi?
            if (signal.direction == 'buy' and high >= tp) or (signal.direction == 'sell' and low <= tp):
                pnl = (abs(entry - tp) * qty) - (entry * qty * self.fee_rate)
                self._record(df.index[j], "TP1", pnl, signal)
                return

    def _record(self, time, res, pnl, sig):
        self.balance += pnl
        self.trades.append({
            'time': time, 'res': res, 'pnl': round(pnl, 2), 
            'bal': round(self.balance, 2), 'dir': sig.direction
        })

    def _generate_report(self, sym):
        if not self.trades:
            print(f"⚠️ {sym} bo'yicha qoidaga mos signal topilmadi.")
            return

        tdf = pd.DataFrame(self.trades)
        wins = len(tdf[tdf['pnl'] > 0])
        wr = (wins / len(tdf)) * 100
        
        equity = pd.Series([self.initial_balance] + tdf['bal'].tolist())
        dd = ((equity.cummax() - equity) / equity.cummax()).max() * 100

        print(f"\n📈 --- {sym} BACKTEST NATIJASI ---")
        print(f"💰 Yakuniy balans: ${round(self.balance, 2)}")
        print(f"🏆 Win-Rate: {round(wr, 1)}% | Savdolar: {len(tdf)}")
        print(f"📉 Max Drawdown: {round(dd, 2)}%")
        print(f"💵 Jami ROI: {round(((self.balance/self.initial_balance)-1)*100, 2)}%\n")

async def main():
    with open('config/settings.yaml', 'r') as f:
        cfg = yaml.safe_load(f)
    
    symbols = cfg.get('symbols', [])
    if not symbols:
        print("XATO: config/settings.yaml ichida simbollar topilmadi.")
        return

    # Aprel 1 dan bugungacha (May 13) taxminan 43 kun
    days_to_test = 43
    
    print("="*60)
    print(f"SMC TITAN: 13 TA INSTRUMENT UCHUN TARIXIY TEST")
    print(f"DAVR: 2026-04-01 dan 2026-05-13 gacha ({days_to_test} kun)")
    print("="*60 + "\n")
    
    total_initial = 100.0 * len(symbols)
    total_final = 0.0
    
    for sym in symbols:
        tester = SMCBacktester('config/settings.yaml', initial_balance=100.0)
        await tester.run(sym, timeframe='15m', days=days_to_test)
        total_final += tester.balance
        print("-" * 40)

    total_roi = ((total_final / total_initial) - 1) * 100
    print("\n" + "="*60)
    print(f"YAKUNIY PORTFEL NATIJASI:")
    print(f"💰 Boshlang'ich kapital: ${total_initial}")
    print(f"💰 Yakuniy kapital: ${round(total_final, 2)}")
    print(f"📊 Umumiy ROI: {round(total_roi, 2)}%")
    print("="*60)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
