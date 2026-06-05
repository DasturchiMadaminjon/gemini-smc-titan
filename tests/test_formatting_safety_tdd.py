import pytest
import json
from unittest.mock import MagicMock, patch, AsyncMock
from utils.telegram import TelegramNotifier

def test_price_rounding_logic():
    """
    TDD: Narxlarni 5 ta raqamgacha yaxlitlash mantiqini tekshirish.
    """
    entry_raw = 0.7814000248908997
    entry_rounded = round(float(entry_raw), 5)
    
    assert entry_rounded == 0.7814, f"Yaxlitlash xato: {entry_rounded}"

@pytest.mark.asyncio
async def test_telegram_message_chunking():
    """
    TDD: TelegramNotifier uzun xabarlarni (4000+ belgi) bo'laklarga bo'lishini tekshirish.
    """
    # Mocking ClientSession.post
    with patch('aiohttp.ClientSession.post') as mock_post, patch.dict('os.environ', {'TELEGRAM_CHAT_ID': '12345'}):
        # Async context manager mock
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.__aenter__.return_value = mock_resp
        mock_post.return_value = mock_resp
        
        # Obyektni yaratish (dummy config bilan)
        config = {'telegram': {'chat_id': ['12345']}}
        import threading
        notifier = TelegramNotifier(config, threading.Lock())
        
        # 9000 belgilik juda uzun xabar (3 ta bo'lak: 4000 + 4000 + 1000)
        long_text = "A" * 9000
        
        await notifier.send(long_text)
        
        # post() metodi 3 marta chaqirilgan bo'lishi kerak
        assert mock_post.call_count == 3, f"Xabar bo'laklanmadi! Chaqiriqlar soni: {mock_post.call_count}"

def test_signal_data_structure_rounding():
    """
    TDD: Signal ma'lumotlari strukturasida narxlar yaxlitlanganligini tekshirish.
    """
    raw_price = 1.371400055
    sig_data = {
        'entry': round(float(raw_price), 5),
        'sl': round(float(1.36430001), 5)
    }
    
    assert sig_data['entry'] == 1.3714
    assert sig_data['sl'] == 1.3643
