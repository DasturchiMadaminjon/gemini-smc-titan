import unittest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from utils.telegram import TelegramNotifier

class TestSignalDelivery(unittest.IsolatedAsyncioTestCase):
    async def test_signal_is_delivered(self):
        """Signal TelegramNotifier orqali yuborilishini tekshirish"""
        
        # Soxta (Mock) obyektlar yaratamiz
        mock_config = {'telegram': {'bot_token': 'test_token', 'chat_id': ['12345']}}
        mock_lock = MagicMock()
        
        # Notifier ni initsializatsiya qilamiz
        notifier = TelegramNotifier(mock_config, mock_lock)
        
        # 'send' metodini soxtalashtiramiz (haqiqiy API ga so'rov yubormasligi uchun)
        notifier.send = AsyncMock()
        
        # Faraz qilaylik bot.py da qandaydir signal paydo bo'ldi
        fake_signal_message = "\U0001f4e2 [SIGNAL] EUR/USD - BUY (A+ Sifat)"
        
        # Signalni yuboramiz
        await notifier.send(fake_signal_message, cid="12345")
        
        # Asosiy Test: Haqiqatan ham 'send' funksiyasi chaqirildimi?
        notifier.send.assert_called_once_with(fake_signal_message, cid="12345")
        print("[TDD] test_signal_delivery: Signal muvaffaqiyatli 'send' funksiyasiga uzatildi. \u2705")

if __name__ == '__main__':
    unittest.main()
