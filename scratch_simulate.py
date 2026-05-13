import asyncio
import os
import threading
from unittest.mock import AsyncMock, MagicMock
from utils.telegram import TelegramNotifier
import bot
from datetime import datetime, timezone

async def test():
    config = {'telegram': {'bot_token': 'dummy'}, 'gemini_ai': {'api_keys': ['dummy']}}
    lock = threading.Lock()
    os.environ['TELEGRAM_BOT_TOKEN'] = 'dummy'
    
    notifier = TelegramNotifier(config, lock)
    uid = '123'
    notifier.user_states[uid] = "in_session"
    notifier.user_modules[uid] = "chat"
    
    user_text = "shu signal bilan real savdo qilganimda natija nima bo'lar edi? tarixni  ko'rib ayib ber. [12/05/2026 21:58] @awssignal_bot: YANGI SIGNAL: XAU/USD"
    
    update_data = {
        'update_id': 999,
        'message': {
            'from': {'id': int(uid)},
            'text': user_text
        }
    }
    
    bs = {'ai_requests': []}
    cfg_full = {'symbols': ['XAU/USD']}
    
    await notifier.handle_update(update_data, bs, cfg_full, MagicMock(), "dummy.txt")
    req = bs['ai_requests'][0]
    
    b = bot.GeminiBot()
    b.exchange.fetch_ohlcv = AsyncMock(return_value=MagicMock(empty=False, tail=MagicMock(return_value=MagicMock(to_string=MagicMock(return_value="OHLC DATA DUMMY")))))
    b.telegram.get_ai_analysis = AsyncMock(return_value="AI JAVOBI")
    b.telegram.send = AsyncMock()
    
    await b._handle_ai(req)
    
    args, kwargs = b.telegram.get_ai_analysis.call_args
    prompt = args[0]
    with open("prompt_dump.txt", "w", encoding="utf-8") as f:
        f.write(prompt)

if __name__ == "__main__":
    asyncio.run(test())
