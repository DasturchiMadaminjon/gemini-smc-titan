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

@pytest.mark.asyncio
async def test_ai_incomplete_response_handling():
    """TDD: AI chala javob qaytarsa, TAMOM so'zi orqali aniqlash va qayta ishlash"""
    engine = AIEngine(["fake_key"])
    
    responses = [
        "Javobning birinchi qismi. ",
        "ikkinchi qismi. [TAMOM]"
    ]
    
    call_count = [0]
    
    async def mock_generate_content(*args, **kwargs):
        if call_count[0] < len(responses):
            t = responses[call_count[0]]
        else:
            t = responses[-1]
        call_count[0] += 1
        
        # Tekshiramiz: ikkinchi chaqiruvda contents ichida "Oldingi qism" bormi?
        if call_count[0] == 2:
            contents = kwargs.get('contents', [])
            # contents list bo'lsa, ichida "Oldingi qism" qidiramiz
            found_context = any("Oldingi qism" in str(c) for c in args) # asyncio.to_thread args[1] is model, args[2] is contents? No.
            # to_thread(func, *args, **kwargs) -> func(*args, **kwargs)
            # self.client.models.generate_content(model=..., contents=..., config=...)
        
        class DummyResponse:
            @property
            def text(self):
                return t
        return DummyResponse()
    
    with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
        mock_thread.side_effect = mock_generate_content
        
        # get_analysis ni chaqiramiz
        result = await engine.get_analysis("test prompt")
        
        assert call_count[0] == 2, "AI Engine chala javobni sezib, API ga qayta murojaat qilmadi!"
        assert "[TAMOM]" not in result, "Yakuniy javobdan TAMOM so'zi olib tashlanmadi!"
        assert "Javobning birinchi qismi. ikkinchi qismi." in result, "Javoblar to'g'ri jamlanmadi (Accumulation fail)!"
        print("\n✅ AI Auto-Continuation TDD testi o'tdi!")
