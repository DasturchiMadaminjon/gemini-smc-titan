import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from bot import GeminiBot

@pytest.mark.asyncio
async def test_universal_html_sanitization():
    """TDD: AI javobidagi maxsus belgilarni (&, <, >) universal escape qilinishini tekshirish"""
    
    # Mock configuration
    config = {
        'telegram': {'bot_token': 'test_token', 'admins': [123]},
        'gemini_ai': {'api_keys': ['key1']}
    }
    
    # Botni mock qilamiz
    with patch('utils.database.DatabaseManager'), \
         patch('utils.telegram.TelegramNotifier'), \
         patch('utils.ai_engine.AIEngine'):
        
        bot = GeminiBot()
        bot.cfg = config # Manual config override
        bot.telegram.send = AsyncMock()
        bot.telegram.get_ai_analysis = AsyncMock()
        
        # Test ma'lumotlari: AI javobida Telegramni buzuvchi belgilar bor
        dangerous_res = "Narx < 4700 va RSI > 70. Support & Resistance zonasi."
        expected_res = "Narx &lt; 4700 va RSI &gt; 70. Support &amp; Resistance zonasi."
        
        bot.telegram.get_ai_analysis.return_value = dangerous_res
        
        # AI so'rovini simulyatsiya qilamiz
        req = {'chat_id': 123, 'type': 'chat', 'symbol': 'GOLD', 'text': 'tahlil qil'}
        await bot._handle_ai(req)
        
        # Telegramga yuborilgan xabarni tekshiramiz
        args, kwargs = bot.telegram.send.call_args
        sent_text = args[0]
        
        assert expected_res in sent_text, "Maxsus belgilar (&, <, >) to'g'ri escape qilinmadi!"
        assert "<" not in sent_text.split("AI CHAT TAHLILI (GOLD):</b>\n\n")[1], "Asl '<' belgisi xabarda qolib ketgan!"
        assert ">" not in sent_text.split("AI CHAT TAHLILI (GOLD):</b>\n\n")[1], "Asl '>' belgisi xabarda qolib ketgan!"
        assert "& " not in sent_text, "Asl '&' belgisi xabarda qolib ketgan!"

        print("\nSUCCESS: Universal HTML Sanitization TDD testi o'tdi!")

if __name__ == "__main__":
    asyncio.run(test_universal_html_sanitization())
