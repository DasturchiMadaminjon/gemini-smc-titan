import pytest
import asyncio
from utils.ai_engine import AIEngine
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_ai_signal_review():
    """AI signalni baholay olishini (AI Score) tekshirish."""
    mock_api_keys = ["AIzaTest123456789012345678901234567890"]
    engine = AIEngine(mock_api_keys)
    
    # AI javobini mock qilamiz
    mock_response = "Signal tahlili: R:R 1:3. Mantiq: BOS+FVG. AI Bahosi: 90/100."
    
    with patch.object(engine, 'get_analysis', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        
        prompt = "USD/CHF BUY 0.7888 SL 0.7876 TP 0.7916. To'g'rimi?"
        result = await engine.get_analysis(prompt, context_type="chat")
        
        assert "AI Bahosi" in result
        assert "90/100" in result
        print("\n✅ AI Signal Review testi o'tdi!")
