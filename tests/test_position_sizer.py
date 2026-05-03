"""
tests/test_position_sizer.py
Position Sizer (lot hisoblash) logikasini tekshirish.
"""
import pytest
from utils.position_sizer import calculate_position, format_position_line, INSTRUMENT_SPECS


class TestCalculatePosition:
    """calculate_position() funksiyasi uchun testlar"""

    def test_eurusd_basic(self):
        """EUR/USD uchun oddiy lot hisoblash."""
        result = calculate_position(
            balance=10000.0, risk_pct=2.0,
            entry=1.1000, sl=1.0950, symbol="EUR/USD"
        )
        assert result["risk_dollar"] == 200.0
        assert result["lot_size"] > 0
        assert result["unit"] == "Lot"

    def test_xauusd_gold(self):
        """XAU/USD uchun lot hisoblash."""
        result = calculate_position(
            balance=5000.0, risk_pct=2.0,
            entry=2350.0, sl=2340.0, symbol="XAU/USD"
        )
        assert result["risk_dollar"] == 100.0
        assert result["lot_size"] >= 0.01
        assert result["unit"] == "Lot"

    def test_btcusdt_crypto(self):
        """BTC/USDT uchun lot hisoblash."""
        result = calculate_position(
            balance=10000.0, risk_pct=1.0,
            entry=65000.0, sl=64000.0, symbol="BTC/USDT"
        )
        assert result["risk_dollar"] == 100.0
        assert result["unit"] == "BTC"

    def test_zero_sl_distance(self):
        """SL = Entry bo'lsa, lot_size 0 qaytadi."""
        result = calculate_position(
            balance=10000.0, risk_pct=2.0,
            entry=1.1000, sl=1.1000, symbol="EUR/USD"
        )
        assert result["lot_size"] == 0.0

    def test_minimum_lot_enforced(self):
        """Hisoblangan lot minimum dan kam bo'lmaydi."""
        # Juda katta SL → juda kichik lot → min_lot ga teng bo'lishi kerak
        result = calculate_position(
            balance=100.0, risk_pct=1.0,
            entry=1.1000, sl=1.0000, symbol="EUR/USD"
        )
        assert result["lot_size"] >= INSTRUMENT_SPECS["EUR/USD"]["min_lot"]

    def test_risk_dollar_calculation(self):
        """Risk dollar to'g'ri hisoblanadi."""
        result = calculate_position(
            balance=8000.0, risk_pct=2.5,
            entry=1.2000, sl=1.1950, symbol="GBP/USD"
        )
        assert result["risk_dollar"] == 200.0

    def test_unknown_symbol_uses_default(self):
        """Nomalum instrument EUR/USD sozlamalarini ishlatadi."""
        result = calculate_position(
            balance=5000.0, risk_pct=2.0,
            entry=1.5000, sl=1.4950, symbol="UNKNOWN/PAIR"
        )
        assert result is not None
        assert result["lot_size"] >= 0


class TestFormatPositionLine:
    """format_position_line() funksiyasi uchun testlar"""

    def test_returns_string(self):
        """Natija string bo'ladi."""
        result = format_position_line(
            balance=10000.0, risk_pct=2.0,
            entry=2350.0, sl=2340.0, tp1=2360.0, tp2=2370.0,
            symbol="XAU/USD"
        )
        assert isinstance(result, str)

    def test_contains_risk_info(self):
        """Risk va lot ma'lumotlari kiritilgan."""
        result = format_position_line(
            balance=10000.0, risk_pct=2.0,
            entry=1.1000, sl=1.0950, tp1=1.1100, tp2=1.1200,
            symbol="EUR/USD"
        )
        assert "Risk" in result
        assert "200" in result  # 2% of 10000

    def test_zero_sl_returns_simple_line(self):
        """SL=Entry bo'lsa sodda risk qatori qaytadi."""
        result = format_position_line(
            balance=5000.0, risk_pct=2.0,
            entry=1.1000, sl=1.1000, tp1=1.1100, tp2=1.1200,
            symbol="EUR/USD"
        )
        assert "Risk" in result
