import os
import time
import asyncio
import pandas as pd
import logging
import requests
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)

class ExchangeClient:
    def __init__(self, config: dict):
        self.config = config
        self.name = config['exchange']['name'].lower()
        logger.info(f"ExchangeClient (Binance Direct) yuklandi.")

    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 300) -> Optional[pd.DataFrame]:
        """OHLCV ma'lumotlarini Binance orqali olish (DNS xatoligini chetlab o'tish)"""
        try:
            # Symbol formatini Binance uchun to'g'rilash
            # XAUUSD -> PAXGUSDT, EURUSD -> EURUSDT
            clean_sym = symbol.replace("/", "").replace("XAUUSD", "PAXGUSDT").replace("XAU/USD", "PAXGUSDT")
            if "USD" in clean_sym and "USDT" not in clean_sym:
                clean_sym = clean_sym.replace("USD", "USDT")
            
            tf_map = {'1h': '1h', '4h': '4h', '1d': '1d', '15m': '15m', '5m': '5m'}
            bin_tf = tf_map.get(timeframe, '1h')

            url = f"https://api.binance.com/api/v3/klines?symbol={clean_sym.upper()}&interval={bin_tf}&limit={limit}"
            
            loop = asyncio.get_event_loop()
            # requests chaqiruvi bloklamasligi uchun executor ishlatamiz
            resp = await loop.run_in_executor(None, requests.get, url, {'timeout': 10})
            
            if resp.status_code == 200:
                data = resp.json()
                df = pd.DataFrame(data, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'qav', 'num_trades', 'taker_base', 'taker_quote', 'ignore'
                ])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
                df.set_index('timestamp', inplace=True)
                return df[['open', 'high', 'low', 'close', 'volume']].astype(float)
            else:
                logger.warning(f"Binance API Status {resp.status_code} ({clean_sym})")
        except Exception as e:
            logger.debug(f"Binance Error ({symbol}): {e}")

        return None

    def get_balance(self): return None
    def create_order(self, *args, **kwargs): return None
