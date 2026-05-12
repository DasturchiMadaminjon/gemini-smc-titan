import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from utils.exchange import ExchangeClient, _fetch_sync

def test_fetch_sync_retry_logic():
    """
    TDD: _fetch_sync funksiyasining retry mantiqini tekshirish.
    """
    # 1. Mock yf.Ticker
    with patch('utils.exchange.yf.Ticker') as mock_ticker_class:
        mock_instance = MagicMock()
        mock_ticker_class.return_value = mock_instance
        
        # yfinance odatda katta harfli ustunlar qaytaradi
        valid_df = pd.DataFrame({
            'Open': [100.0], 'High': [105.0], 'Low': [95.0], 'Close': [102.0], 'Volume': [1000]
        }, index=[pd.Timestamp.now(tz='UTC')])
        
        mock_instance.history.side_effect = [
            pd.DataFrame(), # 1
            pd.DataFrame(), # 2
            valid_df        # 3
        ]
        
        # 2. _fetch_sync ni chaqiramiz (Sinxron)
        # Importlar uchun mock biroz kutishni tezlashtirish uchun time.sleep ni patch qilamiz
        with patch('time.sleep', return_value=None):
            result = _fetch_sync("BTC-USD", "15m", "1d", 1)
        
        # 3. Tasdiqlash
        assert result is not None, "Retry 3-urinishda ishlashi kerak edi!"
        assert len(result) == 1
        assert result['close'].iloc[0] == 102.0
        assert mock_instance.history.call_count == 3

def test_symbol_to_yahoo_mapping():
    """
    TDD: Simvollar Yahoo formatiga to'g'ri o'girilishini tekshirish.
    """
    from utils.exchange import _to_yahoo
    assert _to_yahoo("XAU/USD") == "GC=F"
    assert _to_yahoo("BTC/USDT") == "BTC-USD"
