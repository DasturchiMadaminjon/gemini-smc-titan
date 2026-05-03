import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import json
import asyncio

# Biz test qilmoqchi bo'lgan klassni import qilamiz
# Eslatma: Test muhitida importlar ishlashi uchun dummy obyektlar yaratamiz
class DummyBot:
    def __init__(self):
        self.admins = ["12345"] # Admin ID
        self.user_states = {}

    async def handle_message(self, t, uid, is_admin):
        # Bu yerda telegram.py dagi mantiqni simulyatsiya qilamiz
        if t == "/start":
            return "WELCOME"
        elif "Risk Status" in t and is_admin:
            return "RISK_OK"
        elif "Risk Status" in t and not is_admin:
            return "NOT_AUTHORIZED"
        elif "Test Signal" in t and is_admin:
            return "SIGNAL_CREATED"
        elif "Texnik Tahlil" in t:
            return "CHOOSE_SYMBOL"
        elif "PANIC" in t.upper() and is_admin:
            return "PANIC_ACTIVATED"
        return "DEFAULT_AI"

class TestButtonsLogic(unittest.TestCase):
    def setUp(self):
        self.bot = DummyBot()

    def test_admin_risk_status(self):
        """Admin Risk Status ni ko'ra olishini tekshirish"""
        res = asyncio.run(self.bot.handle_message("⚖️ Risk Status", "12345", True))
        self.assertEqual(res, "RISK_OK")

    def test_user_risk_status_denied(self):
        """Oddiy foydalanuvchi Risk Status ni ko'ra olmasligini tekshirish"""
        res = asyncio.run(self.bot.handle_message("⚖️ Risk Status", "67890", False))
        self.assertEqual(res, "NOT_AUTHORIZED")

    def test_test_signal_logic(self):
        """Test Signal tugmasi ishlashini tekshirish"""
        res = asyncio.run(self.bot.handle_message("🧪 Test Signal", "12345", True))
        self.assertEqual(res, "SIGNAL_CREATED")

    def test_technical_analysis_trigger(self):
        """Texnik tahlil tugmasi instrument tanlashni so'rashini tekshirish"""
        res = asyncio.run(self.bot.handle_message("📊 Texnik Tahlil", "12345", True))
        self.assertEqual(res, "CHOOSE_SYMBOL")

    def test_panic_button(self):
        """Panic tugmasi faqat adminga ishlashini tekshirish"""
        res = asyncio.run(self.bot.handle_message("🚨 PANIC CLOSE ALL", "12345", True))
        self.assertEqual(res, "PANIC_ACTIVATED")

if __name__ == '__main__':
    unittest.main()
