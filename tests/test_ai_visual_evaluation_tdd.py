import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from utils.ai_engine import AIEngine

@pytest.fixture
def ai_engine():
    return AIEngine(api_keys="dummy_key_at_least_21_chars_long_123456")

@pytest.mark.asyncio
async def test_ai_visual_evaluation_logic(ai_engine):
    """
    TDD: AI rasm va narx ma'lumotlarini qabul qilib, 
    'TASDIQLAYMAN' yoki 'RAD ETAMAN' qaytarishini tekshirish.
    """
    mock_image = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    
    # 2. Mock get_analysis (evaluator personasi uchun)
    ai_engine.get_analysis = AsyncMock(
        return_value="Tahlil: Grafikda kuchli BOS ko'rinmoqda. RR juda yaxshi. TASDIQLAYMAN"
    )
    
    # 3. Signal ma'lumotlari
    signal_data = {
        'symbol': 'XAU/USD',
        'direction': 'BUY',
        'entry': 2350.0,
        'sl': 2340.0,
        'tp1': 2370.0,
        'quality': 85.0,
        'reason': 'BOS + FVG'
    }
    
    # 4. Tahlilni yurgizish
    is_approved, reason = await ai_engine.evaluate_trade_signal(signal_data, mock_image)
    
    # 5. Tekshiruv
    assert is_approved is True
    assert "TASDIQLAYMAN" in reason
    assert ai_engine.get_analysis.called
    
    # Prompt ichida narxlar borligini tekshirish
    call_args = ai_engine.get_analysis.call_args[0][0]
    assert "2350.0" in call_args
    assert "2340.0" in call_args
