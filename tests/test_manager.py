import pytest
from unittest.mock import MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.manager import TradeManager

class TestManager:
    def test_manager_initialization(self):
        manager = TradeManager(MagicMock(), MagicMock(), MagicMock())
        assert manager is not None
