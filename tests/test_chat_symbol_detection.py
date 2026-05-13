import pytest
import os
import threading
from unittest.mock import MagicMock, AsyncMock
import pandas as pd
import bot

@pytest.mark.asyncio
async def test_full_ai_context_injection():
    # 1. Setup mock environment
    os.environ['TELEGRAM_BOT_TOKEN'] = 'dummy'
    b = bot.GeminiBot()
    
    # Mock Exchange to return some fake data
    data = {
        'open': [4670.0] * 48,
        'high': [4720.0] * 48,
        'low': [4650.0] * 48,
        'close': [4680.0] * 48,
        'volume': [1000] * 48
    }
    mock_df = pd.DataFrame(data)
    
    b.exchange.fetch_ohlcv = AsyncMock(return_value=mock_df)
    b.telegram.get_ai_analysis = AsyncMock(return_value="AI JAVOBI TEST")
    b.telegram.send = AsyncMock()
    b.telegram.send_action = AsyncMock()
    
    # 2. Simulate user request
    req = {
        'chat_id': '12345',
        'symbol': 'XAU/USD',
        'type': 'chat',
        'text': "XAU/USD narxi haqida tahlil ber."
    }
    
    # 3. Handle AI
    await b._handle_ai(req)
    
    # 4. Assertions
    args, kwargs = b.telegram.get_ai_analysis.call_args
    prompt = args[0]
    
    # Promptda jadval borligini tekshirish
    assert "NARXLAR JADVALI (OHLC):" in prompt, "XATO: Promptda OHLC jadvali yo'q!"
    assert "4670.0" in prompt, "XATO: Jadval ma'lumotlari promptga qo'shilmagan!"
    assert "XAU/USD" in prompt, "XATO: Simbol nomi promptda yo'q!"
    
    # System Instruction borligini tekshirish
    assert "Foydalanuvchi taqdim etgan signal natijasini aniqlashingiz uchun" in prompt
    assert "DIQQAT: Matn oxirida berilgan OHLC narxlar jadvalidan to'liq foydalaning" in prompt
    
    print("SUCCESS: TDD Test muvaffaqiyatli o'tdi. AI kontekstga OHLC ma'lumotlari to'liq qo'shilmoqda.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_full_ai_context_injection())
