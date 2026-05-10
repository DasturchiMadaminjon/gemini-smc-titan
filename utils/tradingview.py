"""
GEMINI V20 BOT - TradingView Data Client (ASYNCHRONOUS)
TradingView API'dan API kalitsiz OHLCV ma'lumotlarini asinxron olish
"""
import json
import re
import random
import string
import logging
import aiohttp
import pandas as pd
from typing import Optional

logger = logging.getLogger(__name__)

# TradingView timeframe mapping
TV_TIMEFRAMES = {
    '1m':  '1',
    '3m':  '3',
    '5m':  '5',
    '15m': '15',
    '30m': '30',
    '45m': '45',
    '1h':  '60',
    '2h':  '120',
    '3h':  '180',
    '4h':  '240',
    '1d':  '1D',
    '1w':  '1W',
    '1M':  '1M',
}

# Instrument exchange mapping (TradingView uchun)
SYMBOL_EXCHANGE = {
    'XAUUSD':   'OANDA',         # GOLD
    'XAGUSD':   'OANDA',         # SILVER
    'EURUSD':   'OANDA',
    'GBPUSD':   'OANDA',
    'USDJPY':   'OANDA',
    'BTCUSDT':  'BINANCE',
    'ETHUSDT':  'BINANCE',
    'SOLUSDT':  'BINANCE',
    'XRPUSDT':  'BINANCE',
    'BNBUSDT':  'BINANCE',
    'BTCUSD':   'COINBASE',
}


def _normalize_symbol(symbol: str) -> tuple[str, str]:
    """
    ccxt formatidan ('BTC/USDT') TradingView formatiga ('BTCUSDT', 'BINANCE') o'tkazish
    """
    if symbol.upper() in ('GOLD', 'XAU/USD', 'XAUUSD'):
        return 'XAUUSD', 'OANDA'
    if symbol.upper() in ('SILVER', 'XAG/USD', 'XAGUSD'):
        return 'XAGUSD', 'OANDA'

    forex_pairs = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'USDCHF', 'NZDUSD']
    clean = symbol.replace('/', '').upper()
    if clean in forex_pairs:
        return clean, 'OANDA'

    if '/' in symbol:
        base, quote = symbol.upper().split('/', 1)
        tv_sym = base + quote
        exchange = SYMBOL_EXCHANGE.get(tv_sym, 'BINANCE')
        return tv_sym, exchange

    exchange = SYMBOL_EXCHANGE.get(clean, 'BINANCE')
    return clean, exchange


class TradingViewClient:
    """
    TradingView dan API kalitsiz OHLCV ma'lumotlarini asinxron olish
    """
    
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Origin': 'https://www.tradingview.com',
        'Referer': 'https://www.tradingview.com/',
    }

    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None

    async def get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(headers=self.HEADERS, timeout=aiohttp.ClientTimeout(total=20))
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def fetch_ohlcv(self, symbol: str, timeframe: str = '5m', limit: int = 300) -> Optional[pd.DataFrame]:
        tv_sym, exchange = _normalize_symbol(symbol)
        tv_tf = TV_TIMEFRAMES.get(timeframe, '5')

        try:
            data = await self._fetch_via_scan(tv_sym, exchange, tv_tf, limit)
            if data is not None and len(data) >= 10:
                return data
        except Exception as e:
            logger.debug(f"TV scan xato ({symbol}): {e}")

        try:
            data = await self._fetch_via_history(tv_sym, exchange, tv_tf, limit)
            return data
        except Exception as e:
            logger.error(f"TV history xato ({symbol}): {e}")
            return None

    async def _fetch_via_scan(self, symbol: str, exchange: str, tf: str, limit: int) -> Optional[pd.DataFrame]:
        url = 'https://scanner.tradingview.com/global/scan'
        payload = {
            "columns": [f"open|{tf}", f"high|{tf}", f"low|{tf}", f"close|{tf}", f"volume|{tf}", "time"],
            "filter": [{"left": "exchange", "operation": "in_range", "right": [exchange]},
                       {"left": "name", "operation": "equal", "right": symbol}],
            "markets": ["global"],
            "symbols": {"tickers": [f"{exchange}:{symbol}"]},
            "sort": {"sortBy": "time", "sortOrder": "desc"},
            "range": [0, min(limit, 200)]
        }
        
        sess = await self.get_session()
        async with sess.post(url, json=payload) as resp:
            if resp.status != 200: return None
            result = await resp.json()
            data_list = result.get('data', [])
            if not data_list: return None

            rows = []
            for item in data_list:
                d = item.get('d', [])
                if len(d) >= 6:
                    rows.append({'open': d[0], 'high': d[1], 'low': d[2],
                                'close': d[3], 'volume': d[4], 'timestamp': d[5]})
            
            if not rows: return None
            df = pd.DataFrame(rows)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', utc=True)
            df.set_index('timestamp', inplace=True)
            df = df.sort_index()
            return df.astype(float)

    async def _fetch_via_history(self, symbol: str, exchange: str, tf: str, limit: int) -> Optional[pd.DataFrame]:
        import time as _time
        url = 'https://history.tradingview.com/history'
        params = {
            'symbol': f'{exchange}:{symbol}',
            'resolution': tf,
            'from': int(_time.time()) - (limit * self._tf_to_seconds(tf) * 2),
            'to': int(_time.time()),
            'countback': limit,
        }
        
        sess = await self.get_session()
        async with sess.get(url, params=params) as resp:
            if resp.status != 200: return None
            res = await resp.json()
            if res.get('s') != 'ok': return None
            
            df = pd.DataFrame({
                'timestamp': res.get('t', []),
                'open': res.get('o', []),
                'high': res.get('h', []),
                'low': res.get('l', []),
                'close': res.get('c', []),
                'volume': res.get('v', [])
            })
            if df.empty: return None
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', utc=True)
            df.set_index('timestamp', inplace=True)
            df = df.sort_index()
            return df.astype(float)

    def _tf_to_seconds(self, tf: str) -> int:
        mult = 60
        if tf.endswith('D'): mult = 86400
        elif tf.endswith('W'): mult = 604800
        elif tf.endswith('M'): mult = 2592000
        
        digits = re.findall(r'\d+', tf)
        val = int(digits[0]) if digits else 1
        return val * mult
