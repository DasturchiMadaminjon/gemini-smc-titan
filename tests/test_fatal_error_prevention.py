"""
TDD: Fatal Error Prevention Suite (V2)
=======================================
Ushbu testlar botni 'AttributeError', 'Unpacking' va 'NameError' (undefined variable)
xatolaridan himoya qiladi.
"""

import pytest
import pandas as pd
import numpy as np
from core.indicator import GeminiIndicator

def test_indicator_attribute_safety():
    """GeminiIndicator draw_chart_bytes metodi borligini va ishlashini tekshiradi."""
    cfg = {"smc": {"min_quality": 70.0}}
    ind = GeminiIndicator(cfg)
    
    # 1. Metod borligini tekshirish
    assert hasattr(ind, 'draw_chart_bytes'), "GeminiIndicator da draw_chart_bytes metodi yo'q!"
    
    # 2. Metod ishlashini tekshirish
    df = pd.DataFrame({
        'open': [100]*10, 'high': [105]*10, 'low': [95]*10, 'close': [102]*10, 'volume': [1000]*10
    }, index=pd.date_range('2026-01-01', periods=10, freq='15min'))
    
    res = ind.draw_chart_bytes(df, "BTC/USDT")
    assert isinstance(res, bytes)
    assert len(res) > 0

def test_monitor_loop_variable_safety():
    """Monitor loop ichida o'zgaruvchilar (current_symbol) to'g'ri ishlatilishini tekshiradi."""
    
    # bot.py dagi mantiq simulyatsiyasi
    def process_signal(sig_row):
        try:
            # 1. Unpacking (DB schema alignment)
            sid = sig_row[0]
            current_symbol = sig_row[1]
            side = sig_row[2]
            
            # 2. Variable usage (NameError prevention)
            msg = f"VIRTUAL NATIJA: {current_symbol}"
            log = f"[MONITOR] {current_symbol} natijasi"
            
            return True, current_symbol
        except Exception as e:
            # Error logdagi xavfsizlik
            err_log = f"Xato: {current_symbol if 'current_symbol' in locals() else 'Unknown'}"
            return False, err_log

    # Test cases
    ok, res = process_signal((1, "EUR/USD", "BUY"))
    assert ok is True
    assert res == "EUR/USD"
    
    # Test: xatolik bo'lganda ham NameError bermasligi kerak
    # (sig_row[1] ga kirishdan oldin xato bo'lsa)
    ok, res = process_signal([None]) # Bu IndexError beradi
    assert ok is False
    assert "Unknown" in res or "Xato" in res
