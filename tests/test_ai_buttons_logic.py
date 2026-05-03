import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import threading
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.telegram import TelegramNotifier
from utils.ai_engine import AIEngine

@pytest.fixture
def mock_cfg():
    return {
        'telegram': {'bot_token': 'test_token', 'chat_id': ['123']},
        'gemini_ai': {'api_keys': ['key1', 'key2'], 'model': 'gemini-1.5-flash'},
        'symbols': ['XAU/USD', 'BTC/USDT'],
        'timeframe': '15m'
    }

class TestAIButtonsLogic:

    @pytest.mark.asyncio
    @patch('utils.ai_engine.genai.Client')
    async def test_technical_analysis_request(self, mock_client_class, mock_cfg):
        """Technical analysis tugmasi bosilganda AI tahlili chaqirilishi."""
        notifier = TelegramNotifier(mock_cfg, threading.Lock())
        # Mock AI engine
        notifier.ai.get_analysis = AsyncMock(return_value="Analiz natijasi")
        
        result = await notifier.get_ai_analysis("XAU/USD tahlil qil", "123", context="technical")
        
        assert result == "Analiz natijasi"
        notifier.ai.get_analysis.assert_called_once()
        args, kwargs = notifier.ai.get_analysis.call_args
        assert kwargs['context_type'] == "technical"

    @pytest.mark.asyncio
    @patch('utils.ai_engine.genai.Client')
    async def test_fundamental_analysis_request(self, mock_client_class, mock_cfg):
        """Fundamental analysis tugmasi bosilganda AI drayverlarni tekshirishi."""
        notifier = TelegramNotifier(mock_cfg, threading.Lock())
        notifier.ai.get_analysis = AsyncMock(return_value="Fundamental xulosa")
        
        result = await notifier.get_ai_analysis("DXY tahlili", "123", context="fundamental")
        
        assert result == "Fundamental xulosa"
        args, kwargs = notifier.ai.get_analysis.call_args
        assert kwargs['context_type'] == "fundamental"

    @pytest.mark.asyncio
    @patch('utils.ai_engine.genai.Client')
    async def test_mentor_qa_request(self, mock_client_class, mock_cfg):
        """Mentor Q&A rejimi to'g'ri ishlashi."""
        notifier = TelegramNotifier(mock_cfg, threading.Lock())
        notifier.ai.get_analysis = AsyncMock(return_value="SMC darsi")
        
        result = await notifier.get_ai_analysis("BOS nima?", "123", context="mentor_qa")
        
        assert result == "SMC darsi"
        args, kwargs = notifier.ai.get_analysis.call_args
        assert kwargs['context_type'] == "mentor_qa"

    @pytest.mark.asyncio
    @patch('utils.ai_engine.genai.Client')
    async def test_ai_key_rotation_on_failure(self, mock_client_class, mock_cfg):
        """API Key limiti tugaganda avtomatik aylanish (rotation)."""
        # Mocking genai client
        mock_client = mock_client_class.return_value
        
        # Mock chat and response
        mock_chat = MagicMock()
        mock_client.chats.create.return_value = mock_chat
        
        # Side effect: first call fails, second succeeds
        mock_chat.send_message.side_effect = [
            Exception("429 Resource exhausted"),
            MagicMock(text="Key rotated success")
        ]
        
        ai = AIEngine(mock_cfg['gemini_ai']['api_keys'], "gemini-1.5-flash")
        ai._rotate_key = MagicMock(side_effect=ai._rotate_key)
        
        # In the new SDK, client is stored in ai.client
        ai.client = mock_client
        
        resp = await ai.get_analysis("Test prompt")
        
        assert ai._rotate_key.called
        assert "Key rotated success" in resp
