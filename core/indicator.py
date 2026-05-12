import pandas as pd
import numpy as np
import io
import matplotlib.pyplot as plt
import mplfinance as mpf
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple

@dataclass
class Signal:
    direction: str
    symbol: str
    entry: float
    sl: float
    tp1: float
    tp2: float
    tp3: float
    quality: float
    reason: str
    timestamp: pd.Timestamp

class GeminiIndicator:
    """
    SMC (Smart Money Concepts) Quant-Grade Signal Generator.
    Professional Hedge Fund mantiqi: MTF Sync, FVG/OB Pullback, Sweep Protection.
    """

    def __init__(self, config: dict):
        self.cfg = config
        self.smc = config.get('smc', {})
        self.tp  = config.get('tp', {})
        self.min_rr = 1.5  # Qat'iy 2.0 dan 1.5 ga yumshatildi (Realist)

    # ------------------------------------------------------------------
    # 1. SWING POINT ENGINE (Fractal Logic)
    # ------------------------------------------------------------------

    def _get_swings(self, df: pd.DataFrame, n: int = 5) -> Tuple[pd.Series, pd.Series]:
        """Pivot High va Low nuqtalarini aniqlash (Non-centered for live/backtest)."""
        # Faqat o'tmishdagi n ta shamdan katta/kichik bo'lishini tekshiramiz
        highs = df['high'].shift(1).rolling(window=n).max()
        lows = df['low'].shift(1).rolling(window=n).min()
        
        pivot_h = (df['high'].shift(n) == df['high'].shift(n).rolling(window=2*n+1, center=True).max())
        pivot_l = (df['low'].shift(n) == df['low'].shift(n).rolling(window=2*n+1, center=True).min())
        return pivot_h, pivot_l

    # ------------------------------------------------------------------
    # 2. MTF TREND GUARD
    # ------------------------------------------------------------------

    def _get_trend(self, df: pd.DataFrame) -> str:
        """Katta taymfreym trendini aniqlash (EMA 200 + Market Structure)."""
        if len(df) < 200: return 'neutral'
        ema200 = df['close'].ewm(span=200, adjust=False).mean().iloc[-1]
        last_close = df['close'].iloc[-1]
        
        if last_close > ema200: return 'bullish'
        if last_close < ema200: return 'bearish'
        return 'neutral'

    # ------------------------------------------------------------------
    # 3. CORE LOGIC: SWEEP VS BOS
    # ------------------------------------------------------------------

    def _detect_structure_break(self, df: pd.DataFrame, n: int = 5) -> Dict:
        """
        BOS (Body Break) va Sweep (Wick Break) farqlash.
        Sweep: Narx soyasi bilan o'tib, tana bilan qaytsa.
        BOS: Narx tanasi (body) bilan yopilsa.
        """
        ph, pl = self._get_swings(df, n)
        # Faqat hozirgi shamdan oldingi tasdiqlangan pivotlarni olamiz
        # ph[i] True degani -> i-n dagi sham pivot bo'lgan
        valid_ph_prices = df['high'].shift(n)[ph & (df.index < df.index[-1])]
        valid_pl_prices = df['low'].shift(n)[pl & (df.index < df.index[-1])]
        
        last_ph = valid_ph_prices.iloc[-1] if not valid_ph_prices.empty else 0
        last_pl = valid_pl_prices.iloc[-1] if not valid_pl_prices.empty else 0
        
        curr = df.iloc[-1]
        
        res = {'bos_up': False, 'bos_down': False, 'sweep_up': False, 'sweep_down': False}
        
        # Bullish Break
        if curr['high'] > last_ph:
            if curr['close'] > last_ph: res['bos_up'] = True
            else: res['sweep_up'] = True
            
        # Bearish Break
        if curr['low'] < last_pl:
            if curr['close'] < last_pl: res['bos_down'] = True
            else: res['sweep_down'] = True
            
        return res

    # ------------------------------------------------------------------
    # 4. FIBONACCI & ZONES (Premium/Discount)
    # ------------------------------------------------------------------

    def _get_fibo_zone(self, low: float, high: float, price: float) -> str:
        """Narx Discount (BUY uchun) yoki Premium (SELL uchun) zonadami?"""
        rng = high - low
        if rng <= 0: return 'neutral'
        
        retracement = (high - price) / rng
        if retracement >= 0.618: return 'discount'  # 0.618 - 0.786 oralig'i
        if retracement <= 0.382: return 'premium'
        return 'equilibrium'

    def _find_unmitigated_fvg(self, df: pd.DataFrame) -> Dict[str, Optional[Tuple[float, float]]]:
        """Yopilmagan FVG (Fair Value Gap) topish (Bullish va Bearish alohida)."""
        res = {'bullish': None, 'bearish': None}
        for i in range(len(df)-1, 2, -1):
            # Bullish FVG
            if res['bullish'] is None and df['high'].iat[i-2] < df['low'].iat[i]:
                gap = (df['high'].iat[i-2], df['low'].iat[i])
                future_lows = df['low'].iloc[i+1:]
                if len(future_lows) == 0 or future_lows.min() > gap[1]: # Hali yopilmagan
                    res['bullish'] = gap
            # Bearish FVG
            if res['bearish'] is None and df['low'].iat[i-2] > df['high'].iat[i]:
                gap = (df['high'].iat[i], df['low'].iat[i-2])
                future_highs = df['high'].iloc[i+1:]
                if len(future_highs) == 0 or future_highs.max() < gap[0]: # Hali yopilmagan
                    res['bearish'] = gap
            if res['bullish'] and res['bearish']:
                break
        return res

    # ------------------------------------------------------------------
    # 5. ATR DYNAMIC STOP-LOSS
    # ------------------------------------------------------------------

    def _get_atr_buffer(self, df: pd.DataFrame) -> float:
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        return true_range.rolling(14).mean().iloc[-1]


    # ------------------------------------------------------------------
    # 6. VISUALIZATION ENGINE (For AI & Telegram)
    # ------------------------------------------------------------------

    def draw_chart_bytes(self, df: pd.DataFrame, symbol: str, signal: Optional[Signal] = None) -> bytes:
        """
        OHLCV ma'lumotlarini rasmga (bytes) aylantirib beradi.
        SMC darajalari (BOS, FVG, Entry, SL, TP) rasmda belgilanadi.
        """
        try:
            # So'nggi 50 ta shamni olamiz
            plot_df = df.tail(50).copy()
            
            # Ranglar sxemasi
            mc = mpf.make_marketcolors(up='green', down='red', inherit=True)
            s  = mpf.make_mpf_style(marketcolors=mc, gridstyle='dotted')
            
            # Qo'shimcha chiziqlar (Entry, SL, TP)
            hlines = []
            if signal:
                hlines = [
                    {'hlines': [float(signal.entry)], 'colors': ['blue'], 'linestyle': 'solid', 'linewidths': 1},
                    {'hlines': [float(signal.sl)], 'colors': ['red'], 'linestyle': 'dashed', 'linewidths': 1},
                    {'hlines': [float(signal.tp1)], 'colors': ['green'], 'linestyle': 'dotted', 'linewidths': 1}
                ]

            buf = io.BytesIO()
            
            # Grafik chizish
            fig, axes = mpf.plot(
                plot_df,
                type='candle',
                style=s,
                title=f"\n{symbol} ({plot_df.index[-1].strftime('%H:%M')})",
                ylabel='Price',
                hlines=hlines,
                returnfig=True,
                figsize=(10, 6)
            )
            
            # Rasmni saqlash
            fig.savefig(buf, format='png', bbox_inches='tight')
            plt.close(fig)
            buf.seek(0)
            return buf.read()
            
        except Exception as e:
            print(f"DEBUG: draw_chart_bytes error: {e}")
            return b""

    def generate_signal(self, df: pd.DataFrame, symbol: str, tf: str = '15m', loss_streak: int = 0, htf_df: Optional[pd.DataFrame] = None) -> Optional[Signal]:
        if len(df) < 50: return None
        
        # 1. MTF Trend Check
        htf_trend = self._get_trend(htf_df) if htf_df is not None else 'neutral'
        
        # 2. Market Structure
        struct = self._detect_structure_break(df)
        
        # 3. ATR Buffer for SL
        atr = self._get_atr_buffer(df)
        curr_price = df['close'].iloc[-1]
        
        # 4. Swing High/Low for Fibo & SL
        recent_high = df['high'].rolling(100).max().iloc[-1]
        recent_low = df['low'].rolling(100).min().iloc[-1]
        zone = self._get_fibo_zone(recent_low, recent_high, curr_price)
        
        # 5. FVG/OB Confluence
        fvgs = self._find_unmitigated_fvg(df.tail(100))

        # --- DINAMIK SIFAT HISOBINI BOSHLASH ---
        # settings.yaml dan min_quality ni olamiz
        target_min_q = self.smc.get('min_quality', 70.0)
        
        def calculate_quality(direction: str, current_zone: str, trend: str, has_fvg: bool, risk_reward: float) -> float:
            score = 30.0 # Boshlang'ich ball (Struktura mavjudligi uchun)
            
            # Zona mosligi
            if (direction == 'buy' and current_zone == 'discount') or (direction == 'sell' and current_zone == 'premium'):
                score += 20.0
            
            # Trend mosligi
            if (direction == 'buy' and trend != 'bearish') or (direction == 'sell' and trend != 'bullish'):
                score += 20.0
                
            # FVG mavjudligi
            if has_fvg:
                score += 20.0
                
            # R:R sifati
            if risk_reward >= 2.5: score += 10.0
            elif risk_reward >= 1.5: score += 5.0
            
            return min(score, 100.0)

        # --- BUY SIGNAL LOGIC ---
        if struct['bos_up'] or (target_min_q <= 50 and struct['sweep_up']):
            sl = recent_low - (atr * 0.5)
            risk = curr_price - sl
            if risk > 0:
                rr = (recent_high - curr_price) / risk
                q = calculate_quality('buy', zone, htf_trend, fvgs['bullish'] is not None, rr)
                
                # Agar sifat yetarli bo'lsa yoki bozor juda aniq bo'lsa
                if q >= target_min_q:
                    return Signal(
                        direction='buy', symbol=symbol, entry=curr_price,
                        sl=sl, tp1=curr_price + risk * 1.5, tp2=curr_price + risk * 2.5, tp3=curr_price + risk * 4.0,
                        quality=q, reason=f"SMC Setup (Q:{q}%)",
                        timestamp=pd.Timestamp.now()
                    )

        # --- SELL SIGNAL LOGIC ---
        if struct['bos_down'] or (target_min_q <= 50 and struct['sweep_down']):
            sl = recent_high + (atr * 0.5)
            risk = sl - curr_price
            if risk > 0:
                rr = (curr_price - recent_low) / risk
                q = calculate_quality('sell', zone, htf_trend, fvgs['bearish'] is not None, rr)
                
                if q >= target_min_q:
                    return Signal(
                        direction='sell', symbol=symbol, entry=curr_price,
                        sl=sl, tp1=curr_price - risk * 1.5, tp2=curr_price - risk * 2.5, tp3=curr_price - risk * 4.0,
                        quality=q, reason=f"SMC Setup (Q:{q}%)",
                        timestamp=pd.Timestamp.now()
                    )

        return None
