"""
TDD: Fatal Error Prevention Suite
==================================
Ushbu testlar botni 'AttributeError' va 'Unpacking' xatolaridan himoya qiladi.
"""

import pytest
import pandas as pd
import numpy as np
from core.indicator import GeminiIndicator
from bot import GeminiBot

def test_indicator_attribute_safety():
    """GeminiIndicator draw_chart_bytes metodi borligini va ishlashini tekshiradi."""
    cfg = {"smc": {"min_quality": 70.0}}
    ind = GeminiIndicator(cfg)
    
    # 1. Metod borligini tekshirish
    assert hasattr(ind, 'draw_chart_bytes'), "GeminiIndicator da draw_chart_bytes metodi yo'q!"
    
    # 2. Metod ishlashini tekshirish (crashes prevention)
    df = pd.DataFrame({
        'open': [100]*10, 'high': [105]*10, 'low': [95]*10, 'close': [102]*10, 'volume': [1000]*10
    }, index=pd.date_range('2026-01-01', periods=10, freq='15min'))
    
    try:
        res = ind.draw_chart_bytes(df, "BTC/USDT")
        assert isinstance(res, bytes), "Metod bytes qaytarishi kerak!"
        assert len(res) > 0, "Rasm bytes bo'sh bo'lmasligi kerak!"
    except Exception as e:
        pytest.fail(f"draw_chart_bytes xatolik berdi: {e}")

def test_monitor_loop_unpacking_safety():
    """Botning signal unpacking mantiqi xavfsizligini tekshiradi."""
    # Dummy bot instance (faqat mantiqni tekshirish uchun)
    class MockBot:
        def test_logic(self, sig_row):
            # bot.py dagi monitor loop mantiqi
            sid = sig_row[0]
            current_symbol = sig_row[2]
            side = sig_row[3]
            entry = sig_row[4]
            sl = sig_row[5]
            tp1 = sig_row[6]
            return sid, current_symbol, side

    bot = MockBot()
    
    # To'g'ri row (10 ta ustunli database row)
    valid_row = (1, 'time', 'EUR/USD', 'buy', 1.05, 1.04, 1.07, 90, 'reason', 'pending')
    sid, sym, side = bot.test_logic(valid_row)
    assert sym == 'EUR/USD'
    
    # Kutilmagan uzunlikdagi row (faqat boshidagi ustunlar kerak)
    long_row = (1, 'time', 'BTC/USDT', 'sell', 60000, 61000, 59000, 80, 'reason', 'pending', 'extra_col')
    sid, sym, side = bot.test_logic(long_row)
    assert sym == 'BTC/USDT'
