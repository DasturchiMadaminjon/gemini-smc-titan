import pytest
import asyncio
import threading
from unittest.mock import MagicMock, AsyncMock
from bot import GeminiBot

@pytest.mark.asyncio
async def test_monitor_loop_error_handling(monkeypatch):
    """
    _monitor_loop dagi xatolarni ushlash mexanizmini tekshirish.
    """
    # 1. Database mock
    mock_db = MagicMock()
    mock_db.get_pending_signals.return_value = [
        (1, "ERROR/USD", "BUY", 100, 90, 110),
        (2, "GOOD/USD", "BUY", 100, 90, 110)
    ]

    # 2. Exchange mock
    mock_exchange = MagicMock()
    async def fake_fetch_ohlcv(symbol, timeframe, limit):
        import pandas as pd
        if symbol == "ERROR/USD":
            raise Exception("API Error")
        return pd.DataFrame({'close': [115.0]}, index=[pd.Timestamp.now()])
    mock_exchange.fetch_ohlcv.side_effect = fake_fetch_ohlcv

    # 3. Telegram mock
    mock_telegram = AsyncMock()

    # 4. Bot creation with all required attributes
    bot = GeminiBot.__new__(GeminiBot)
    bot.db = mock_db
    bot.exchange = mock_exchange
    bot.telegram = mock_telegram
    bot.cfg = {'tp': {'tp1_mult': 1.5}, 'trend': {'risk_perc': 2.0}}
    bot.bot_state = {'terminal': {'balance': 1000.0}, 'loss_streak': 0}
    bot.lock = threading.Lock()
    bot.trades = MagicMock()
    bot.trades.loss_streak = 0

    # 5. Loop exit mechanism
    loop_count = 0
    async def mock_sleep(seconds):
        nonlocal loop_count
        loop_count += 1
        if loop_count >= 1:
            raise asyncio.CancelledError("Loop exit")
    
    monkeypatch.setattr("asyncio.sleep", mock_sleep)
    monkeypatch.setattr("bot.save_state", MagicMock())

    # 6. Execute loop
    with pytest.raises(asyncio.CancelledError):
        await bot._monitor_loop()

    # 7. Verification
    assert mock_exchange.fetch_ohlcv.call_count == 2
    assert mock_db.update_signal_result.call_count == 1
    assert mock_db.update_signal_result.call_args[0][0] == 2 # GOOD/USD sid=2
    assert "WIN" in mock_db.update_signal_result.call_args[0][1]
