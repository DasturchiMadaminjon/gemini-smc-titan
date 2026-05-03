import pytest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.mt5_signal import MT5SignalSender

class TestMT5Signal:
    @patch('utils.mt5_signal.mt5', create=True)
    def test_mt5_initialization(self, mock_mt5):
        mock_mt5.initialize.return_value = True
        executor = MT5SignalSender(MagicMock())
        assert executor is not None
