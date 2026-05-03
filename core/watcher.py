import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional
import pandas as pd

logger = logging.getLogger('GeminiBot.Watcher')

class MarketWatcher:
    """Bozor ma'lumotlarini kuzatish va MTF tahlil moduli"""
    def __init__(self, config: dict, exchange_client):
        self.cfg = config
        self.exchange = exchange_client
        self.timeframe = config.get('timeframe', '15m')
        self._mtf_cache = {}

    def load_symbol_data(self, symbol: str, bot_state, state_lock) -> Optional[pd.DataFrame]:
        """Birjadan OHLCV ma'lumotlarini olish va dashboardni yangilash"""
        try:
            df = self.exchange.fetch_ohlcv(symbol, self.timeframe, limit=300)
            if df is None or len(df) < 60:
                logger.warning(f"{symbol}: Yetarli ma'lumot yo'q")
                return None

            # Joriy narxni yangilash
            ticker = self.exchange.get_ticker(symbol)
            if ticker:
                price = ticker.get('last', df['close'].iloc[-1])
                change = ticker.get('percentage', 0) or 0
                with state_lock:
                    if 'symbols' in bot_state and symbol in bot_state['symbols']:
                        bot_state['symbols'][symbol].update({'price': price, 'change': change})
            return df
        except Exception as e:
            logger.error(f"{symbol} ma'lumot olishda xato: {e}")
            return None

    def get_ltf_data(self, symbol: str, tf: str = '5m') -> Optional[str]:
        """Skalping uchun pastki timeframe ma'lumotlarini olish"""
        try:
            df_ltf = self.exchange.fetch_ohlcv(symbol, tf, limit=60)
            if df_ltf is None or len(df_ltf) < 20:
                return None
            
            last = df_ltf.iloc[-1]
            # Mikro trend (EMA 20)
            ema20 = df_ltf['close'].rolling(20).mean().iloc[-1]
            trend = "bullish" if last['close'] > ema20 else "bearish"
            
            ltf_summary = (f"LTF Mode ({tf}) | Price: {last['close']} | "
                           f"Micro-Trend: {trend.upper()} | High: {last['high']} | Low: {last['low']}")
            return ltf_summary
        except Exception as e:
            logger.error(f"LTF tahlil xatosi ({symbol}): {e}")
            return None

    def get_htf_trend(self, symbol: str) -> Optional[str]:
        """Yuqori timeframe trendini aniqlash (MTF PRO)"""
        mtf_cfg = self.cfg.get('mtf', {})
        if not mtf_cfg.get('enabled', True):
            return None

        htf = mtf_cfg.get('higher_tf', '1h')
        ema_p = mtf_cfg.get('ema_period', 200)

        try:
            df_htf = self.exchange._yf_fetch(symbol, htf, limit=ema_p + 20)
            if df_htf is None or len(df_htf) < ema_p:
                return None
            
            ema = df_htf['close'].ewm(span=ema_p, adjust=False).mean().iloc[-1]
            last_close = df_htf['close'].iloc[-1]
            
            trend = "bullish" if last_close > ema else "bearish"
            logger.debug(f"🔍 MTF Trend ({symbol}): {trend.upper()}")
            return trend
        except Exception as e:
            logger.error(f"MTF Trend tahlili xatosi ({symbol}): {e}")
            return None

    def update_mtf_cache(self, symbol: str, htf_trend: str, state_lock):
        """MTF trendini keshda yangilash"""
        with state_lock:
            self._mtf_cache[symbol] = {'trend': htf_trend, 'time': time.time()}

    def get_cached_trend(self, symbol: str) -> Optional[str]:
        cache = self._mtf_cache.get(symbol, {})
        now = time.time()
        # 30 minutlik kesh
        if cache and (now - cache.get('time', 0)) < 1800:
            return cache.get('trend')
        return None
