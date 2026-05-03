import pytest
from unittest.mock import MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.tradingview import TradingViewClient

class TestTradingView:
    def test_tradingview_initialization(self):
        client = TradingViewClient()
        assert client is not None
