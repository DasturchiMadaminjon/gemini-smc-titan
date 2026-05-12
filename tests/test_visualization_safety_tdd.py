import pytest
import pandas as pd
import numpy as np
from core.indicator import GeminiIndicator, Signal

def test_draw_chart_bytes_numpy_safety():
    """
    TDD: Signal darajalari numpy.float64 bo'lganda draw_chart_bytes 
    xato bermasligini tekshirish (Regression Test).
    """
    indicator = GeminiIndicator({})
    
    # 1. Mock OHLCV ma'lumotlari
    data = {
        'open': np.random.randn(60) + 100,
        'high': np.random.randn(60) + 101,
        'low': np.random.randn(60) + 99,
        'close': np.random.randn(60) + 100,
        'volume': np.random.randint(100, 1000, 60)
    }
    df = pd.DataFrame(data)
    now = pd.Timestamp.now()
    df.index = pd.date_range(end=now, periods=60, freq='15min')
    
    # 2. Mock Signal (Darajalar numpy.float64 formatida!)
    mock_signal = Signal(
        direction='BUY',
        symbol='BTC/USDT',
        entry=np.float64(100.5),
        sl=np.float64(98.2),
        tp1=np.float64(105.0),
        tp2=107.0,
        tp3=110.0,
        quality=85.0,
        reason='Test',
        timestamp=now
    )
    
    # 3. Grafik chizishni tekshirish
    chart_bytes = indicator.draw_chart_bytes(df, "BTC/USDT", mock_signal)
    
    # 4. Tasdiqlash
    assert isinstance(chart_bytes, bytes), "Natija bytes formatida bo'lishi kerak!"
    assert len(chart_bytes) > 0, "Rasm bo'sh bo'lmasligi kerak!"
    assert chart_bytes != b"", "Grafik chizishda xatolik yuz berdi (Numpy type error?)"
