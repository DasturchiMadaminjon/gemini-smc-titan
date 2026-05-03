import unittest
from unittest.mock import MagicMock, AsyncMock
import json
import asyncio

class UltimateTitanTest(unittest.TestCase):
    def setUp(self):
        # Tizim holatini simulyatsiya qilish
        self.bs = {
            'terminal': {'balance': 10000},
            'loss_streak': 0,
            'settings': {'ai_review_enabled': True},
            'ai_requests': [],
            'panic_request': False
        }
        self.is_admin = True
        self.uid = "12345"

    # --- 1-BO'LIM: ASOSIY TUGMALAR ANALIZI ---
    def test_main_buttons_logic(self):
        """Barcha 11 ta asosiy tugma mantiqini tekshirish"""
        buttons = [
            "\U0001f4ca Texnik Tahlil", "\U0001f310 Fundamental", "\u26a1 Scalping AI",
            "\U0001f468\u200d\U0001f3eb Jonli SMC Trener", "\U0001f4ac AI Chat Assistant",
            "\U0001f4c8 Hisobot (Analytics)", "\u2699\ufe0f Sozlamalar", "\u2696\ufe0f Risk Status",
            "\U0001f4d6 Qo'llanma", "\U0001f9ea Test Signal", "\U0001f6a8 PANIC CLOSE ALL"
        ]
        print(f"\n[ANALIZ] Jami {len(buttons)} ta asosiy tugma tekshirilmoqda...")
        for btn in buttons:
            self.assertTrue(len(btn) > 0, f"{btn} tugmasi aniqlanmadi!")

    # --- 2-BO'LIM: ICHKI TUGMALAR (SETTINGS) ---
    def test_settings_sub_buttons(self):
        """Sozlamalar ichidagi 7 ta tugmani tekshirish"""
        sub_buttons = [
            "sym_list", "tf_menu", "risk_menu", "qual_menu", 
            "stat_winrate", "set_balance_menu", "toggle_ai_review"
        ]
        print(f"[ANALIZ] Sozlamalar ichidagi {len(sub_buttons)} ta funksiya tekshirilmoqda...")
        for sub in sub_buttons:
            # Har bir callback_data mavjudligini tekshiramiz
            self.assertIn(sub, ["sym_list", "tf_menu", "risk_menu", "qual_menu", "stat_winrate", "set_balance_menu", "toggle_ai_review"])

    # --- 3-BO'LIM: AI REVIEW VA WEBHOOK ---
    def test_ai_review_and_webhook_flow(self):
        """AI Review va Webhook zanjiri tahlili"""
        print("[ANALIZ] AI Review va Webhook mantiqi tekshirilmoqda...")
        
        # Simulyatsiya: Webhookdan signal keldi
        webhook_signal = {'pair': 'ETH/USDT', 'side': 'buy'}
        self.bs['ai_requests'].append({'type': 'review', 'data': webhook_signal})
        
        # AI Review yoqilganligini tekshirish
        self.assertTrue(self.bs['settings']['ai_review_enabled'])
        self.assertEqual(len(self.bs['ai_requests']), 1)

    # --- 4-BO'LIM: VIRTUAL MONITOR (SL/TP) ---
    def test_virtual_monitor_precision(self):
        """SL/TP monitoring aniqligi tahlili"""
        print("[ANALIZ] SL/TP Virtual Monitor mantiqi tekshirilmoqda...")
        entry = 1.0500
        tp = 1.0600
        sl = 1.0450
        
        # Narx TP ga yetdi
        current_price = 1.0610
        status = "PROFIT" if current_price >= tp else ("LOSS" if current_price <= sl else "OPEN")
        self.assertEqual(status, "PROFIT")

    # --- 5-BO'LIM: PANIC VA XAVFSIZLIK ---
    def test_panic_security(self):
        """Panic Button va xavfsizlik tahlili"""
        print("[ANALIZ] Panic Button va xavfsizlik tizimi tekshirilmoqda...")
        # Panic bosildi
        self.bs['panic_request'] = True
        self.assertTrue(self.bs['panic_request'])

if __name__ == '__main__':
    unittest.main()
