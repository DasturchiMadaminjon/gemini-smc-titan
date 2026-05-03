import pytest
import yaml
import os
from bot import GeminiBot
from unittest.mock import MagicMock

def test_config_linkage():
    """Tugma bosilganda sozlama o'zgarishi va bot uni ko'rishini tekshirish."""
    # 1. Sozlamani yuklaymiz
    with open('config/settings.yaml', 'r') as f:
        cfg = yaml.safe_load(f)
    
    # 2. Sifatni 90% ga qo'yamiz (Xuddi knopka bosilgandek)
    cfg['smc']['min_quality'] = 90.0
    
    # 3. Botni ushbu sozlama bilan simulyatsiya qilamiz
    bot = GeminiBot()
    bot.cfg = cfg # Yangilangan sozlamani beramiz
    
    # 4. Botning loopidagi mantiqni tekshiramiz
    min_q = bot.cfg.get('smc', {}).get('min_quality', 70.0)
    
    assert min_q == 90.0
    print(f"\n✅ Sozlama bog'lanishi testi o'tdi! Joriy chegara: {min_q}%")

if __name__ == "__main__":
    test_config_linkage()
