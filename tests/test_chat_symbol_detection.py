import pytest
import os
import threading
from unittest.mock import MagicMock, AsyncMock
from utils.telegram import TelegramNotifier

@pytest.mark.asyncio
async def test_chat_module_symbol_detection():
    # 1. Setup mock bot
    config = {'telegram': {'bot_token': 'dummy_token_123'}, 'gemini_ai': {'api_keys': ['dummy_key']}}
    lock = threading.Lock()
    
    # Prevent bot from making real web requests on init
    os.environ['TELEGRAM_BOT_TOKEN'] = 'dummy'
    
    notifier = TelegramNotifier(config, lock)
    uid = '12345'
    
    # 2. Foydalanuvchi "AI Chat Assistant" ga kirgan deb tasavvur qilamiz
    notifier.user_states[uid] = "in_session"
    notifier.user_modules[uid] = "chat"
    
    # Mock funksiyalar (haqiqiy API chaqirilmasligi uchun)
    notifier.send = AsyncMock()
    notifier.send_action = AsyncMock()
    notifier.get_session = AsyncMock()
    
    # 3. Foydalanuvchining xabari: "XAU/USD hozirgi narxi qancha?"
    update_data = {
        'update_id': 999,
        'message': {
            'from': {'id': int(uid)},
            'text': "XAU/USD hozirgi narxi qancha?"
        }
    }
    
    bs = {'ai_requests': []}
    cfg_full = {'symbols': ['XAU/USD', 'BTC/USDT']}
    
    # 4. Update ni qayta ishlash
    await notifier.handle_update(update_data, bs, cfg_full, MagicMock(), "dummy_offset.txt")
    
    # 5. Tekshirish (Assert)
    assert len(bs['ai_requests']) > 0, "AI so'rovi qo'shilmadi!"
    req = bs['ai_requests'][0]
    
    # O'zgarishdan oldin bu yerda 'SMC' chiqardi. Endi 'XAU/USD' chiqishi kerak!
    assert req['symbol'] == 'XAU/USD', f"XATO: Simbol topilmadi. Kutilgan: XAU/USD, Olingan: {req['symbol']}"
    assert req['type'] == 'chat', f"XATO: Modul turi noto'g'ri: {req['type']}"
    
    print("SUCCESS: Muvaffaqiyat! AI Chat moduli xabar ichidan to'g'ri instrumentni (XAU/USD) topdi.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_chat_module_symbol_detection())
