import pytest
from utils.dashboard import create_app
import threading
from unittest.mock import patch

@pytest.fixture
def client():
    bot_state = {
        'symbols': {'XAU/USD': {'price': 2300.50, 'change': 0.5}},
        'terminal': {'balance': 5000.0, 'equity': 5050.0},
        'ai_requests': [],
        'signals_log': [],
        'last_ai_report': ''
    }
    cfg = {'telegram': {'bot_token': 'test'}}
    lock = threading.Lock()
    
    with patch('os.path.exists', return_value=False):
        app = create_app(bot_state, cfg, lock)
        app.config['TESTING'] = True
        app.secret_key = 'test'
        with app.test_client() as client:
            # Login sessiyasini simulyatsiya qilish
            with client.session_transaction() as sess:
                sess['logged'] = True
            yield client

def test_dashboard_access_with_login(client):
    """Login qilingandan so'ng asosiy sahifa yuklanishini tekshirish."""
    response = client.get('/')
    assert response.status_code == 200
    print("\n✅ Dashboard Access testi o'tdi!")

def test_dashboard_api_data_with_login(client):
    """Login qilingandan so'ng API ma'lumotlar qaytarishini tekshirish."""
    response = client.get('/api/symbols_data')
    assert response.status_code == 200
    data = response.get_json()
    assert 'symbols' in data
    assert 'XAU/USD' in data['symbols']
    print("✅ Dashboard API (Authenticated) testi o'tdi!")

def test_dashboard_favicon_route(client):
    response = client.get('/favicon.ico')
    assert response.status_code in [200, 204]
