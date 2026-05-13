"""
ExchangeClient — yfinance Backend (AWS EC2 Uchun Optimallashtirilgan)
======================================================================
SABAB: Binance API AWS EC2 IP larini bloklaydi (400 Bad Request).
YECHIM: yfinance — Gold, Forex, Crypto — barchasi bepul va to'siqsiz.

Symbol xaritasi (settings.yaml → Yahoo Finance ticker):
  XAU/USD   → GC=F         (Gold Futures)
  EUR/USD   → EURUSD=X
  GBP/USD   → GBPUSD=X
  BTC/USDT  → BTC-USD
  ETH/USDT  → ETH-USD
  XRP/USDT  → XRP-USD
  USD/JPY   → USDJPY=X
  USD/CAD   → USDCAD=X
  USD/CHF   → USDCHF=X
  AUD/USD   → AUDUSD=X
  NZD/USD   → NZDUSD=X
  SOL/USDT  → SOL-USD
  AVAX/USD  → AVAX-USD
"""

import asyncio
import logging
import pandas as pd
import yfinance as yf
from typing import Optional

logger = logging.getLogger(__name__)


# ── Symbol xaritasi ────────────────────────────────────────────────────────
SYMBOL_MAP = {
    # Metals
    "XAU/USD": "GC=F",
    "GOLD": "GC=F",
    "XAG/USD": "SI=F",
    "OIL/USD": "CL=F",

    # Forex
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "USDJPY=X",
    "USD/CAD": "USDCAD=X",
    "USD/CHF": "USDCHF=X",
    "AUD/USD": "AUDUSD=X",
    "NZD/USD": "NZDUSD=X",
    "USD/TRY": "USDTRY=X",

    # Crypto
    "BTC/USDT": "BTC-USD",
    "ETH/USDT": "ETH-USD",
    "XRP/USDT": "XRP-USD",
    "SOL/USDT": "SOL-USD",
    "AVAX/USD": "AVAX-USD",
    "BNB/USDT": "BNB-USD",
    "ADA/USDT": "ADA-USD",
    "DOT/USDT": "DOT-USD",
}

# ── Timeframe xaritasi ─────────────────────────────────────────────────────
TF_MAP = {
    "1m":  "1m",
    "5m":  "5m",
    "15m": "15m",
    "30m": "30m",
    "1h":  "1h",
    "4h":  "1h",    # yfinance 4h yo'q → 1h olib resample qilamiz
    "1d":  "1d",
}

# Har bir timeframe uchun qancha kun tarix olish kerak (limit ni qoplash uchun)
PERIOD_DAYS = {
    "1m":  "7d",
    "5m":  "60d",
    "15m": "60d",
    "30m": "60d",
    "1h":  "730d",
    "4h":  "730d",
    "1d":  "max",
}


def _to_yahoo(symbol: str) -> str:
    """Bot symbolini Yahoo Finance ticker ga o'girish (XAU/USD -> GC=F)."""
    s = symbol.upper().strip()
    
    # Maxsus holatlar (Agar mappingda bo'lsa)
    if s in SYMBOL_MAP:
        ticker = SYMBOL_MAP[s]
    else:
        # Standart Forex/Crypto o'girish
        ticker = s.replace("/", "") + "=X"
        if "-" not in ticker and len(s) > 7: # Crypto bo'lishi mumkin
             ticker = s.replace("/", "-")
             
    logger.debug(f"[SYMBOL-MAP] {symbol} -> {ticker}")
    return ticker


def _fetch_sync(ticker: str, interval: str, period: str, limit: int) -> Optional[pd.DataFrame]:
    """Sinxron yfinance chaqiruvi (3 marta qayta urinish bilan)."""
    import time as _time
    for attempt in range(3):
        try:
            tk = yf.Ticker(ticker)
            df = tk.history(period=period, interval=interval, auto_adjust=True)

            if df is not None and not df.empty:
                # Ustun nomlarini kichik harfga o'girish
                df.columns = [c.lower() for c in df.columns]
                
                # Kerakli ustunlarni tanlash
                needed = ['open', 'high', 'low', 'close', 'volume']
                if all(c in df.columns for c in needed):
                    df = df[needed].copy()
                    
                    # Index ni UTC ga o'girish
                    if df.index.tzinfo is None:
                        df.index = df.index.tz_localize('UTC')
                    else:
                        df.index = df.index.tz_convert('UTC')
                    
                    df.dropna(inplace=True)
                    if len(df) > limit:
                        df = df.tail(limit)
                    
                    if not df.empty:
                        return df.astype(float)

            # Agar bo'sh bo'lsa yoki xato bo'lsa, biroz kutib qayta urinish
            _time.sleep(0.5 * (attempt + 1))
        except Exception as e:
            logger.debug(f"yfinance urinish {attempt+1} xato ({ticker}): {e}")
            _time.sleep(0.5 * (attempt + 1))
            
    logger.warning(f"yfinance: {ticker} uchun 3 ta urinishdan keyin ham ma'lumot olib bo'lmadi.")
    return None


def _resample_4h(df: pd.DataFrame) -> pd.DataFrame:
    """1h ma'lumotlarini 4h ga resample qilish."""
    df_4h = df.resample('4h').agg({
        'open':   'first',
        'high':   'max',
        'low':    'min',
        'close':  'last',
        'volume': 'sum',
    }).dropna()
    return df_4h


class ExchangeClient:
    """
    yfinance asosida bozor ma'lumotlarini oluvchi klass.
    AWS EC2 da Binance o'rniga ishonchli ishlaydi.
    """

    def __init__(self, config: dict):
        self.config = config
        logger.info("ExchangeClient (yfinance) yuklandi. AWS EC2 uchun optimallashtirilgan.")
        print("INFO: ExchangeClient yfinance backend (Binance emas) OK")

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 300
    ) -> Optional[pd.DataFrame]:
        """
        OHLCV ma'lumotlarini yfinance orqali olish.
        Barcha Forex, Metal va Crypto symbollarini qo'llab-quvvatlaydi.
        """
        ticker = _to_yahoo(symbol)
        yf_interval = TF_MAP.get(timeframe, "15m")
        need_resample = (timeframe == "4h")

        # 4h uchun ko'proq ma'lumot olish kerak
        if need_resample:
            fetch_limit = limit * 4 + 50
            fetch_tf = "1h"
        else:
            fetch_limit = limit + 50
            fetch_tf = yf_interval

        period = PERIOD_DAYS.get(timeframe, "8d")

        try:
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(
                None, _fetch_sync, ticker, fetch_tf, period, fetch_limit
            )

            if df is None:
                logger.debug(f"[EXCHANGE] {symbol} ({ticker}): ma'lumot yo'q.")
                return None

            # 4h resample
            if need_resample:
                df = _resample_4h(df)

            # Oxirgi limit ta sham
            df = df.tail(limit)

            if len(df) < 50:
                logger.debug(f"[EXCHANGE] {symbol}: yetarli sham yo'q ({len(df)} < 50)")
                return None

            logger.debug(f"[EXCHANGE] {symbol} ({ticker}): {len(df)} ta sham olindi ✅")
            return df

        except Exception as e:
            logger.error(f"[EXCHANGE] {symbol} xato: {e}")
            return None

    def get_balance(self):
        """Hisob balansi (sim. demo uchun)."""
        return None

    def create_order(self, *args, **kwargs):
        """Order yaratish (sim. demo uchun)."""
        return None
