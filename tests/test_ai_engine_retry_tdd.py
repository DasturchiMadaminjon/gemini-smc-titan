import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
from utils.ai_engine import AIEngine

class TestAIEngineRetryTDD:
    """TDD test cases for AIEngine rate limit retries and backoff"""

    @pytest.mark.asyncio
    async def test_ai_engine_retries_on_429_single_key(self):
        # Arrange
        api_keys = ["AIzaSyFakeKey123"]
        engine = AIEngine(api_keys=api_keys, model_name="models/gemini-2.5-flash")
        
        # Mock client models.generate_content
        mock_generate = MagicMock()
        engine.client = MagicMock()
        engine.client.models.generate_content = mock_generate
        
        # First call raises 429, second call returns a valid response
        mock_response = MagicMock()
        mock_response.text = "Muvaffaqiyatli tahlil [TAMOM]"
        mock_response.candidates = [MagicMock()]
        
        mock_generate.side_effect = [
            Exception("429 RESOURCE_EXHAUSTED: Rate limit exceeded"),
            mock_response
        ]
        
        # Act
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            res = await engine.get_analysis("XAU/USD tahlil qil", context_type="technical", provider="GEMINI")
            
            # Assert
            assert res == "Muvaffaqiyatli tahlil"
            assert mock_generate.call_count == 2
            mock_sleep.assert_called_once()  # Should sleep before retry
