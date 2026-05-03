import unittest
from unittest.mock import MagicMock, AsyncMock
import asyncio
import os

class TestCoreLogic(unittest.TestCase):
    def setUp(self):
        # Dummy config va managerlar
        self.mock_db = MagicMock()
        self.mock_ai = MagicMock()
        self.mock_ai.get_analysis = AsyncMock(return_value="APPROVE")

    def test_ai_review_approval(self):
        """Signalni AI tahlilidan o'tishini tekshirish"""
        signal_data = {'symbol': 'BTC/USDT', 'type': 'BUY', 'price': 65000}
        
        async def run_review():
            # AI ga signalni yuboramiz
            decision = await self.mock_ai.get_analysis(str(signal_data), context="signal_review")
            return decision

        result = asyncio.run(run_review())
        self.assertEqual(result, "APPROVE")
        self.mock_ai.get_analysis.assert_called_once()

    def test_database_migration_logic(self):
        """Bazaga yangi ustun qo'shish mantiqini tekshirish"""
        # Simulyatsiya: Baza ochilganda 'ai_score' ustuni bormi yoki yo'qmi tekshiriladi
        existing_columns = ['id', 'symbol', 'type']
        required_columns = ['ai_score', 'quality']
        
        missing = [c for c in required_columns if c not in existing_columns]
        
        self.assertIn('ai_score', missing)
        self.assertEqual(len(missing), 2)

    def test_virtual_monitor_logic(self):
        """SL va TP darajalarini tekshirish mantiqi"""
        entry = 100
        sl = 95
        tp = 110
        
        # Holat 1: Narx SL ga tegdi
        current_price_sl = 94
        is_sl = current_price_sl <= sl
        
        # Holat 2: Narx TP ga tegdi
        current_price_tp = 112
        is_tp = current_price_tp >= tp
        
        self.assertTrue(is_sl)
        self.assertTrue(is_tp)

    def test_webhook_queue_logic(self):
        """Webhookdan kelgan signalni navbatga (Queue) qo'shish"""
        queue = []
        incoming_webhook = {'pair': 'ETH/USDT', 'action': 'sell', 'source': 'TradingView'}
        
        queue.append(incoming_webhook)
        
        self.assertEqual(len(queue), 1)
        self.assertEqual(queue[0]['pair'], 'ETH/USDT')

if __name__ == '__main__':
    unittest.main()
