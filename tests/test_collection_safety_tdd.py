import pytest
import os
import yaml
from utils.telegram import TelegramNotifier
from utils.persistence import load_extras
from unittest.mock import MagicMock

def test_telegram_collection_types():
    """
    TDD: TelegramNotifier ichidagi kolleksiyalar tipini va 
    metodlar mosligini tekshirish (Regression Test).
    """
    # 1. Mock config
    cfg = {
        'telegram': {
            'bot_token': '123:abc',
            'chat_id': ['12345']
        },
        'gemini_ai': {
            'api_keys': ['key12345678901234567890'],
            'model': 'gemini-1.5-flash'
        }
    }
    lock = MagicMock()
    bot = TelegramNotifier(cfg, lock)

    # 2. onboarding_done 'set' bo'lishi va .add() ishlashi shart
    assert isinstance(bot.onboarding_done, set), "onboarding_done set bo'lishi kerak!"
    # .append() xato berishi kerak (set da append yo'q)
    with pytest.raises(AttributeError):
        bot.onboarding_done.append("123")
    # .add() ishlashi kerak
    bot.onboarding_done.add("123")
    assert "123" in bot.onboarding_done

    # 3. admins 'list' bo'lishi shart
    assert isinstance(bot.admins, list), "admins list bo'lishi kerak!"
    bot.admins.append("67890") # list da append bor

def test_bot_state_ai_requests_safety():
    """
    TDD: bot_state['ai_requests'] har doim list bo'lishini tekshirish.
    """
    # Bot inicializatsiyasini simulyatsiya qilish
    bot_state = {
        'symbols': {},
        'terminal': {'balance': 5000.0},
        'ai_requests': [],  # Bu har doim list bo'lishi shart
        'loss_streak': 0
    }
    
    # .append() ishlashi shart
    bot_state['ai_requests'].append({'type': 'test'})
    assert len(bot_state['ai_requests']) == 1
    assert isinstance(bot_state['ai_requests'], list)

def test_persistence_extras_types():
    """
    TDD: Extras yuklanganda tiplar to'g'ri conversion bo'lishini tekshirish.
    """
    # persistence.load_extras har doim set qaytarishi kerak
    extras = load_extras()
    assert isinstance(extras['onboarding_done'], set)
    assert isinstance(extras['price_alerts'], dict)
    assert isinstance(extras['dedup_cache'], dict)
