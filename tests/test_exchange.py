import pytest
from unittest.mock import MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.exchange import ExchangeClient

class TestExchange:
    def test_exchange_initialization(self):
        mock_config = {'exchange': {'name': 'yahoo'}}
        client = ExchangeClient(mock_config)
        assert client is not None
