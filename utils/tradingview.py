"""
GEMINI V20 BOT - TradingView Data Client
TradingView API'dan API kalitsiz OHLCV ma'lumotlarini olish
GOLD (XAUUSD), Forex, Crypto va boshqa instrumentlar uchun
"""
import json
import re
import random
import string
import logging
import requests
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
    # GOLD uchun
    if symbol.upper() in ('GOLD', 'XAU/USD', 'XAUUSD'):
        return 'XAUUSD', 'OANDA'
    if symbol.upper() in ('SILVER', 'XAG/USD', 'XAGUSD'):
        return 'XAGUSD', 'OANDA'

    # Forex
    forex_pairs = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'USDCHF', 'NZDUSD']
    clean = symbol.replace('/', '').upper()
    if clean in forex_pairs:
        return clean, 'OANDA'

    # ccxt format ('ETH/USDT') -> TradingView ('ETHUSDT', 'BINANCE')
    if '/' in symbol:
        base, quote = symbol.upper().split('/', 1)
        tv_sym = base + quote
        exchange = SYMBOL_EXCHANGE.get(tv_sym, 'BINANCE')
        return tv_sym, exchange

    exchange = SYMBOL_EXCHANGE.get(clean, 'BINANCE')
    return clean, exchange


def _gen_session_id(prefix='cs') -> str:
    return prefix + ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))


class TradingViewClient:
    """
    TradingView dan API kalitsiz OHLCV ma'lumotlarini olish
    GOLD, Forex, Crypto va boshqa 50,000+ instrumentlar uchun ishlaydi
    """
    
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Origin': 'https://www.tradingview.com',
        'Referer': 'https://www.tradingview.com/',
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        # TradingView session cookie olish
        try:
            self.session.get('https://www.tradingview.com', timeout=10)
        except Exception:
            pass

    def fetch_ohlcv(self, symbol: str, timeframe: str = '5m',
                    limit: int = 300) -> Optional[pd.DataFrame]:
        """
        TradingView dan OHLCV ma'lumotlarini olish
        
        Args:
            symbol: 'ETH/USDT', 'XAUUSD', 'GOLD', 'EUR/USD' kabi
            timeframe: '1m','5m','15m','1h','4h','1d' kabi
            limit: nechta bar (max 5000)
        
        Returns:
            DataFrame ('open','high','low','close','volume' ustunlari bilan)
            yoki None (xato bo'lganda)
        """
        tv_sym, exchange = _normalize_symbol(symbol)
        tv_tf = TV_TIMEFRAMES.get(timeframe, '5')

        try:
            data = self._fetch_via_scan(tv_sym, exchange, tv_tf, limit)
            if data is not None and len(data) >= 10:
                return data
        except Exception as e:
            logger.debug(f"TV scan xato ({symbol}): {e}")

        # Zahira usul
        try:
            data = self._fetch_via_history(tv_sym, exchange, tv_tf, limit)
            return data
        except Exception as e:
            logger.error(f"TV history xato ({symbol}): {e}")
            return None

    def _fetch_via_scan(self, symbol: str, exchange: str, 
                        tf: str, limit: int) -> Optional[pd.DataFrame]:
        """TradingView scanner API orqali"""
        url = 'https://scanner.tradingview.com/global/scan'
        
        # So'rov ma'lumotlari
        payload = {
            "columns": [
                f"open|{tf}", f"high|{tf}", f"low|{tf}", 
                f"close|{tf}", f"volume|{tf}", "time"
            ],
            "filter": [
                {"left": "exchange", "operation": "in_range", 
                 "right": [exchange]},
                {"left": "name", "operation": "equal", 
                 "right": symbol}
            ],
            "markets": ["global"],
            "symbols": {"tickers": [f"{exchange}:{symbol}"]},
            "sort": {"sortBy": "time", "sortOrder": "desc"},
            "range": [0, min(limit, 200)]
        }
        
        resp = self.session.post(url, json=payload, timeout=15)
        if resp.status_code != 200:
            return None
            
        result = resp.json()
        data_list = result.get('data', [])
        if not data_list:
            return None

        rows = []
        for item in data_list:
            d = item.get('d', [])
            if len(d) >= 6:
                rows.append({
                    'open': d[0], 'high': d[1], 'low': d[2],
                    'close': d[3], 'volume': d[4], 'timestamp': d[5]
                })
        
        if not rows:
            return None
            
        df = pd.DataFrame(rows)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', utc=True)
        df.set_index('timestamp', inplace=True)
        df = df.sort_index()
        df = df.astype(float)
        return df

    def _fetch_via_history(self, symbol: str, exchange: str,
                           tf: str, limit: int) -> Optional[pd.DataFrame]:
        """TradingView history endpoint orqali"""
        import time as _time
        
        url = 'https://history.tradingview.com/history'
        params = {
            'symbol':    f'{exchange}:{symbol}',
            'resolution': tf,
            'from':      int(_time.time()) - (limit * self._tf_to_seconds(tf) * 2),
            'to':        int(_time.time()),
            'countback': limit,
        }
        
        resp = self.session.get(url, params=params, timeout=15)
        if resp.status_code != 200:
            return None
            
        data = resp.json()
        if data.get('s') != 'ok':
            logger.warning(f"TV history: {data.get('s')} — {data.get('errmsg', '')}")
            return None

        df = pd.DataFrame({
            'timestamp': data['t'],
            'open':      data['o'],
            'high':      data['h'],
            'low':       data['l'],
            'close':     data['c'],
            'volume':    data.get('v', [0] * len(data['t'])),
        })
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', utc=True)
        df.set_index('timestamp', inplace=True)
        df = df.sort_index()
        df = df.tail(limit)
        return df

    def get_ticker(self, symbol: str) -> Optional[dict]:
        """Joriy narx ma'lumoti"""
        tv_sym, exchange = _normalize_symbol(symbol)
        try:
            url = 'https://scanner.tradingview.com/global/scan'
            payload = {
                "columns": ["close", "change", "change_abs", "volume"],
                "symbols": {"tickers": [f"{exchange}:{tv_sym}"]},
            }
            resp = self.session.post(url, json=payload, timeout=10)
            if resp.status_code == 200:
                data = resp.json().get('data', [])
                if data:
                    d = data[0].get('d', [])
                    return {
                        'last':       d[0] if len(d) > 0 else 0,
                        'percentage': d[1] if len(d) > 1 else 0,
                        'change':     d[2] if len(d) > 2 else 0,
                        'volume':     d[3] if len(d) > 3 else 0,
                    }
        except Exception as e:
            logger.error(f"TV ticker xato ({symbol}): {e}")
        return None

    def _tf_to_seconds(self, tf: str) -> int:
        """TradingView resolution ni soniyaga o'tkazish"""
        if tf.endswith('D'): return int(tf[:-1] or 1) * 86400
        if tf.endswith('W'): return int(tf[:-1] or 1) * 604800
        return int(tf) * 60
