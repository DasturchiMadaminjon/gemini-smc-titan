import pytest
from unittest.mock import MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.watcher import MarketWatcher

class TestWatcher:
    def test_watcher_initialization(self):
        watcher = MarketWatcher(MagicMock(), MagicMock())
        assert watcher is not None
