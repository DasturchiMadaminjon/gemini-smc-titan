import pandas as pd
import numpy as np
from core.indicator import GeminiIndicator
from utils.exchange import ExchangeClient
import yaml
import os
import sys
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

    def run(self, symbol: str, timeframe: str = '15m', days: int = 60):
        print(f"🚀 {symbol} uchun {days} kunlik backtest boshlandi...")
        
        # 1. Real birja tarixini yuklash
        # Yahoo finance 15m data limit is 60 days
        df = self.exchange.fetch_ohlcv(symbol, timeframe, limit=days * 96) 
        htf_df = self.exchange.fetch_ohlcv(symbol, '4h', limit=days * 6)
        
        if df is None or len(df) < 300:
            print("❌ Ma'lumot yetarli emas!")
            return

        print(f"📊 {len(df)} ta sham tahlil qilinmoqda...")

        # 2. Vaqt bo'yicha iteratsiya (Look-ahead bias oldini olish uchun)
        for i in range(100, len(df)):
            current_window = df.iloc[:i]
            # HTF trendni o'sha paytdagi holat bo'yicha olish
            current_htf = None
            if htf_df is not None and not htf_df.empty:
                current_htf = htf_df[htf_df.index <= current_window.index[-1]]
            
            signal = self.indicator.generate_signal(current_window, symbol, htf_df=current_htf)
            
            if signal:
                self._process_trade(df, i, signal)

        self._generate_report(symbol)

    def _process_trade(self, df, start_idx, signal):
        """Savdo natijasini kelajakdagi shamlar orqali aniqlash."""
        entry = signal.entry * (1 + self.slippage if signal.direction == 'buy' else 1 - self.slippage)
        sl = signal.sl
        tp = signal.tp1
        
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
            print(f"⚠️ {sym} bo'yicha hech qanday signal topilmadi.")
            return

        tdf = pd.DataFrame(self.trades)
        wins = len(tdf[tdf['pnl'] > 0])
        wr = (wins / len(tdf)) * 100
        
        # Max Drawdown hisoblash
        equity = pd.Series([self.initial_balance] + tdf['bal'].tolist())
        dd = ((equity.cummax() - equity) / equity.cummax()).max() * 100

        print(f"\n📈 --- {sym} BACKTEST NATIJASI ---")
        print(f"💰 Yakuniy balans: ${round(self.balance, 2)}")
        print(f"🏆 Win-Rate: {round(wr, 1)}% | Savdolar: {len(tdf)}")
        print(f"📉 Max Drawdown: {round(dd, 2)}%")
        print(f"💵 Jami ROI: {round(((self.balance/self.initial_balance)-1)*100, 2)}%\n")

if __name__ == "__main__":
    symbols = [
        'XAU/USD', 'EUR/USD', 'GBP/USD', 'BTC/USDT', 'ETH/USDT', 
        'XRP/USDT', 'USD/JPY', 'USD/CAD', 'USD/CHF', 'AUD/USD', 
        'NZD/USD', 'SOL/USDT'
    ]
    
    print("="*50, flush=True)
    print(f"Barcha instrumentlar uchun 60 kunlik test (Mart-Aprel 2026)", flush=True)
    print("Manba: Yahoo Finance / Binance Real-Time Data", flush=True)
    print("="*50, flush=True)
    
    for sym in symbols:
        tester = SMCBacktester('config/settings.yaml', initial_balance=100.0)
        tester.run(sym, days=60)
        print("-" * 30, flush=True)
