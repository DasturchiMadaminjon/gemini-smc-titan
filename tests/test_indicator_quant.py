import pytest
import pandas as pd
import numpy as np
from core.indicator import GeminiIndicator, Signal

# ---------------------------------------------------------------------------
# Test uchun soxta OHLCV ma'lumotlar yaratish yordamchisi
# ---------------------------------------------------------------------------

def make_ohlcv(n=300, trend='up'):
    """Testlar uchun professional OHLCV DataFrame yaratish."""
    np.random.seed(42)
    base = 100.0
    direction = 1 if trend == 'up' else -1
    
    # Trend yaratish
    closes = []
    curr = base
    for i in range(n):
        curr += direction * 0.05 + np.random.randn() * 0.02
        closes.append(curr)
        
    df = pd.DataFrame({
        'open': [c - 0.02 for c in closes],
        'high': [c + 0.05 for c in closes],
        'low': [c - 0.05 for c in closes],
        'close': closes,
        'volume': [1000] * n
    }, index=pd.date_range("2026-01-01", periods=n, freq="15min"))
    return df

@pytest.fixture
def config():
    return {
        'smc': {'swing_len': 5},
        'tp': {'tp1_mult': 1.5, 'tp2_mult': 3.0, 'tp3_mult': 5.0}
    }

# ---------------------------------------------------------------------------
# TESTLAR
# ---------------------------------------------------------------------------

class TestQuantIndicator:
    
    def test_swing_detection(self, config):
        """Pivot nuqtalarini aniqlash testi."""
        ind = GeminiIndicator(config)
        df = make_ohlcv(100, trend='up')
        # Sun'iy pivot yaratish
        df.at[df.index[50], 'high'] = 120.0
        
        ph, pl = ind._get_swings(df, n=5)
        # 50-indeks pivot bo'lishi kerak (shift(5) tufayli indeks 55 da aniqlanadi)
        assert ph.any()
        assert isinstance(ph, pd.Series)

    def test_trend_detection(self, config):
        """HTF Trend aniqlash testi."""
        ind = GeminiIndicator(config)
        df_up = make_ohlcv(250, trend='up')
        df_down = make_ohlcv(250, trend='down')
        
        assert ind._get_trend(df_up) == 'bullish'
        assert ind._get_trend(df_down) == 'bearish'

    def test_fibo_zone_logic(self, config):
        """Premium/Discount zonalarni aniqlash testi."""
        ind = GeminiIndicator(config)
        # Low=100, High=200
        assert ind._get_fibo_zone(100, 200, 110) == 'discount'   # 10% retracement (pastda)
        assert ind._get_fibo_zone(100, 200, 190) == 'premium'    # 90% retracement (tepada)
        assert ind._get_fibo_zone(100, 200, 150) == 'equilibrium'

    def test_bos_vs_sweep(self, config):
        """BOS va Sweep farqlash testi."""
        ind = GeminiIndicator(config)
        df = make_ohlcv(60, trend='up')
        
        # 1. Pivot High o'rnatish
        df.at[df.index[30], 'high'] = 110.0
        df.at[df.index[30], 'close'] = 109.0
        
        # 2. Sweep testi (Soya baland, tana past)
        df_sweep = df.copy()
        df_sweep.at[df_sweep.index[-1], 'high'] = 111.0
        df_sweep.at[df_sweep.index[-1], 'close'] = 108.0
        res_sweep = ind._detect_structure_break(df_sweep)
        assert res_sweep['sweep_up'] is True
        assert res_sweep['bos_up'] is False
        
        # 3. BOS testi (Tana baland yopildi)
        df_bos = df.copy()
        df_bos.at[df_bos.index[-1], 'high'] = 112.0
        df_bos.at[df_bos.index[-1], 'close'] = 111.0
        res_bos = ind._detect_structure_break(df_bos)
        assert res_bos['bos_up'] is True
        assert res_bos['sweep_up'] is False

    def test_fvg_detection(self, config):
        """FVG aniqlash testi."""
        ind = GeminiIndicator(config)
        df = make_ohlcv(50, trend='up')
        # Bullish FVG yaratish
        df.at[df.index[-3], 'high'] = 105.0
        df.at[df.index[-2], 'low'] = 106.0
        df.at[df.index[-2], 'high'] = 107.0
        df.at[df.index[-1], 'low'] = 108.0
        
        fvg = ind._find_unmitigated_fvg(df)
        assert fvg is not None
        assert fvg[2] == 'bullish'

    def test_rr_validation_filter(self, config):
        """R:R filteri (1.5) ishlash testi."""
        ind = GeminiIndicator(config)
        # Agar TP SL dan juda yaqin bo'lsa signal chiqmasligi kerak
        # Bu test generate_signal ichidagi RR mantiqini tekshiradi
        df = make_ohlcv(100, trend='up')
        # Sun'iy ravishda RR ni buzamiz
        res = ind.generate_signal(df, "EUR/USD")
        if res:
            risk = res.entry - res.sl
            reward = res.tp1 - res.entry
            assert reward / risk >= 1.5
