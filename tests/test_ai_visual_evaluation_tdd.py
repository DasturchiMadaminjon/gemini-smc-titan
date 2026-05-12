"""
TDD: AI Visual Evaluation Test
==============================
Ushbu test AI Engine rasm qabul qilishi va yangi 'evaluator' 
shaxsi (persona) orqali signalni tahlil qilishini tekshiradi.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from utils.ai_engine import AIEngine

@pytest.fixture
def ai_engine():
    # API keylarsiz mock engine
    engine = AIEngine(api_keys=["fake_key_12345678901234567890"])
    return engine

@pytest.mark.asyncio
async def test_evaluate_signal_with_image_success(ai_engine):
    """AI rasm bilan birga signalni tasdiqlashini tekshirish."""
    
    # Mocking chat response
    mock_response = MagicMock()
    mock_response.text = "SMC tamoyillari asosida tahlil qildim. TASDIQLAYMAN."
    
    # Mocking get_analysis to simulate AI call
    with patch.object(ai_engine, 'get_analysis', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response.text
        
        signal_data = {
            'symbol': 'XAU/USD',
            'direction': 'buy',
            'quality': 85.0,
            'reason': 'BOS + FVG'
        }
        fake_image = b"fake_image_bytes_123"
        
        is_appr, reason = await ai_engine.evaluate_trade_signal(signal_data, image_bytes=fake_image)
        
        # Tekshiramiz: rasm yuborildimi?
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert kwargs['context_type'] == "evaluator"
        assert kwargs['image_bytes'] == fake_image
        
        # Tekshiramiz: Tasdiqlandimi?
        assert is_appr is True
        assert "TASDIQLAYMAN" in reason

@pytest.mark.asyncio
async def test_evaluate_signal_rejection(ai_engine):
    """AI past sifatli signalni rad etishini tekshirish."""
    
    mock_response = MagicMock()
    mock_response.text = "Sifat juda past, RR qoniqarsiz. RAD ETAMAN."
    
    with patch.object(ai_engine, 'get_analysis', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response.text
        
        signal_data = {'symbol': 'BTC/USDT', 'direction': 'sell', 'quality': 45.0}
        
        is_appr, reason = await ai_engine.evaluate_trade_signal(signal_data)
        
        assert is_appr is False
        assert "RAD ETAMAN" in reason

def test_evaluator_persona_contains_strict_rules(ai_engine):
    """Evaluator personasi qoidalari qat'iyligini tekshirish."""
    persona = ai_engine.personas.get("evaluator")
    assert "TITAN SMC MASTER" in persona
    assert "QAT'IYAN TAQIQLANADI" in persona
    assert "TASDIQLANG" in persona
