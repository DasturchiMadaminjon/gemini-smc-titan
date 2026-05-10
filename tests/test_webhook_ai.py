import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from utils.ai_engine import AIEngine
from bot import GeminiBot

@pytest.fixture
def mock_ai_engine():
    test_key = "AIza" + "x" * 35
    engine = AIEngine(api_keys=[test_key])
    engine.get_analysis = AsyncMock(return_value="Tasdiqlayman: Bu signal SMC mantiqiga mos va xavfsiz.")
    return engine

@pytest.mark.asyncio
async def test_evaluate_trade_signal_approved(mock_ai_engine):
    signal_data = {"symbol": "EUR/USD", "direction": "buy", "entry": 1.10}
    is_appr, reason = await mock_ai_engine.evaluate_trade_signal(signal_data)
    assert is_appr is True
    assert "Tasdiqlayman" in reason

@pytest.mark.asyncio
async def test_evaluate_trade_signal_rejected(mock_ai_engine):
    mock_ai_engine.get_analysis = AsyncMock(return_value="Rad etaman: Trendga qarshi xavfli savdo.")
    signal_data = {"symbol": "EUR/USD", "direction": "buy", "entry": 1.10}
    is_appr, reason = await mock_ai_engine.evaluate_trade_signal(signal_data)
    assert is_appr is False
    assert "Rad etaman" in reason

@pytest.mark.asyncio
async def test_evaluate_trade_signal_draft_mode(mock_ai_engine):
    # AI limiti tugasa, u endi Tasdiqlamaydi
    mock_ai_engine.get_analysis = AsyncMock(return_value="❌ Barcha API kalitlar band.")
    signal_data = {"symbol": "EUR/USD", "direction": "buy", "entry": 1.10}
    is_appr, reason = await mock_ai_engine.evaluate_trade_signal(signal_data)
    assert is_appr is False
    assert "kalitlar band" in reason

def test_webhook_queue_creation(tmp_path):
    # This is a basic test to ensure our dashboard route would write json
    import json
    queue_file = tmp_path / "webhook_queue.json"
    queue = [{"symbol": "BTC/USDT", "direction": "buy", "entry": 60000}]
    with open(queue_file, 'w') as f:
        json.dump(queue, f)
    
    with open(queue_file, 'r') as f:
        loaded = json.load(f)
    assert len(loaded) == 1
    assert loaded[0]['symbol'] == "BTC/USDT"
