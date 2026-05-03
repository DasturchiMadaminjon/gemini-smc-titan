import pytest
from unittest.mock import MagicMock, patch
from utils.analytics import generate_trade_report

class TestGenerateTradeReport:
    """generate_trade_report() funksiyasi uchun yangilangan testlar"""

    @patch('utils.analytics.DatabaseManager')
    def test_empty_signals_returns_default_message(self, mock_db_class):
        """Signal yo'q bo'lsa standart xabar qaytadi."""
        mock_db = MagicMock()
        mock_db.get_stats.return_value = {'total_signals': 0}
        mock_db_class.return_value = mock_db
        
        result = generate_trade_report()
        assert "hech qanday signal" in result.lower()

    @patch('utils.analytics.DatabaseManager')
    def test_report_contains_win_loss_counts(self, mock_db_class):
        """Hisobot bazadagi statistikani to'g'ri ko'rsatishi kerak."""
        mock_db = MagicMock()
        mock_db.get_stats.return_value = {
            'total_signals': 10,
            'total': 5,
            'tp': 3,
            'sl': 2,
            'winrate': 60.0,
            'profit': 4.5
        }
        mock_db_class.return_value = mock_db
        
        result = generate_trade_report()
        assert "10" in result        # Jami yuborilgan
        assert "3" in result         # Win
        assert "2" in result         # Loss
        assert "60.0" in result      # Win-rate
        assert "4.5" in result       # Profit
