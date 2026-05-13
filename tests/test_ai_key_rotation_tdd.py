import pytest
from unittest.mock import MagicMock, patch
from utils.ai_engine import AIEngine

@pytest.mark.asyncio
async def test_ai_key_rotation_on_403_error():
    """
    TDD: 403 Permission Denied (Leaked Key) xatosi bo'lganda 
    AIEngine keyingi kalitga o'tishini (Rotation) tekshirish.
    """
    # 1. 2 ta soxta kalit bilan Engine ni yaratamiz
    mock_keys = "key1,key2"
    engine = AIEngine(mock_keys)
    
    # 2. Mocking Gemini Client
    with patch.object(engine, 'client') as mock_client:
        # 1-chaqiriqda 403 xatosi bersin, 2-sida muvaffaqiyatli javob
        mock_response = MagicMock()
        mock_response.text = "TASDIQLANDI: Bu 2-kalit orqali olingan javob. [TAMOM]"
        
        # Side effect: 1. Exception (403), 2. Success Response
        mock_chat = MagicMock()
        mock_client.chats.create.return_value = mock_chat
        
        # Biz asyncio.to_thread ni ham patch qilishimiz kerak yoki send_message ni
        with patch('asyncio.to_thread') as mock_thread:
            # 1-urinishda Exception, 2-da muvaffaqiyat
            mock_thread.side_effect = [
                Exception("403 PERMISSION_DENIED: Your API key was reported as leaked."),
                mock_response
            ]
            
            # 3. Testni yurgizamiz
            result = await engine.get_analysis("Test prompt", context_type="evaluator")
            
            # 4. Tasdiqlash
            assert "2-kalit" in result, f"Bot keyingi kalitga o'tmadi! Natija: {result}"
            # 1-kalit bloklangani uchun rotate_key chaqirilgan bo'lishi kerak
            assert engine.current_key_index == 1, "Kalit indeksi yangilanmadi!"
            # 2 marta thread chaqirilgan bo'lishi kerak
            assert mock_thread.call_count == 2

def test_ai_key_rotation_logic_direct():
    """
    TDD: _rotate_key funksiyasining mantiqini tekshirish.
    """
    engine = AIEngine("k1,k2,k3")
    assert engine.current_key_index == 0
    
    engine._rotate_key()
    assert engine.current_key_index == 1
    
    engine._rotate_key()
    assert engine.current_key_index == 2
    
    # Oxirgi kalitdan keyin yana boshiga qaytish
    engine._rotate_key()
    assert engine.current_key_index == 0
