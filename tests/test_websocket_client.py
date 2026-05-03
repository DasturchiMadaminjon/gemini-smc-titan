import pytest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.websocket_client import BinanceWS

class TestWebsocketClient:
    def test_websocket_client_initialization(self):
        client = BinanceWS(symbols=["BTCUSDT"], callback=lambda x: x)
        assert client is not None
        assert hasattr(client, 'start')
        assert hasattr(client, 'stop')
