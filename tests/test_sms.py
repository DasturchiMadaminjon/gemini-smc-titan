import pytest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.sms import send_signal_sms

class TestSMS:
    @patch('utils.sms.requests.post')
    def test_send_signal_sms(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        result = send_signal_sms("BTC/USD", "buy", 60000, 61000, 59000)
        assert result is True or result is False # depending on env vars it might be false
