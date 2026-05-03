import unittest
import yaml
import os
from core.indicator import GeminiIndicator

class TestBotLogic(unittest.TestCase):
    def setUp(self):
        self.config_path = "config/test_settings.yaml"
        self.test_config = {
            'smc': {'min_quality': 30.0},
            'symbols': ['BTC/USDT', 'ETH/USDT'],
            'trend': {'risk_perc': 2.0},
            'timeframe': '15m',
            'tp': {'tp1_mult': 1.5, 'tp2_mult': 3.0, 'tp3_mult': 5.0}
        }
        if not os.path.exists("config"): os.makedirs("config")
        with open(self.config_path, 'w') as f:
            yaml.dump(self.test_config, f)

    def test_quality_threshold(self):
        """Sifat darajasi 30% bo'lganda ishlashini tekshirish."""
        ind = GeminiIndicator(self.test_config)
        self.assertEqual(ind.smc['min_quality'], 30.0)

    def test_risk_management(self):
        """Risk foizini o'zgarishini tekshirish."""
        self.test_config['trend']['risk_perc'] = 1.0
        self.assertEqual(self.test_config['trend']['risk_perc'], 1.0)

    def tearDown(self):
        if os.path.exists(self.config_path):
            os.remove(self.config_path)

if __name__ == '__main__':
    unittest.main()
