import pytest
from unittest.mock import patch, MagicMock
import sys
import os
import threading

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.dashboard import create_app

class TestDashboard:
    def test_dashboard_initialization(self):
        lock = threading.Lock()
        app = create_app({}, {}, lock)
        app.config['TESTING'] = True
        with app.test_client() as client:
            response = client.get('/')
            assert response.status_code in [200, 302]
