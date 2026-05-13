import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from utils.telegram import TelegramNotifier
import threading

@pytest.mark.asyncio
async def test_smart_message_chunking():
    # Setup Notifier
    config = {'telegram': {'bot_token': 'dummy'}, 'gemini_ai': {'api_keys': ['key']}}
    lock = threading.Lock()
    notifier = TelegramNotifier(config, lock)
    
    class MockResponse:
        status = 200
        async def json(self): return {}
        async def text(self): return "ok"
    
    class MockContextManager:
        async def __aenter__(self): return MockResponse()
        async def __aexit__(self, exc_type, exc, tb): pass

    mock_session = AsyncMock()
    mock_session.post = lambda *args, **kwargs: MockContextManager()
    notifier.get_session = AsyncMock(return_value=mock_session)
    
    # We will track calls manually since we replaced it with a lambda
    calls = []
    original_post = mock_session.post
    def fake_post(*args, **kwargs):
        calls.append((args, kwargs))
        return MockContextManager()
    mock_session.post = fake_post
    
    # Create a long message that is > 4000 chars, with paragraph breaks
    part1 = "A" * 3000
    part2 = "B" * 2000
    long_text = part1 + "\n\n" + part2
    
    # Send the message
    result = await notifier.send(long_text, cid="12345")
    
    # Assertions
    assert result is True, "Xabar yuborish muvaffaqiyatsiz bo'ldi"
    
    # Tekshiramizki, post() kamida 2 marta chaqirilgan
    assert len(calls) == 2, f"Kutilgan chaqiruvlar soni 2, lekin {len(calls)} ta bo'ldi"
    
    # 1-chunk "A" lardan va 2-chunk "B" lardan iborat bo'lishi kerak.
    # Ular aniq "\n\n" bo'yicha bo'linishi kerak, so'zning o'rtasidan emas.
    args1, kwargs1 = calls[0]
    args2, kwargs2 = calls[1]
    
    chunk1 = kwargs1['json']['text']
    chunk2 = kwargs2['json']['text']
    
    # chunk1 faqat A lardan iborat bo'lishi kerak va oxirida \n\n bo'lmasligi kerak (yoki bo'lishi ham mumkin, lekin B qo'shilmasligi kerak)
    assert "B" not in chunk1, "1-chunk qismiga 2-qism aralashib qoldi (xato chunking)!"
    assert "A" not in chunk2, "2-chunk qismiga 1-qism aralashib qoldi (xato chunking)!"
    assert len(chunk1) <= 4000, "1-chunk hajmi 4000 dan oshib ketdi!"
    assert len(chunk2) <= 4000, "2-chunk hajmi 4000 dan oshib ketdi!"

    print("SUCCESS: Smart Chunking TDD testi o'tdi!")

if __name__ == "__main__":
    asyncio.run(test_smart_message_chunking())
