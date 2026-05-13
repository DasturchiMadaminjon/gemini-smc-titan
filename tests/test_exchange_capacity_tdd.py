import pytest
import os
import yaml
from utils.exchange import ExchangeClient, PERIOD_DAYS

def test_exchange_historical_capacity_tdd():
    """
    TDD: ExchangeClient backtest uchun yetarli tarixiy ma'lumot qamroviga egaligini tekshirish.
    Kamida 60 kunlik 15m va 730 kunlik 1h ma'lumot talab qilinadi.
    """
    # 1. PERIOD_DAYS sozlamalarini tekshirish
    assert PERIOD_DAYS.get("15m") == "60d", "XATO: 15m uchun limit 60 kun bo'lishi shart!"
    assert PERIOD_DAYS.get("1h") == "730d", "XATO: 1h uchun limit 730 kun bo'lishi shart!"
    assert PERIOD_DAYS.get("5m") == "60d", "XATO: 5m uchun limit 60 kun bo'lishi shart!"
    
    print("\nSUCCESS: Exchange historical capacity TDD testi o'tdi!")

@pytest.mark.asyncio
async def test_fetch_ohlcv_limit_handling():
    """
    ExchangeClient.fetch_ohlcv funksiyasi limitni to'g'ri hisoblashini tekshirish.
    """
    with open('config/settings.yaml', 'r') as f:
        cfg = yaml.safe_load(f)
    
    client = ExchangeClient(cfg)
    
    # Biz yfinance ni mock qilamiz, faqat fetch_ohlcv parametrlarini tekshirish uchun
    from unittest.mock import patch, MagicMock
    with patch('utils.exchange._fetch_sync') as mock_fetch:
        mock_fetch.return_value = None # Haqiqiy ma'lumot kerak emas
        
        # 15m so'raymiz
        await client.fetch_ohlcv("XAU/USD", "15m", limit=100)
        
        # _fetch_sync chaqirilganini tekshiramiz
        # call_args: (ticker, interval, period, limit)
        args, _ = mock_fetch.call_args
        assert args[1] == "15m"
        assert args[2] == "60d" # PERIOD_DAYS["15m"]
        assert args[3] >= 100 # fetch_limit >= limit
        
    print("SUCCESS: OHLCV limit handling testi o'tdi!")

if __name__ == "__main__":
    test_exchange_historical_capacity_tdd()
